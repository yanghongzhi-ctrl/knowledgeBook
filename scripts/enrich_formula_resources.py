from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = {
    "ch02": {
        "raw": ROOT / "data/raw/ch02",
        "word_extract": ROOT / "output/ch02_rag_engine/reports/ch02_word_extract.txt",
    },
    "ch03": {
        "raw": ROOT / "data/raw/ch03",
        "word_extract": ROOT / "output/ch03_rag_engine/reports/ch03_word_extract.txt",
    },
    "ch05": {
        "raw": ROOT / "data/raw/ch05",
        "word_extract": ROOT / "output/ch05_rag_engine/reports/ch05_word_extract.txt",
    },
}

LABEL_RE = re.compile(r"[（(]\s*(\d+)\s*[-－]\s*(\d+)\s*[）)]")
PROSE_FORMULA_MARKERS = ("按式", "由式", "采用式", "计算公式如", "可按式", "则", "当", "式中", "其中", "符号")


@dataclass
class FormulaOccurrence:
    label_key: str
    label_text: str
    expression: str
    context_before: str
    context_after: str
    variable_lines: list[str]
    line_no: int


def main() -> int:
    summary: dict[str, Any] = {}
    for chapter_id, paths in CHAPTERS.items():
        raw_path = next(paths["raw"].glob("*.json"))
        data = json.loads(raw_path.read_text(encoding="utf-8"))
        occurrences = extract_formula_occurrences(paths["word_extract"])
        chapter_summary = enrich_chapter(data, occurrences, chapter_id)
        raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary[chapter_id] = chapter_summary

    output = ROOT / "output/formula_resource_enrichment_report.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"report={output}")
    return 0


def extract_formula_occurrences(path: Path) -> dict[str, list[FormulaOccurrence]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    by_label: dict[str, list[FormulaOccurrence]] = {}
    for idx, line in enumerate(lines):
        matches = list(LABEL_RE.finditer(line))
        if not matches:
            continue
        for match in matches:
            chapter_no, formula_no = match.group(1), match.group(2)
            label_key = f"{chapter_no}-{formula_no}"
            before = line[: match.start()].strip(" \t:：，,。")
            expression = before if is_formula_expression(before) else ""
            if not expression and before:
                expression = nearest_formula_line_after(lines, idx, label_key) or nearest_formula_line_before(lines, idx, label_key)
            if not expression:
                expression = nearest_formula_line_before(lines, idx, label_key) or nearest_formula_line_after(lines, idx, label_key)
            occurrence = FormulaOccurrence(
                label_key=label_key,
                label_text=f"（{label_key}）",
                expression=cleanup_formula(expression),
                context_before=nearest_context_before(lines, idx),
                context_after=nearest_context_after(lines, idx, match.end()),
                variable_lines=collect_variable_lines(lines, idx + 1),
                line_no=idx + 1,
            )
            by_label.setdefault(label_key, []).append(occurrence)
    return by_label


def nearest_formula_line_before(lines: list[str], idx: int, label_key: str) -> str:
    for offset in range(1, 4):
        prev = lines[idx - offset].strip() if idx - offset >= 0 else ""
        if prev and is_formula_expression(prev) and formula_line_matches_label(prev, label_key):
            return prev
    return ""


def nearest_formula_line_after(lines: list[str], idx: int, label_key: str) -> str:
    for offset in range(1, 4):
        nxt = lines[idx + offset].strip() if idx + offset < len(lines) else ""
        if nxt and is_formula_expression(nxt) and formula_line_matches_label(nxt, label_key):
            return nxt
    return ""


def formula_line_matches_label(text: str, label_key: str) -> bool:
    labels = {f"{m.group(1)}-{m.group(2)}" for m in LABEL_RE.finditer(text)}
    return not labels or label_key in labels


def nearest_context_before(lines: list[str], idx: int) -> str:
    candidates: list[str] = []
    for offset in range(1, 4):
        prev = lines[idx - offset].strip() if idx - offset >= 0 else ""
        if prev and not looks_like_formula(prev):
            candidates.append(prev)
    return cleanup_text(candidates[0] if candidates else "")


def nearest_context_after(lines: list[str], idx: int, label_end: int) -> str:
    same_line_tail = lines[idx][label_end:].strip(" \t:：，,。")
    if same_line_tail:
        return cleanup_text(same_line_tail)
    for offset in range(1, 4):
        nxt = lines[idx + offset].strip() if idx + offset < len(lines) else ""
        if nxt and not looks_like_formula(nxt):
            return cleanup_text(nxt)
    return ""


def collect_variable_lines(lines: list[str], start_idx: int) -> list[str]:
    result: list[str] = []
    for idx in range(start_idx, min(len(lines), start_idx + 5)):
        line = lines[idx].strip()
        if not line:
            continue
        if LABEL_RE.search(line) and looks_like_formula(line):
            break
        if any(marker in line for marker in ("式中", "其中", "表中符号", "符号的意义")):
            result.append(cleanup_text(line))
            continue
        if result and ("—" in line or "——" in line or "=" in line or "为" in line):
            result.append(cleanup_text(line))
            continue
        if result:
            break
    return result[:5]


def looks_like_formula(text: str) -> bool:
    compact = text.replace(" ", "")
    if LABEL_RE.search(compact):
        compact = LABEL_RE.sub("", compact)
    operators = sum(compact.count(ch) for ch in "=+-*/×÷√∑ΣπΠ≤≥<>")
    latin = len(re.findall(r"[A-Za-zα-ωΑ-Ω]", compact))
    digits = len(re.findall(r"\d", compact))
    return bool(compact) and (operators >= 1 or latin + digits >= 4) and len(compact) <= 220


def is_formula_expression(text: str) -> bool:
    return looks_like_formula(text) and not any(marker in text for marker in PROSE_FORMULA_MARKERS)


def cleanup_formula(text: str) -> str:
    text = cleanup_text(text)
    text = LABEL_RE.sub("", text)
    text = text.replace("​​​​​​​​​​​", " ").replace("鈥嬧€嬧€嬧€嬧€嬧€", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def cleanup_text(text: str) -> str:
    text = str(text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def enrich_chapter(data: dict[str, Any], occurrences: dict[str, list[FormulaOccurrence]], chapter_id: str) -> dict[str, Any]:
    kps_by_formula = related_kps_by_formula(data)
    cards_by_formula = related_cards_by_formula(data)
    formula_resources = [r for r in data.get("Resources", []) if r.get("resource_type") == "formula"]
    enriched = 0
    unresolved: list[str] = []
    duplicate_labels: dict[str, int] = {}

    for row in formula_resources:
        label_key = formula_key_from_resource(str(row.get("resource_id") or ""), str(row.get("title") or ""))
        hits = occurrences.get(label_key, [])
        if len(hits) > 1:
            duplicate_labels[label_key] = len(hits)
        hit = select_best_occurrence(hits)
        related_kps = unique_list((row.get("related_kps") or []) + kps_by_formula.get(str(row.get("resource_id")), []))
        related_cards = cards_by_formula.get(str(row.get("resource_id")), [])
        detail = {
            "label": f"公式（{label_key}）" if label_key else str(row.get("title") or row.get("resource_id")),
            "label_key": label_key,
            "expression": hit.expression if hit else "",
            "context_before": hit.context_before if hit else "",
            "context_after": hit.context_after if hit else "",
            "variables": hit.variable_lines if hit else [],
            "related_answer_cards": related_cards,
            "source": str((ROOT / f"output/{chapter_id}_rag_engine/reports/{chapter_id}_word_extract.txt").relative_to(ROOT)),
            "source_line": hit.line_no if hit else None,
            "extraction_status": "extracted" if hit and hit.expression else "needs_manual_review",
        }
        row["formula_detail"] = detail
        row["related_kps"] = related_kps
        row["qa_use"] = row.get("qa_use") or "当学生询问对应计算公式、变量含义或计算流程时作为证据资源。"
        row["teaching_use"] = row.get("teaching_use") or "用于计算类知识点解释和例题设计。"
        row["status"] = "structured" if detail["extraction_status"] == "extracted" else row.get("status") or "placeholder"
        keywords = unique_list((row.get("keywords") or []) + [detail["label"], label_key, row.get("title") or ""])
        row["keywords"] = [item for item in keywords if item]
        if hit and hit.expression:
            enriched += 1
        else:
            unresolved.append(str(row.get("resource_id")))

    return {
        "formula_resources": len(formula_resources),
        "enriched": enriched,
        "unresolved": unresolved,
        "duplicate_labels": duplicate_labels,
    }


def select_best_occurrence(hits: list[FormulaOccurrence]) -> FormulaOccurrence | None:
    if not hits:
        return None

    def score(hit: FormulaOccurrence) -> tuple[int, int, int, int]:
        expression = hit.expression or ""
        return (
            1 if is_formula_expression(expression) else 0,
            0 if any(marker in expression for marker in PROSE_FORMULA_MARKERS) else 1,
            1 if "=" in expression else 0,
            min(len(expression), 220),
        )

    return max(hits, key=score)


def formula_key_from_resource(resource_id: str, title: str) -> str:
    match = re.search(r"(?:formula|公式|式)[_\s（(]*(\d+)[_\-－\s]*(\d+)", resource_id + " " + title)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    match = LABEL_RE.search(title)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return ""


def related_kps_by_formula(data: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for kp in data.get("Knowledge_Points", []):
        kp_id = str(kp.get("kp_id") or "")
        for formula_id in kp.get("related_formulas") or []:
            result.setdefault(str(formula_id), []).append(kp_id)
    return result


def related_cards_by_formula(data: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for card in data.get("Answer_Cards", []):
        answer_id = str(card.get("answer_id") or "")
        for resource_id in card.get("recommended_resources") or []:
            if "formula" in str(resource_id):
                result.setdefault(str(resource_id), []).append(answer_id)
    return result


def unique_list(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
