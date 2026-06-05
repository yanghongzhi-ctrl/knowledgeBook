from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .embeddings import DEFAULT_MODEL, DEFAULT_OLLAMA_URL, OllamaEmbeddingClient
from .hybrid import HybridTrace, _hit_trace, _vector_scoring_params
from .loader import KnowledgePackage
from .retrieve import AnswerRetriever, RetrievalHit


DEFAULT_DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/road_kb"
DEFAULT_VERSION_ID = "ch01_kb_v1.0"


@dataclass(frozen=True)
class DbVectorHit:
    embedding_id: str
    source_id: str
    source_type: str
    similarity: float

    def as_trace(self) -> dict[str, Any]:
        return {
            "embedding_id": self.embedding_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "similarity": round(self.similarity, 6),
        }


def database_url(default: str = DEFAULT_DATABASE_URL) -> str:
    return os.environ.get("ROAD_KB_DATABASE_URL") or default


class PgVectorSearcher:
    def __init__(
        self,
        dsn: str | None = None,
        version_id: str = DEFAULT_VERSION_ID,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_OLLAMA_URL,
    ):
        self.dsn = dsn or database_url()
        self.version_id = version_id
        self.model = model
        self.embedding_client = OllamaEmbeddingClient(model=model, base_url=base_url)

    def search_answer_cards(self, question: str, top_k: int = 20) -> list[DbVectorHit]:
        vectors = self.embedding_client.embed([question])
        if not vectors:
            return []
        vector = _vector_literal(vectors[0])
        sql = """
            SELECT
              embedding_id,
              source_id,
              source_type,
              1 - (embedding <=> (%s)::vector(1024)) AS similarity
            FROM embedding_corpus
            WHERE version_id = %s
              AND source_type = 'answer_card'
              AND embedding IS NOT NULL
            ORDER BY embedding <=> (%s)::vector(1024)
            LIMIT %s
        """
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            rows = conn.execute(sql, (vector, self.version_id, vector, top_k)).fetchall()
        return [
            DbVectorHit(
                embedding_id=str(row["embedding_id"]),
                source_id=str(row["source_id"]),
                source_type=str(row["source_type"]),
                similarity=float(row["similarity"]),
            )
            for row in rows
        ]

    def table_counts(self) -> dict[str, int]:
        sql = """
            SELECT 'answer_cards' AS table_name, count(*) AS row_count FROM answer_cards WHERE version_id = %s
            UNION ALL
            SELECT 'knowledge_points', count(*) FROM knowledge_points WHERE version_id = %s
            UNION ALL
            SELECT 'embedding_corpus', count(*) FROM embedding_corpus WHERE version_id = %s
            UNION ALL
            SELECT 'embedded_vectors', count(*) FROM embedding_corpus WHERE version_id = %s AND embedding IS NOT NULL
            UNION ALL
            SELECT 'resources', count(*) FROM resources WHERE version_id = %s
        """
        params = (self.version_id,) * 5
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            rows = conn.execute(sql, params).fetchall()
        return {str(row["table_name"]): int(row["row_count"]) for row in rows}


class DbHybridAnswerRetriever:
    def __init__(
        self,
        package: KnowledgePackage,
        dsn: str | None = None,
        version_id: str = DEFAULT_VERSION_ID,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_OLLAMA_URL,
    ):
        self.package = package
        self.keyword = AnswerRetriever(package)
        self.cards_by_id = {str(card.get("answer_id")): card for card in package.answer_cards}
        self.model = model
        self.searcher = PgVectorSearcher(dsn=dsn, version_id=version_id, model=model, base_url=base_url)

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
        vector_error = ""
        try:
            vector_hits = self.searcher.search_answer_cards(question, top_k=vector_k)
        except Exception as exc:  # pragma: no cover - runtime service fallback
            vector_hits = []
            vector_error = str(exc)

        combined: dict[str, dict[str, Any]] = {}
        for hit in keyword_hits:
            combined[hit.answer_id] = {
                "answer_id": hit.answer_id,
                "score": hit.score,
                "reasons": list(hit.reasons),
                "card": hit.card,
            }

        threshold, scale = _vector_scoring_params(self.model)
        for vector_hit in vector_hits:
            answer_id = vector_hit.source_id
            card = self.cards_by_id.get(answer_id)
            if not card:
                continue
            vector_score = max(0.0, (vector_hit.similarity - threshold) * scale)
            item = combined.setdefault(
                answer_id,
                {"answer_id": answer_id, "score": 0.0, "reasons": [], "card": card},
            )
            item["score"] += vector_score
            if vector_score > 0:
                item["reasons"].append(f"pgvector:{vector_hit.similarity:.4f}")

        merged = [
            RetrievalHit(
                answer_id=str(item["answer_id"]),
                score=float(item["score"]),
                reasons=list(item["reasons"]),
                card=item["card"],
            )
            for item in combined.values()
            if item["score"] > 0
        ]
        merged.sort(key=lambda hit: hit.score, reverse=True)

        vector_top = [hit.as_trace() for hit in vector_hits[:top_k]]
        if vector_error:
            vector_top = [{"error": vector_error, "fallback": "keyword_only"}]

        trace = HybridTrace(
            question=question,
            keyword_top=[_hit_trace(hit) for hit in keyword_hits[:top_k]],
            vector_top=vector_top,
            hybrid_top=[_hit_trace(hit) for hit in merged[:top_k]],
        )
        return merged[:top_k], trace


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{float(value):.8g}" for value in vector) + "]"
