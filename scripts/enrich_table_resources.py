from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = {
    "ch02": {
        "raw": ROOT / "data/raw/ch02",
        "word_extract": ROOT / "output/ch02_rag_engine/reports/ch02_word_extract.txt",
    },
}

TABLE_LABEL_RE = re.compile(r"(?:表)\s*(\d+)\s*[-－]\s*(\d+)")


def main() -> int:
    summary: dict[str, Any] = {}
    for chapter_id, paths in CHAPTERS.items():
        raw_path = next(paths["raw"].glob("*.json"))
        data = json.loads(raw_path.read_text(encoding="utf-8"))
        tables = extract_tables(paths["word_extract"])
        summary[chapter_id] = enrich_chapter(data, tables)
        raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    output = ROOT / "output/table_resource_enrichment_report.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"report={output}")
    return 0


def extract_tables(path: Path) -> dict[str, dict[str, Any]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    tables: dict[str, dict[str, Any]] = {}
    for idx, line in enumerate(lines):
        if line == "规则格网DEM和不规则三角网（TIN）DEM的对比":
            parsed = parse_pipe_table(lines, idx + 1)
            tables["2-1"] = {
                "label": "表2-1",
                "title": line,
                "context_before": nearest_context_before(lines, idx),
                **parsed,
                "source_line": idx + 1,
            }
        elif line == "线框、表面和实体模型特点及表达能力":
            parsed = parse_pipe_table(lines, idx + 1)
            tables["2-2"] = {
                "label": "表2-2",
                "title": line,
                "context_before": nearest_context_before(lines, idx),
                **parsed,
                "source_line": idx + 1,
            }
    return tables


def parse_pipe_table(lines: list[str], start_idx: int) -> dict[str, Any]:
    table_lines: list[str] = []
    for line in lines[start_idx : start_idx + 12]:
        if "|" not in line:
            if table_lines:
                break
            continue
        table_lines.append(line)
    if not table_lines:
        return {"columns": [], "rows": [], "extraction_status": "needs_manual_review"}

    columns = [cell.strip() for cell in table_lines[0].split("|")]
    rows = []
    for line in table_lines[1:]:
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) < len(columns):
            continue
        rows.append({columns[i]: cells[i] for i in range(len(columns))})
    return {
        "columns": columns,
        "rows": rows,
        "extraction_status": "extracted" if columns and rows else "needs_manual_review",
    }


def nearest_context_before(lines: list[str], idx: int) -> str:
    for offset in range(1, 8):
        prev = lines[idx - offset].strip() if idx - offset >= 0 else ""
        if prev and "|" not in prev and not TABLE_LABEL_RE.search(prev):
            return prev
    return ""


def enrich_chapter(data: dict[str, Any], tables: dict[str, dict[str, Any]]) -> dict[str, Any]:
    resources = [row for row in data.get("Resources", []) if row.get("resource_type") == "table"]
    enriched = 0
    unresolved: list[str] = []
    cards_by_resource = related_cards_by_resource(data)

    for row in resources:
        resource_id = str(row.get("resource_id") or "")
        title = str(row.get("title") or "")
        label_key = table_key_from_resource(resource_id, title)
        table = tables.get(label_key)
        if not table:
            unresolved.append(resource_id)
            continue

        detail = {
            "label": table["label"],
            "label_key": label_key,
            "title": table["title"],
            "columns": table["columns"],
            "rows": table["rows"],
            "context_before": table.get("context_before", ""),
            "related_answer_cards": cards_by_resource.get(resource_id, []),
            "source": "output/ch02_rag_engine/reports/ch02_word_extract.txt",
            "source_line": table.get("source_line"),
            "extraction_status": table["extraction_status"],
        }
        row["table_detail"] = detail
        row["status"] = "structured" if detail["extraction_status"] == "extracted" else row.get("status") or "placeholder"
        row["qa_use"] = row.get("qa_use") or "当学生询问对应教材表格、对比项或适用场景时作为结构化资源。"
        row["teaching_use"] = row.get("teaching_use") or "用于比较类知识点解释、课堂讲解和自学复习。"
        row["keywords"] = unique_list(
            (row.get("keywords") or [])
            + [detail["label"], detail["label_key"], detail["title"], row.get("title") or ""]
            + detail["columns"]
        )
        if detail["extraction_status"] == "extracted":
            enriched += 1
        else:
            unresolved.append(resource_id)

    return {
        "table_resources": len(resources),
        "enriched": enriched,
        "unresolved": unresolved,
    }


def table_key_from_resource(resource_id: str, title: str) -> str:
    match = re.search(r"(?:table|表)[_\s]*(\d+)[_\-－\s]*(\d+)", resource_id + " " + title)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    match = TABLE_LABEL_RE.search(title)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return ""


def related_cards_by_resource(data: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for card in data.get("Answer_Cards", []):
        answer_id = str(card.get("answer_id") or "")
        for resource_id in card.get("recommended_resources") or []:
            if "table" in str(resource_id):
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
