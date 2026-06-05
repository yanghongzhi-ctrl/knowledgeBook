from __future__ import annotations

from typing import Any


def render_answer(card: dict[str, Any], include_evidence: bool = True) -> str:
    mode = str(card.get("answer_mode") or "bullet")
    points = [str(p) for p in (card.get("answer_points") or [])]
    question = str(card.get("canonical_question") or "")

    if mode == "table":
        body = _render_table(points)
    elif mode == "step":
        body = _render_steps(points)
    elif mode == "paragraph":
        body = str(card.get("expanded_answer") or card.get("concise_answer") or "\n".join(points))
    else:
        body = _render_bullets(points)

    prefix = f"针对“{question}”，教材知识库可概括为：\n\n" if question else ""
    answer = prefix + body

    if include_evidence:
        evidence = str(card.get("source_excerpt") or "").strip()
        if evidence:
            answer += "\n\n教材依据：" + evidence
    return answer


def _render_bullets(points: list[str]) -> str:
    if not points:
        return "教材知识库未提供可直接输出的答案要点。"
    return "\n".join(f"{idx}. {point}" for idx, point in enumerate(points, 1))


def _render_steps(points: list[str]) -> str:
    if not points:
        return "教材知识库未提供流程步骤。"
    return "\n".join(f"步骤{idx}：{point}" for idx, point in enumerate(points, 1))


def _render_table(points: list[str]) -> str:
    if not points:
        return "教材知识库未提供比较维度。"
    rows = ["| 维度 | 教材要点 |", "|---|---|"]
    for point in points:
        if "：" in point:
            left, right = point.split("：", 1)
        elif ":" in point:
            left, right = point.split(":", 1)
        else:
            left, right = "比较要点", point
        rows.append(f"| {left.strip()} | {right.strip()} |")
    return "\n".join(rows)

