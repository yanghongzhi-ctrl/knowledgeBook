from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any

from .loader import KnowledgePackage


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "bge-m3"


@dataclass(frozen=True)
class EmbeddingRecord:
    embedding_id: str
    source_type: str
    source_id: str
    model: str
    dimensions: int
    embedding: list[float]


class OllamaEmbeddingClient:
    def __init__(self, model: str = DEFAULT_MODEL, base_url: str = DEFAULT_OLLAMA_URL, timeout: int = 120):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = json.dumps({"model": self.model, "input": texts}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama embedding request failed: {exc}") from exc
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list):
            raise RuntimeError(f"Unexpected Ollama embedding response keys: {sorted(data)}")
        return embeddings


def build_embedding_records(
    package: KnowledgePackage,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    batch_size: int = 8,
    limit: int | None = None,
) -> list[EmbeddingRecord]:
    rows = list(package.data.get("Embedding_Corpus", []))
    if limit:
        rows = rows[:limit]
    client = OllamaEmbeddingClient(model=model, base_url=base_url)
    records: list[EmbeddingRecord] = []

    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        texts = [str(row.get("embedding_text") or "") for row in batch]
        vectors = client.embed(texts)
        if len(vectors) != len(batch):
            raise RuntimeError(f"Expected {len(batch)} vectors, got {len(vectors)}")
        for row, vector in zip(batch, vectors):
            if not vector:
                raise RuntimeError(f"Empty embedding for {row.get('embedding_id')}")
            records.append(
                EmbeddingRecord(
                    embedding_id=str(row.get("embedding_id")),
                    source_type=str(row.get("source_type")),
                    source_id=str(row.get("source_id")),
                    model=model,
                    dimensions=len(vector),
                    embedding=[float(value) for value in vector],
                )
            )
        # A tiny pause keeps Ollama responsive on small local machines.
        time.sleep(0.02)

    return records


def write_embedding_jsonl(records: list[EmbeddingRecord], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(
                json.dumps(
                    {
                        "embedding_id": record.embedding_id,
                        "source_type": record.source_type,
                        "source_id": record.source_id,
                        "model": record.model,
                        "dimensions": record.dimensions,
                        "embedding": record.embedding,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )
    return output


def vector_literal(vector: list[float]) -> str:
    # pgvector accepts '[1,2,3]'::vector.
    return "'[" + ",".join(f"{value:.8g}" for value in vector) + "]'::vector"


def sql_text(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def write_embedding_update_sql(records: list[EmbeddingRecord], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "-- Generated embedding updates for pgvector.",
        "-- Apply after 001_init_pgvector.sql and ch01_seed.sql.",
        "BEGIN;",
        "",
    ]
    for record in records:
        lines.append(
            "UPDATE embedding_corpus "
            f"SET embedding = {vector_literal(record.embedding)}, updated_at = now() "
            f"WHERE embedding_id = {sql_text(record.embedding_id)};"
        )
    lines.extend(["", "COMMIT;", ""])
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def summarize_records(records: list[EmbeddingRecord]) -> dict[str, Any]:
    dimensions = sorted(set(record.dimensions for record in records))
    by_source: dict[str, int] = {}
    for record in records:
        by_source[record.source_type] = by_source.get(record.source_type, 0) + 1
    return {
        "count": len(records),
        "dimensions": dimensions,
        "models": sorted(set(record.model for record in records)),
        "by_source_type": by_source,
    }


def read_embedding_jsonl(path: str | Path) -> list[EmbeddingRecord]:
    records: list[EmbeddingRecord] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            records.append(
                EmbeddingRecord(
                    embedding_id=str(row.get("embedding_id")),
                    source_type=str(row.get("source_type")),
                    source_id=str(row.get("source_id")),
                    model=str(row.get("model")),
                    dimensions=int(row.get("dimensions")),
                    embedding=[float(value) for value in row.get("embedding", [])],
                )
            )
    return records


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return -1.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return -1.0
    return dot / (left_norm * right_norm)


def vector_search(
    question: str,
    vector_path: str | Path,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    source_type: str = "answer_card",
    top_k: int = 5,
) -> list[dict[str, Any]]:
    records = [record for record in read_embedding_jsonl(vector_path) if record.source_type == source_type]
    if not records:
        return []
    client = OllamaEmbeddingClient(model=model, base_url=base_url)
    query_vectors = client.embed([question])
    if not query_vectors:
        return []
    query_vector = [float(value) for value in query_vectors[0]]
    scored = [
        {
            "embedding_id": record.embedding_id,
            "source_type": record.source_type,
            "source_id": record.source_id,
            "model": record.model,
            "dimensions": record.dimensions,
            "similarity": cosine_similarity(query_vector, record.embedding),
        }
        for record in records
    ]
    scored.sort(key=lambda item: item["similarity"], reverse=True)
    return scored[:top_k]
