from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from audit_word_alignment_ch06_ch09 import CHAPTERS, extract_docx_paragraphs, locate_chapter_ranges
from review_ch10_ch11_source_boundaries import DEFAULT_DOCX


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APPROVAL_TEMPLATE = ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.template.json"
DEFAULT_OUTPUT_JSON = ROOT / "output" / "ch10_p1_source_review_packet_2026-06-05.json"
DEFAULT_OUTPUT_MD = ROOT / "output" / "ch10_p1_source_review_packet_2026-06-05.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a focused P1 review packet for ch10 Source_Chunks.")
    parser.add_argument("--template", type=Path, default=DEFAULT_APPROVAL_TEMPLATE)
    parser.add_argument("--docx", type=Path, default=DEFAULT_DOCX)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--context", type=int, default=2)
    args = parser.parse_args()

    template = json.loads(args.template.read_text(encoding="utf-8"))
    paragraphs = extract_docx_paragraphs(args.docx)
    ranges = locate_chapter_ranges(paragraphs)
    ch10_start, ch10_end = ranges["ch10"]
    by_index = {para.index: para for para in paragraphs if ch10_start <= para.index < ch10_end}
    decisions = [
        item
        for item in template.get("decisions", [])
        if isinstance(item, dict) and str(item.get("priority_group") or "").startswith("P1_ch10")
    ]

    items = [build_packet_item(item, by_index, args.context) for item in decisions]
    payload = {
        "source_template": str(args.template),
        "source_docx": str(args.docx),
        "chapter_id": "ch10",
        "purpose": "Focused P1 review packet. Suggestions are not manual approvals.",
        "items": items,
        "summary": {
            "total": len(items),
            "quick_confirm": sum(1 for item in items if item["priority_group"] == "P1_ch10_quick_confirm"),
            "formula_gap": sum(1 for item in items if item["priority_group"] == "P1_ch10_formula_gap"),
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({"output_json": str(args.output_json), "markdown": str(args.markdown), "summary": payload["summary"]}, ensure_ascii=False, indent=2))
    return 0


def build_packet_item(item: dict[str, Any], by_index: dict[int, Any], context: int) -> dict[str, Any]:
    start = safe_int(item.get("approved_paragraph_start"))
    end = safe_int(item.get("approved_paragraph_end")) or start
    context_rows = []
    if start:
        for para_index in range(start - context, end + context + 1):
            para = by_index.get(para_index)
            if para is None:
                continue
            context_rows.append(
                {
                    "paragraph": para.index,
                    "role": "candidate" if start <= para.index <= end else "context",
                    "text": para.text,
                }
            )
    return {
        "chapter_id": item.get("chapter_id"),
        "chunk_id": item.get("chunk_id"),
        "priority_group": item.get("priority_group"),
        "review_status": item.get("review_status"),
        "suggested_decision": item.get("suggested_decision"),
        "source_excerpt": item.get("source_excerpt"),
        "candidate_score": item.get("candidate_score"),
        "score_margin": item.get("score_margin"),
        "candidate_span": {"start": start, "end": end},
        "candidate_text": item.get("candidate_text"),
        "candidate_reasons": item.get("candidate_reasons") or [],
        "matched_terms": item.get("matched_terms") or [],
        "context": context_rows,
        "review_prompt": review_prompt(item),
    }


def review_prompt(item: dict[str, Any]) -> str:
    if item.get("priority_group") == "P1_ch10_formula_gap":
        return "重点核对公式/变量是否在 Word 段落中被截断；若候选仍不完整，应标记 split_required 或 manual_anchor_pending。"
    return "核对 Source_Chunk 与候选 Word 段落是否表达同一概念；若是，仅确认概念锚点，不标记为逐字引用。"


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# ch10 P1 Source_Chunks 复核包",
        "",
        "说明：本报告用于辅助确认，不构成人工审批文件。确认后仍应通过工作台导出正式审批 JSON，并运行校验脚本。",
        "",
        f"- 总计：{payload['summary']['total']}",
        f"- 快速确认：{payload['summary']['quick_confirm']}",
        f"- 公式缺口：{payload['summary']['formula_gap']}",
        "",
    ]
    for item in payload["items"]:
        lines.extend(
            [
                f"## {item['chunk_id']} / {item['priority_group']}",
                "",
                f"- 建议决策：`{item['suggested_decision']}`",
                f"- 候选段落：{item['candidate_span']['start']}-{item['candidate_span']['end']}",
                f"- score={item['candidate_score']} margin={item['score_margin']}",
                f"- 复核提示：{item['review_prompt']}",
                "",
                "Source_Chunk：",
                "",
                quote(item.get("source_excerpt") or ""),
                "",
                "候选及前后文：",
                "",
            ]
        )
        for row in item["context"]:
            marker = "候选" if row["role"] == "candidate" else "上下文"
            lines.append(f"**P{row['paragraph']} {marker}**")
            lines.append("")
            lines.append(quote(row["text"]))
            lines.append("")
    return "\n".join(lines)


def quote(text: str) -> str:
    cleaned = str(text).strip()
    if not cleaned:
        return "> "
    return "\n".join("> " + line for line in cleaned.splitlines())


def safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
