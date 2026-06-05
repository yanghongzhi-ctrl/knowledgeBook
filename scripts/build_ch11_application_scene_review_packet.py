from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from audit_word_alignment_ch06_ch09 import extract_docx_paragraphs, locate_chapter_ranges
from review_ch10_ch11_source_boundaries import DEFAULT_DOCX


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APPROVALS = ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.draft.json"
DEFAULT_OUTPUT_JSON = ROOT / "output" / "ch11_application_scene_review_packet_2026-06-05.json"
DEFAULT_OUTPUT_MD = ROOT / "output" / "ch11_application_scene_review_packet_2026-06-05.md"
DEFAULT_OUTPUT_CSV = ROOT / "output" / "ch11_application_scene_review_packet_2026-06-05.csv"


SCENE_RULES = [
    (
        "design_multiphysics",
        "数字化设计与多物理场仿真",
        [
            "设计",
            "风场",
            "桥梁",
            "生成式",
            "参数",
            "视距",
            "停车视距",
            "超车视距",
            "视觉诱导",
            "车辆动力学",
            "侧滑",
            "侧翻",
            "主动安全",
            "虚拟驾驶",
            "安全评价",
            "线形",
        ],
    ),
    (
        "construction_control",
        "智能化施工与质量闭环控制",
        ["施工", "工序", "压实", "摊铺", "预制构件", "吊装", "质量", "工地", "路径优化"],
    ),
    (
        "digital_delivery",
        "基于数字主线的数字化交付",
        ["交付", "竣工", "台账", "结构化资产", "可信存证", "责任追溯", "数字主线"],
    ),
    (
        "predictive_maintenance",
        "预测性养护与结构健康监测",
        [
            "养护",
            "健康监测",
            "应力",
            "应变",
            "结构指纹",
            "探地雷达",
            "病害",
            "降阶模型",
            "模型更新",
            "损伤",
            "物理模型",
            "性能退化",
            "衰变",
        ],
    ),
    (
        "asset_management",
        "全生命周期资产管理与价值评估",
        ["全生命周期", "LCC", "性价比", "资产价值", "折旧", "剩余价值", "更新改造", "特许经营"],
    ),
    (
        "traffic_governance",
        "智慧交通治理与韧性服务",
        ["交通", "路网", "车道级", "数字车流", "轨迹", "韧性", "治理"],
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build grouped review packet for ch11 application-scene Source_Chunks.")
    parser.add_argument("--approvals", type=Path, default=DEFAULT_APPROVALS)
    parser.add_argument("--docx", type=Path, default=DEFAULT_DOCX)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--context", type=int, default=2)
    args = parser.parse_args()

    approvals = json.loads(args.approvals.read_text(encoding="utf-8"))
    paragraphs = extract_docx_paragraphs(args.docx)
    ranges = locate_chapter_ranges(paragraphs)
    ch11_start, ch11_end = ranges["ch11"]
    by_index = {para.index: para for para in paragraphs if ch11_start <= para.index < ch11_end}

    decisions = [
        item
        for item in approvals.get("decisions", [])
        if isinstance(item, dict)
        and item.get("chapter_id") == "ch11"
        and item.get("priority_group") == "P3_ch11_application_scene_manual"
    ]
    items = [build_item(item, by_index, args.context) for item in decisions]
    groups = group_items(items)
    payload = {
        "source_approvals": str(args.approvals),
        "source_docx": str(args.docx),
        "chapter_id": "ch11",
        "purpose": "Grouped review packet for ch11 application-scene Source_Chunks. This is not a manual approval file.",
        "summary": build_summary(items, groups),
        "groups": groups,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(payload), encoding="utf-8")
    write_csv(args.csv, items)
    print(
        json.dumps(
            {
                "output_json": str(args.output_json),
                "markdown": str(args.markdown),
                "csv": str(args.csv),
                "summary": payload["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def build_item(item: dict[str, Any], by_index: dict[int, Any], context: int) -> dict[str, Any]:
    start = safe_int(item.get("approved_paragraph_start"))
    end = safe_int(item.get("approved_paragraph_end")) or start
    source_excerpt = str(item.get("source_excerpt") or "")
    candidate_text = str(item.get("candidate_text") or "")
    scene = infer_scene(source_excerpt)
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
        "current_decision": item.get("decision") or "",
        "scene_id": scene["scene_id"],
        "scene_title": scene["title"],
        "scene_score": scene["score"],
        "scene_terms": scene["terms"],
        "source_excerpt": source_excerpt,
        "candidate_span": {"start": start, "end": end},
        "candidate_text": candidate_text,
        "candidate_score": item.get("candidate_score"),
        "score_margin": item.get("score_margin"),
        "matched_terms": item.get("matched_terms") or [],
        "context": context_rows,
        "review_prompt": review_prompt(item, scene),
    }


def infer_scene(text: str) -> dict[str, Any]:
    scores = []
    for index, (scene_id, title, terms) in enumerate(SCENE_RULES):
        matched = [term for term in terms if term in text]
        scores.append((len(matched), -index, scene_id, title, matched))
    score, _priority, scene_id, title, matched = max(scores, key=lambda row: (row[0], row[1]))
    if score <= 0:
        return {"scene_id": "other", "title": "其他应用场景", "score": 0, "terms": []}
    return {"scene_id": scene_id, "title": title, "score": score, "terms": matched}


def group_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    title_by_id: dict[str, str] = {}
    for item in items:
        grouped[item["scene_id"]].append(item)
        title_by_id[item["scene_id"]] = item["scene_title"]
    order = [scene_id for scene_id, _title, _terms in SCENE_RULES] + ["other"]
    groups = []
    for scene_id in order:
        rows = grouped.get(scene_id) or []
        if not rows:
            continue
        groups.append(
            {
                "scene_id": scene_id,
                "scene_title": title_by_id.get(scene_id, scene_id),
                "count": len(rows),
                "open_count": sum(1 for item in rows if not item.get("current_decision")),
                "items": sorted(rows, key=lambda row: safe_int((row.get("candidate_span") or {}).get("start"))),
            }
        )
    return groups


def build_summary(items: list[dict[str, Any]], groups: list[dict[str, Any]]) -> dict[str, Any]:
    scenes = Counter(item["scene_id"] for item in items)
    decisions = Counter(item.get("current_decision") or "" for item in items)
    return {
        "total": len(items),
        "open": sum(1 for item in items if not item.get("current_decision")),
        "filled": sum(1 for item in items if item.get("current_decision")),
        "by_scene": dict(sorted(scenes.items())),
        "by_decision": dict(sorted(decisions.items())),
        "group_count": len(groups),
    }


def review_prompt(item: dict[str, Any], scene: dict[str, Any]) -> str:
    if str(item.get("review_status") or "") == "manual_anchor_required":
        return (
            f"按“{scene['title']}”场景回看前后文：若 Source_Chunk 是教材段落的合理教学摘要，"
            "可保留 manual_anchor_pending 或补更精确段落；若候选只命中小标题，应补正文锚点。"
        )
    return "核对候选段落是否足以支撑该 Source_Chunk，并避免把教学摘要误标为逐字引用。"


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# ch11 应用场景 Source_Chunks 分组复核包",
        "",
        "说明：本报告用于按应用场景成组复核第11章 Source_Chunks 证据边界，不构成人工审批文件。",
        "",
        f"- 总计：{summary['total']}",
        f"- 已填写：{summary['filled']}",
        f"- 未填写：{summary['open']}",
        f"- 场景组数：{summary['group_count']}",
        "",
        "## 场景分布",
        "",
        "| scene | count |",
        "|---|---:|",
    ]
    for group in payload["groups"]:
        lines.append(f"| {group['scene_title']} | {group['count']} |")
    lines.append("")

    for group in payload["groups"]:
        lines.extend(
            [
                f"## {group['scene_title']} ({group['count']})",
                "",
                f"- open：{group['open_count']}",
                "",
            ]
        )
        for item in group["items"]:
            lines.extend(render_item(item))
    return "\n".join(lines)


def render_item(item: dict[str, Any]) -> list[str]:
    lines = [
        f"### {item['chunk_id']}",
        "",
        f"- 建议决策：`{item['suggested_decision']}`",
        f"- 当前 decision：`{item['current_decision'] or '(empty)'}`",
        f"- 候选段落：{item['candidate_span']['start']}-{item['candidate_span']['end']}",
        f"- 场景命中词：{', '.join(item['scene_terms']) or '(none)'}",
        f"- score={item['candidate_score']} margin={item['score_margin']}",
        f"- 复核提示：{item['review_prompt']}",
        "",
        "Source_Chunk：",
        "",
        quote(item["source_excerpt"]),
        "",
        "候选及前后文：",
        "",
    ]
    for row in item["context"]:
        marker = "候选" if row["role"] == "candidate" else "上下文"
        lines.append(f"**P{row['paragraph']} {marker}**")
        lines.append("")
        lines.append(quote(row["text"]))
        lines.append("")
    return lines


def write_csv(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "scene_title",
        "chunk_id",
        "current_decision",
        "suggested_decision",
        "review_status",
        "candidate_start",
        "candidate_end",
        "candidate_score",
        "score_margin",
        "scene_terms",
        "source_excerpt",
        "candidate_text",
        "review_prompt",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in sorted(items, key=lambda row: (row["scene_id"], row["chunk_id"])):
            span = item.get("candidate_span") or {}
            writer.writerow(
                {
                    "scene_title": item.get("scene_title"),
                    "chunk_id": item.get("chunk_id"),
                    "current_decision": item.get("current_decision"),
                    "suggested_decision": item.get("suggested_decision"),
                    "review_status": item.get("review_status"),
                    "candidate_start": span.get("start"),
                    "candidate_end": span.get("end"),
                    "candidate_score": item.get("candidate_score"),
                    "score_margin": item.get("score_margin"),
                    "scene_terms": ";".join(item.get("scene_terms") or []),
                    "source_excerpt": item.get("source_excerpt"),
                    "candidate_text": item.get("candidate_text"),
                    "review_prompt": item.get("review_prompt"),
                }
            )


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
