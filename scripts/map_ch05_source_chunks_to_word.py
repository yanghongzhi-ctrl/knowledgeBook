from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kb_rag.embeddings import DEFAULT_MODEL, OllamaEmbeddingClient, cosine_similarity


RAW_PATH = next((ROOT / "data" / "raw" / "ch05").glob("*.json"))
WORD_EXTRACT = ROOT / "output" / "ch05_rag_engine" / "reports" / "ch05_word_extract.txt"
REPORT_JSON = ROOT / "output" / "ch05_rag_engine" / "reports" / "ch05_word_correspondence.json"
REPORT_MD = ROOT / "output" / "ch05_rag_engine" / "reports" / "ch05_word_correspondence.md"
DEFAULT_MANUAL_APPROVALS = ROOT / "data" / "review" / "ch05_word_correspondence_manual_approvals.json"

SECTION_MARKERS = {
    "ch05": ("GIS理论基础与空间分析方法", "第一节 GIS基础与空间数据模型"),
    "ch05_sec01": ("第一节 GIS基础与空间数据模型", "第二节 空间分析原理与方法"),
    "ch05_sec02": ("第二节 空间分析原理与方法", "第三节 地统计分析的原理与方法"),
    "ch05_sec03": ("第三节 地统计分析的原理与方法", "第四节 道路网络分析方法"),
    "ch05_sec04": ("第四节 道路网络分析方法", None),
}

GENERIC_TERMS = {
    "GIS",
    "道路",
    "工程",
    "分析",
    "方法",
    "模型",
    "系统",
    "数据",
    "空间",
    "应用",
    "组成",
    "原理",
    "基础",
    "问题",
    "关系",
    "功能",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Map ch05 summary Source_Chunks to Word manuscript paragraphs")
    parser.add_argument("--apply-high-confidence", action="store_true")
    parser.add_argument("--high-threshold", type=float, default=0.56)
    parser.add_argument("--medium-threshold", type=float, default=0.43)
    parser.add_argument("--min-margin", type=float, default=0.045)
    parser.add_argument("--use-embeddings", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--manual-approval-file", default=str(DEFAULT_MANUAL_APPROVALS))
    args = parser.parse_args()

    data = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    lines = [line.strip() for line in WORD_EXTRACT.read_text(encoding="utf-8").splitlines() if line.strip()]
    section_ranges = build_section_ranges(lines)
    manual_approvals = load_manual_approvals(Path(args.manual_approval_file), lines)
    kp_by_id = {
        str(row.get("kp_id")): row
        for row in data.get("Knowledge_Points", [])
        if isinstance(row, dict) and row.get("kp_id")
    }
    results = []
    status_counts: Counter[str] = Counter()

    for row in data.get("Source_Chunks", []):
        if not isinstance(row, dict):
            continue
        result = map_chunk(
            row,
            kp_by_id=kp_by_id,
            lines=lines,
            section_ranges=section_ranges,
            high_threshold=args.high_threshold,
            medium_threshold=args.medium_threshold,
            min_margin=args.min_margin,
        )
        result = apply_manual_approval(result, manual_approvals.get(str(row.get("chunk_id") or "")), lines)
        results.append(result)

    if args.use_embeddings:
        enhance_with_embeddings(
            results,
            model=args.model,
            base_url=args.base_url,
            batch_size=args.batch_size,
            high_threshold=args.high_threshold,
            medium_threshold=args.medium_threshold,
            min_margin=args.min_margin,
        )

    for row, result in zip(data.get("Source_Chunks", []), results):
        status_counts[result["status"]] += 1
        if args.apply_high_confidence and isinstance(row, dict):
            apply_result(row, result)

    if args.apply_high_confidence:
        update_metadata(data, status_counts)
        RAW_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    write_reports(results, status_counts, section_ranges, args)
    print(f"chunks={len(results)}")
    print("statuses=" + json.dumps(dict(status_counts), ensure_ascii=False, sort_keys=True))
    print(f"report_json={REPORT_JSON}")
    print(f"report_md={REPORT_MD}")
    print(f"applied={args.apply_high_confidence}")
    return 0


def build_section_ranges(lines: list[str]) -> dict[str, tuple[int, int]]:
    ranges: dict[str, tuple[int, int]] = {}
    for section_id, (start_marker, end_marker) in SECTION_MARKERS.items():
        start = find_line(lines, start_marker)
        end = find_line(lines, end_marker) if end_marker else len(lines)
        if start is None:
            start = 0
        if end is None or end <= start:
            end = len(lines)
        ranges[section_id] = (start, end)
    return ranges


def find_line(lines: list[str], marker: str | None) -> int | None:
    if not marker:
        return None
    marker_norm = normalize(marker)
    for index, line in enumerate(lines):
        line_norm = normalize(line)
        if marker_norm == line_norm or marker_norm in line_norm:
            return index
    return None


def map_chunk(
    row: dict[str, Any],
    *,
    kp_by_id: dict[str, dict[str, Any]],
    lines: list[str],
    section_ranges: dict[str, tuple[int, int]],
    high_threshold: float,
    medium_threshold: float,
    min_margin: float,
) -> dict[str, Any]:
    objective_result = map_learning_objective(row, lines)
    if objective_result is not None:
        return objective_result

    section_id = str(row.get("section_id") or "ch05")
    start, end = section_ranges.get(section_id, (0, len(lines)))
    kp = kp_by_id.get(str(row.get("source_hint") or ""), {})
    query = build_query(row, kp)
    candidates = []
    for line_index in range(start, end):
        for window_size in (1, 2, 3):
            window_end = min(end, line_index + window_size)
            if window_end <= line_index:
                continue
            text = " ".join(lines[line_index:window_end])
            score, reasons = score_candidate(query, text, lines[line_index])
            candidates.append(
                {
                    "line_start": line_index + 1,
                    "line_end": window_end,
                    "score": round(score, 6),
                    "reasons": reasons,
                    "text": text,
                }
            )
    candidates.sort(key=lambda item: float(item["score"]), reverse=True)
    top = dedupe_candidates(candidates)[:5]
    best = top[0] if top else empty_candidate()
    second_score = float(top[1]["score"]) if len(top) > 1 else 0.0
    margin = float(best["score"]) - second_score
    status = classify_status(best, margin, high_threshold, medium_threshold, min_margin)
    return {
        "chunk_id": row.get("chunk_id"),
        "section_id": section_id,
        "section_title": row.get("section_title"),
        "chunk_summary": row.get("chunk_summary"),
        "source_hint": row.get("source_hint"),
        "source_excerpt": row.get("source_excerpt"),
        "_query_text": query_text(query),
        "status": status,
        "best_score": best["score"],
        "score_margin": round(margin, 6),
        "top_candidates": top,
    }


def map_learning_objective(row: dict[str, Any], lines: list[str]) -> dict[str, Any] | None:
    match = re.fullmatch(r"ch05_obj_(\d+)", str(row.get("chunk_id") or ""))
    if not match:
        return None

    objective_number = int(match.group(1))
    line_number = objective_number + 2
    if objective_number not in range(1, 5) or line_number > len(lines):
        return None

    text = lines[line_number - 1]
    candidate = {
        "line_start": line_number,
        "line_end": line_number,
        "score": 1.0,
        "reasons": [f"objective_number_match:{objective_number}"],
        "text": text,
    }
    return {
        "chunk_id": row.get("chunk_id"),
        "section_id": str(row.get("section_id") or "ch05"),
        "section_title": row.get("section_title"),
        "chunk_summary": row.get("chunk_summary"),
        "source_hint": row.get("source_hint"),
        "source_excerpt": row.get("source_excerpt"),
        "_query_text": str(row.get("source_excerpt") or row.get("chunk_summary") or ""),
        "status": "high_confidence",
        "best_score": 1.0,
        "score_margin": 1.0,
        "top_candidates": [candidate],
    }


def load_manual_approvals(path: Path, lines: list[str]) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    approvals: dict[str, dict[str, Any]] = {}
    for item in payload.get("approvals", []):
        if not isinstance(item, dict):
            continue
        chunk_id = str(item.get("chunk_id") or "")
        line_start = int(item.get("line_start") or 0)
        line_end = int(item.get("line_end") or 0)
        if not chunk_id or line_start < 1 or line_end < line_start or line_end > len(lines):
            raise ValueError(f"Invalid manual approval span: {item}")
        approvals[chunk_id] = item
    return approvals


def apply_manual_approval(
    result: dict[str, Any],
    approval: dict[str, Any] | None,
    lines: list[str],
) -> dict[str, Any]:
    if not approval:
        return result
    line_start = int(approval["line_start"])
    line_end = int(approval["line_end"])
    approved_text = " ".join(lines[line_start - 1 : line_end])
    result = dict(result)
    result["status"] = "review_confirmed"
    result["best_score"] = 1.0
    result["score_margin"] = 1.0
    result["manual_review_note"] = approval.get("note")
    result["top_candidates"] = [
        {
            "line_start": line_start,
            "line_end": line_end,
            "score": 1.0,
            "reasons": [
                "manual_review_confirmed",
                f"approved_span:{line_start}-{line_end}",
                str(approval.get("note") or ""),
            ],
            "text": approved_text,
        }
    ]
    return result


def build_query(row: dict[str, Any], kp: dict[str, Any]) -> dict[str, Any]:
    title = str(row.get("section_title") or row.get("chunk_summary") or kp.get("title") or "")
    excerpt = str(row.get("source_excerpt") or "")
    definition = str(kp.get("definition") or "")
    aliases = to_list(kp.get("aliases"))
    keywords = to_list(kp.get("keywords"))
    key_points = to_list(kp.get("key_points"))
    terms = extract_terms([title, *aliases, *keywords, definition, excerpt, *key_points[:2]])
    return {
        "title": title,
        "title_variants": [title],
        "excerpt": excerpt,
        "definition": definition,
        "terms": terms,
    }


def score_candidate(query: dict[str, Any], text: str, first_line: str) -> tuple[float, list[str]]:
    text_norm = normalize(text)
    first_norm = normalize(first_line)
    if not text_norm:
        return 0.0, []

    title_score = 0.0
    title_reason = ""
    for variant in query["title_variants"]:
        variant_norm = normalize(str(variant))
        if not variant_norm:
            continue
        if variant_norm == first_norm:
            candidate_score = 1.0
            reason = "title_exact"
        elif variant_norm in first_norm or first_norm in variant_norm:
            candidate_score = 0.88
            reason = "title_contains"
        elif variant_norm in text_norm:
            candidate_score = 0.76
            reason = "title_in_window"
        else:
            candidate_score = SequenceMatcher(None, variant_norm, first_norm).ratio() * 0.6
            reason = "title_similar"
        if candidate_score > title_score:
            title_score = candidate_score
            title_reason = reason

    definition_score = text_similarity(query["definition"], text)
    excerpt_score = text_similarity(query["excerpt"], text)
    terms = query["terms"]
    matched_terms = [term for term in terms if normalize(term) and normalize(term) in text_norm]
    term_score = len(matched_terms) / len(terms) if terms else 0.0

    score = 0.30 * title_score + 0.25 * definition_score + 0.25 * excerpt_score + 0.20 * term_score
    if title_score >= 0.88 and (definition_score >= 0.20 or excerpt_score >= 0.20 or term_score >= 0.20):
        score += 0.07
    if title_score >= 0.76 and len(matched_terms) >= 2:
        score += 0.04
    score = min(1.0, score)

    reasons = []
    if title_reason and title_score >= 0.55:
        reasons.append(f"{title_reason}:{title_score:.2f}")
    if definition_score >= 0.12:
        reasons.append(f"definition:{definition_score:.2f}")
    if excerpt_score >= 0.12:
        reasons.append(f"summary:{excerpt_score:.2f}")
    if matched_terms:
        reasons.append("terms:" + ",".join(matched_terms[:8]))
    return score, reasons


def text_similarity(left: str, right: str) -> float:
    left_norm = normalize(left)
    right_norm = normalize(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm in right_norm:
        return 1.0
    if right_norm in left_norm:
        return len(right_norm) / len(left_norm)
    sequence = SequenceMatcher(None, left_norm, right_norm).ratio()
    ngrams_left = ngrams(left_norm, 3)
    ngrams_right = ngrams(right_norm, 3)
    jaccard = len(ngrams_left & ngrams_right) / len(ngrams_left | ngrams_right) if ngrams_left | ngrams_right else 0.0
    return 0.45 * sequence + 0.55 * jaccard


def ngrams(text: str, size: int) -> set[str]:
    if len(text) <= size:
        return {text} if text else set()
    return {text[index : index + size] for index in range(len(text) - size + 1)}


def extract_terms(values: list[str]) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        for term in re.findall(r"[A-Za-z][A-Za-z0-9+*.-]{1,}|[\u4e00-\u9fff]{2,12}", str(value)):
            cleaned = term.strip()
            normalized = normalize(cleaned)
            if not normalized or cleaned in GENERIC_TERMS or len(normalized) < 2:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            terms.append(cleaned)
            if len(terms) >= 18:
                return terms
    return terms


def dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    seen_lines: set[int] = set()
    for candidate in candidates:
        line_start = int(candidate.get("line_start") or 0)
        if not line_start or line_start in seen_lines:
            continue
        seen_lines.add(line_start)
        results.append(candidate)
    return results


def classify_status(
    best: dict[str, Any],
    margin: float,
    high_threshold: float,
    medium_threshold: float,
    min_margin: float,
) -> str:
    score = float(best.get("score") or 0.0)
    reasons = best.get("reasons") or []
    has_title_anchor = any(str(reason).startswith(("title_exact", "title_contains", "title_in_window")) for reason in reasons)
    has_content_support = any(str(reason).startswith(("definition", "summary")) for reason in reasons)
    semantic_support = any(
        str(reason).startswith("semantic:") and float(str(reason).split(":", 1)[1]) >= 0.72
        for reason in reasons
    )
    matched_text = normalize(str(best.get("text") or ""))
    if (
        score >= high_threshold
        and margin >= min_margin
        and len(matched_text) >= 24
        and ((has_title_anchor and has_content_support) or (semantic_support and (has_title_anchor or has_content_support)))
    ):
        return "high_confidence"
    if score >= medium_threshold and (has_title_anchor or margin >= min_margin):
        return "medium_confidence"
    return "manual_review"


def apply_result(row: dict[str, Any], result: dict[str, Any]) -> None:
    status = str(result["status"])
    best = result["top_candidates"][0] if result["top_candidates"] else empty_candidate()
    row["source_excerpt_role"] = "knowledge_summary_not_verbatim_quote"
    row["word_correspondence_status"] = status
    row["word_correspondence"] = {
        "source": WORD_EXTRACT.name,
        "line_start": best.get("line_start"),
        "line_end": best.get("line_end"),
        "score": best.get("score"),
        "score_margin": result.get("score_margin"),
        "reasons": best.get("reasons"),
        "matched_text": best.get("text"),
    }
    if status in {"high_confidence", "review_confirmed"}:
        row["word_verification"] = "concept_supported"
        if status == "review_confirmed":
            row["verification_note"] = "该Source_Chunk为知识摘要，已通过人工复核建立正式稿概念依据对应关系，不作为逐字引用。"
        else:
            row["verification_note"] = "该Source_Chunk为知识摘要，已建立高置信度正式稿段落对应关系，不作为逐字引用。"
    elif status == "medium_confidence":
        row["verification_note"] = "已生成正式稿候选段落，需人工确认后方可作为正式稿依据。"
    else:
        row["verification_note"] = "未形成稳定正式稿对应关系，继续保留人工复核。"


def update_metadata(data: dict[str, Any], status_counts: Counter[str]) -> None:
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        data["metadata"] = metadata
    metadata["word_correspondence"] = {
        "source": WORD_EXTRACT.name,
        "method": "title_anchor_definition_summary_term_overlap",
        "status_counts": dict(status_counts),
        "note": "Source_Chunks为知识摘要，correspondence只表示概念依据对应，不表示逐字引用。",
    }
    verification = Counter()
    for row in data.get("Source_Chunks", []):
        if isinstance(row, dict):
            verification[str(row.get("word_verification") or "unverified")] += 1
    metadata["word_verification"] = dict(verification)


def write_reports(
    results: list[dict[str, Any]],
    status_counts: Counter[str],
    section_ranges: dict[str, tuple[int, int]],
    args: argparse.Namespace,
) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "chapter_id": "ch05",
        "source": str(WORD_EXTRACT),
        "raw_package": str(RAW_PATH),
        "applied": args.apply_high_confidence,
        "thresholds": {
            "high": args.high_threshold,
            "medium": args.medium_threshold,
            "min_margin": args.min_margin,
        },
        "section_ranges": {
            section_id: {"line_start": start + 1, "line_end": end}
            for section_id, (start, end) in section_ranges.items()
        },
        "status_counts": dict(status_counts),
        "results": [public_result(item) for item in results],
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# ch05 Source_Chunks 与 Word 正式稿对应关系报告",
        "",
        "说明：第五章 Source_Chunks 多为知识摘要，本报告建立概念依据对应关系，不将摘要标记为教材逐字原文。",
        "",
        "## 结果概览",
        "",
        f"- Source_Chunks：{len(results)}",
        f"- 高置信度：{status_counts.get('high_confidence', 0)}",
        f"- 人工确认：{status_counts.get('review_confirmed', 0)}",
        f"- 中置信度：{status_counts.get('medium_confidence', 0)}",
        f"- 待人工复核：{status_counts.get('manual_review', 0)}",
        f"- 已回写确认项：{'是' if args.apply_high_confidence else '否'}",
        "",
        "## 待人工复核",
        "",
        "| Chunk | 标题 | 分数 | 候选行 | 候选文本 |",
        "|---|---|---:|---:|---|",
    ]
    manual = [item for item in results if item["status"] == "manual_review"]
    for item in manual[:100]:
        candidate = item["top_candidates"][0] if item["top_candidates"] else empty_candidate()
        text = str(candidate.get("text") or "").replace("|", "\\|")
        if len(text) > 100:
            text = text[:100] + "..."
        lines.append(
            f"| `{item['chunk_id']}` | {item.get('section_title') or ''} | "
            f"{float(candidate.get('score') or 0):.3f} | {candidate.get('line_start') or ''} | {text} |"
        )
    if not manual:
        lines.append("| - | 无 | - | - | - |")

    medium = [item for item in results if item["status"] == "medium_confidence"]
    lines.extend(
        [
            "",
            "## 中置信度待确认",
            "",
            "| Chunk | 标题 | 分数 | 候选行 | 候选文本 |",
            "|---|---|---:|---:|---|",
        ]
    )
    for item in medium:
        candidate = item["top_candidates"][0] if item["top_candidates"] else empty_candidate()
        text = str(candidate.get("text") or "").replace("|", "\\|")
        if len(text) > 100:
            text = text[:100] + "..."
        lines.append(
            f"| `{item['chunk_id']}` | {item.get('section_title') or ''} | "
            f"{float(candidate.get('score') or 0):.3f} | {candidate.get('line_start') or ''} | {text} |"
        )
    if not medium:
        lines.append("| - | 无 | - | - | - |")

    lines.extend(
        [
            "",
            "## 高置信度示例",
            "",
            "| Chunk | 标题 | 分数 | 正式稿行 | 匹配依据 |",
            "|---|---|---:|---:|---|",
        ]
    )
    high = [item for item in results if item["status"] == "high_confidence"]
    for item in high[:30]:
        candidate = item["top_candidates"][0]
        reasons = "；".join(candidate.get("reasons") or []).replace("|", "\\|")
        lines.append(
            f"| `{item['chunk_id']}` | {item.get('section_title') or ''} | "
            f"{float(candidate.get('score') or 0):.3f} | {candidate.get('line_start')} | {reasons} |"
        )

    lines.extend(
        [
            "",
            "## 人工确认示例",
            "",
            "| Chunk | 标题 | 正式稿行 | 复核说明 |",
            "|---|---|---:|---|",
        ]
    )
    reviewed = [item for item in results if item["status"] == "review_confirmed"]
    for item in reviewed[:50]:
        candidate = item["top_candidates"][0]
        reasons = candidate.get("reasons") or []
        note = str(reasons[-1] if reasons else "").replace("|", "\\|")
        lines.append(
            f"| `{item['chunk_id']}` | {item.get('section_title') or ''} | "
            f"{candidate.get('line_start')}-{candidate.get('line_end')} | {note} |"
        )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def normalize(text: str) -> str:
    return re.sub(r"[\s，。；：、“”‘’（）()《》〈〉【】\[\]—\-·/]", "", str(text or "")).lower()


def to_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [str(value)]


def title_variants(title: str, aliases: list[str]) -> list[str]:
    results = [title]
    title_norm = normalize(title)
    for alias in aliases:
        alias_norm = normalize(alias)
        if not alias_norm or alias_norm == title_norm:
            continue
        if alias in GENERIC_TERMS or len(alias_norm) < 4:
            continue
        results.append(alias)
    return results


def query_text(query: dict[str, Any]) -> str:
    return " ".join(
        part
        for part in [
            str(query.get("title") or ""),
            str(query.get("definition") or ""),
            str(query.get("excerpt") or ""),
            " ".join(query.get("terms") or []),
        ]
        if part
    )


def enhance_with_embeddings(
    results: list[dict[str, Any]],
    *,
    model: str,
    base_url: str,
    batch_size: int,
    high_threshold: float,
    medium_threshold: float,
    min_margin: float,
) -> None:
    client = OllamaEmbeddingClient(model=model, base_url=base_url)
    candidate_texts: list[str] = []
    seen_texts: set[str] = set()
    for result in results:
        for candidate in result.get("top_candidates", []):
            text = str(candidate.get("text") or "")
            if text and text not in seen_texts:
                seen_texts.add(text)
                candidate_texts.append(text)

    query_texts = [str(result.get("_query_text") or "") for result in results]
    candidate_vectors = embed_batches(client, candidate_texts, batch_size)
    query_vectors = embed_batches(client, query_texts, batch_size)
    vector_by_text = dict(zip(candidate_texts, candidate_vectors))

    for result, query_vector in zip(results, query_vectors):
        rescored = []
        for candidate in result.get("top_candidates", []):
            text = str(candidate.get("text") or "")
            similarity = cosine_similarity(query_vector, vector_by_text.get(text, []))
            lexical_score = float(candidate.get("score") or 0.0)
            semantic_boost = max(0.0, (similarity - 0.45) * 0.45)
            candidate = dict(candidate)
            candidate["lexical_score"] = round(lexical_score, 6)
            candidate["semantic_similarity"] = round(similarity, 6)
            candidate["score"] = round(min(1.0, lexical_score + semantic_boost), 6)
            candidate["reasons"] = list(candidate.get("reasons") or []) + [f"semantic:{similarity:.2f}"]
            rescored.append(candidate)
        rescored.sort(key=lambda item: float(item["score"]), reverse=True)
        result["top_candidates"] = rescored
        best = rescored[0] if rescored else empty_candidate()
        second_score = float(rescored[1]["score"]) if len(rescored) > 1 else 0.0
        margin = float(best.get("score") or 0.0) - second_score
        result["best_score"] = best.get("score", 0.0)
        result["score_margin"] = round(margin, 6)
        result["status"] = classify_status(best, margin, high_threshold, medium_threshold, min_margin)


def embed_batches(client: OllamaEmbeddingClient, texts: list[str], batch_size: int) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        vectors.extend(client.embed(texts[start : start + batch_size]))
    return vectors


def public_result(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if not key.startswith("_")}


def empty_candidate() -> dict[str, Any]:
    return {"line_start": None, "line_end": None, "score": 0.0, "reasons": [], "text": ""}


if __name__ == "__main__":
    raise SystemExit(main())
