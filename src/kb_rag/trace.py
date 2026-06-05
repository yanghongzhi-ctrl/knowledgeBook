from __future__ import annotations

from pathlib import Path
from typing import Any

from .loader import KnowledgePackage, write_json
from .render import render_answer
from .resources import build_bound_resources, recommend_resources
from .retrieve import AnswerRetriever, confidence


DEFAULT_TRACE_QUESTIONS = [
    "道路工程数字化设计经历了哪些主要阶段？",
    "为什么说BIM不是简单的三维模型？",
    "CAD图元和BIM构件有什么本质区别？",
    "BIM+GIS在路线适宜性分析中有什么作用？",
    "数字孪生为什么强调虚实闭环？",
    "以模型为核心的设计流程包括哪些环节？",
]


def build_trace_samples(
    package: KnowledgePackage,
    questions: list[str] | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    retriever = AnswerRetriever(package)
    resources = build_bound_resources(package.resources)
    samples: list[dict[str, Any]] = []

    for question in questions or DEFAULT_TRACE_QUESTIONS:
        hits = retriever.search(question, top_k=top_k)
        top = hits[0] if hits else None
        card = top.card if top else {}
        samples.append(
            {
                "question": question,
                "top_hits": [
                    {
                        "answer_id": hit.answer_id,
                        "score": round(hit.score, 3),
                        "confidence": confidence(hit.score),
                        "reasons": hit.reasons,
                        "canonical_question": hit.card.get("canonical_question"),
                    }
                    for hit in hits
                ],
                "answer_id": top.answer_id if top else None,
                "answer_mode": card.get("answer_mode"),
                "rendered_answer": render_answer(card) if top else "教材知识库未找到直接答案。",
                "recommended_resources": [
                    {
                        "resource_id": res.get("resource_id"),
                        "title": res.get("title"),
                        "file_path": res.get("file_path"),
                        "status": res.get("status"),
                    }
                    for res in recommend_resources(card, resources)
                ]
                if top
                else [],
            }
        )
    return samples


def write_trace_samples(package: KnowledgePackage, output_path: str | Path) -> Path:
    output = Path(output_path)
    write_json(output, build_trace_samples(package))
    return output

