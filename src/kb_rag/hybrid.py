from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .embeddings import (
    DEFAULT_MODEL,
    OllamaEmbeddingClient,
    cosine_similarity,
    read_embedding_jsonl,
)
from .loader import KnowledgePackage, write_json
from .retrieve import AnswerRetriever, RetrievalHit, confidence, list_text


DEFAULT_VECTOR_PATH = Path("output/ch01_rag_engine/embeddings/ch01_embedding_vectors.jsonl")

DOMAIN_PHRASES = [
    "虚实闭环",
    "数字孪生",
    "BIM+GIS",
    "CAD图元",
    "BIM构件",
    "工程语义",
    "构件化",
    "参数化",
    "协同化",
    "生命周期化",
    "模型为核心",
    "技术体系",
    "数据驱动",
    "路线适宜性",
]


@dataclass
class HybridTrace:
    question: str
    keyword_top: list[dict[str, Any]]
    vector_top: list[dict[str, Any]]
    hybrid_top: list[dict[str, Any]]


class HybridAnswerRetriever:
    """Keyword-first retriever with optional cached vector boost.

    High-confidence exact/pattern matches should remain stable. Vectors are most
    useful when the keyword-only score is low or when the student asks a looser
    why/how question.
    """

    def __init__(
        self,
        package: KnowledgePackage,
        vector_path: str | Path = DEFAULT_VECTOR_PATH,
        model: str = DEFAULT_MODEL,
        base_url: str = "http://127.0.0.1:11434",
    ):
        self.package = package
        self.keyword = AnswerRetriever(package)
        self.model = model
        self.base_url = base_url
        self.cards_by_id = {str(card.get("answer_id")): card for card in package.answer_cards}
        self.vector_records = [
            record
            for record in read_embedding_jsonl(vector_path)
            if record.source_type == "answer_card" and record.source_id in self.cards_by_id
        ]

    def search(self, question: str, top_k: int = 5, keyword_k: int = 30, vector_k: int = 20) -> list[RetrievalHit]:
        hits, _trace = self.search_with_trace(question, top_k=top_k, keyword_k=keyword_k, vector_k=vector_k)
        return hits

    def search_with_trace(
        self,
        question: str,
        top_k: int = 5,
        keyword_k: int = 30,
        vector_k: int = 20,
    ) -> tuple[list[RetrievalHit], HybridTrace]:
        keyword_hits = self.keyword.search(question, top_k=keyword_k)
        keyword_by_id = {hit.answer_id: hit for hit in keyword_hits}
        vector_hits = self._vector_hits(question, top_k=vector_k)

        combined: dict[str, dict[str, Any]] = {}
        for hit in keyword_hits:
            combined[hit.answer_id] = {
                "answer_id": hit.answer_id,
                "score": hit.score,
                "reasons": list(hit.reasons),
                "card": hit.card,
                "keyword_score": hit.score,
                "vector_score": 0.0,
                "vector_similarity": None,
            }

        for vector_hit in vector_hits:
            answer_id = str(vector_hit["source_id"])
            card = self.cards_by_id.get(answer_id)
            if not card:
                continue
            # Qwen chat embeddings are serviceable but not ideal. Keep the boost
            # conservative and only reward high similarities.
            similarity = float(vector_hit["similarity"])
            threshold, scale = _vector_scoring_params(str(vector_hit.get("model") or ""))
            vector_score = max(0.0, (similarity - threshold) * scale)
            item = combined.setdefault(
                answer_id,
                {
                    "answer_id": answer_id,
                    "score": 0.0,
                    "reasons": [],
                    "card": card,
                    "keyword_score": 0.0,
                    "vector_score": 0.0,
                    "vector_similarity": None,
                },
            )
            item["score"] += vector_score
            item["vector_score"] = vector_score
            item["vector_similarity"] = similarity
            if vector_score > 0:
                item["reasons"].append(f"vector:{similarity:.4f}")

        self._apply_phrase_boost(question, combined)

        merged = [
            RetrievalHit(
                answer_id=item["answer_id"],
                score=float(item["score"]),
                reasons=list(item["reasons"]),
                card=item["card"],
            )
            for item in combined.values()
            if item["score"] > 0
        ]
        merged.sort(key=lambda hit: hit.score, reverse=True)

        trace = HybridTrace(
            question=question,
            keyword_top=[_hit_trace(hit) for hit in keyword_hits[:top_k]],
            vector_top=vector_hits[:top_k],
            hybrid_top=[_hit_trace(hit) for hit in merged[:top_k]],
        )
        return merged[:top_k], trace

    def _apply_phrase_boost(self, question: str, combined: dict[str, dict[str, Any]]) -> None:
        active_phrases = [phrase for phrase in DOMAIN_PHRASES if phrase.lower() in question.lower()]
        if not active_phrases:
            return
        for item in combined.values():
            card = item["card"]
            canonical = str(card.get("canonical_question") or "")
            answer_text = list_text(card.get("answer_points"))
            for phrase in active_phrases:
                if phrase.lower() in canonical.lower():
                    item["score"] += 35
                    item["reasons"].append(f"phrase_canonical:{phrase}")
                elif phrase.lower() in answer_text.lower():
                    item["score"] += 10
                    item["reasons"].append(f"phrase_answer:{phrase}")

    def _vector_hits(self, question: str, top_k: int) -> list[dict[str, Any]]:
        if not self.vector_records:
            return []
        client = OllamaEmbeddingClient(model=self.model, base_url=self.base_url)
        query_vectors = client.embed([question])
        if not query_vectors:
            return []
        query_vector = [float(value) for value in query_vectors[0]]
        scored = [
            {
                "embedding_id": record.embedding_id,
                "source_id": record.source_id,
                "model": record.model,
                "similarity": cosine_similarity(query_vector, record.embedding),
            }
            for record in self.vector_records
        ]
        scored.sort(key=lambda item: item["similarity"], reverse=True)
        return scored[:top_k]


def _hit_trace(hit: RetrievalHit) -> dict[str, Any]:
    return {
        "answer_id": hit.answer_id,
        "score": round(hit.score, 3),
        "confidence": confidence(hit.score),
        "reasons": hit.reasons,
        "canonical_question": hit.card.get("canonical_question"),
    }


def _vector_scoring_params(model: str) -> tuple[float, float]:
    model = model.lower()
    if "bge" in model:
        return 0.40, 180.0
    return 0.84, 350.0


def write_hybrid_report(
    package: KnowledgePackage,
    questions: list[str],
    output_path: str | Path,
    vector_path: str | Path = DEFAULT_VECTOR_PATH,
    model: str = DEFAULT_MODEL,
) -> Path:
    retriever = HybridAnswerRetriever(package, vector_path=vector_path, model=model)
    rows = []
    for question in questions:
        hits, trace = retriever.search_with_trace(question, top_k=5)
        rows.append(
            {
                "question": question,
                "selected_answer_id": hits[0].answer_id if hits else None,
                "selected_question": hits[0].card.get("canonical_question") if hits else None,
                "keyword_top": trace.keyword_top,
                "vector_top": trace.vector_top,
                "hybrid_top": trace.hybrid_top,
            }
        )
    output = Path(output_path)
    write_json(output, rows)
    return output
