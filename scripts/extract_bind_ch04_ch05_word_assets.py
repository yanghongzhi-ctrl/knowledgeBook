from __future__ import annotations

import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(r"F:\编书\道路工程数字设计方法\05脚本及图片素材")
DOCX = next(SOURCE_ROOT.glob("*.docx"))

CHAPTERS = {
    "ch04": {
        "marker": "道路BIM正向设计的原理与方法",
        "next_marker": "GIS理论基础与空间分析方法",
        "raw": next((ROOT / "data/raw/ch04").glob("*.json")),
        "figure_resources": {
            "4-1": "res_ch04_002",
            "4-2": "res_ch04_003",
            "4-3": "res_ch04_004",
            "4-4": "res_ch04_005",
            "4-5": "res_ch04_006",
            "4-6": "res_ch04_008",
        },
        "table_resources": {"4-1": "res_ch04_001", "4-2": "res_ch04_007"},
    },
    "ch05": {
        "marker": "GIS理论基础与空间分析方法",
        "next_marker": "AutoCAD绘图基础与应用技巧",
        "raw": next((ROOT / "data/raw/ch05").glob("*.json")),
        "figure_resources": {
            "5-4": "fig_5_4",
            "5-5": "fig_5_5",
            "5-7": "fig_5_7",
            "5-14": "fig_5_14",
            "5-19": "fig_5_19",
            "5-21": "fig_5_21",
            "5-22": "fig_5_22",
        },
        "table_resources": {"5-2": "table_5_2"},
    },
}

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

FIGURE_RE = re.compile(r"图\s*([45])\s*[-－—.．]\s*(\d+)")
TABLE_RE = re.compile(r"表\s*([45])\s*[-－—.．]\s*(\d+)")


@dataclass
class Block:
    kind: str
    text: str
    rel_ids: list[str]
    rows: list[list[str]]


def main() -> int:
    blocks, rels = read_docx(DOCX)
    for chapter_id, config in CHAPTERS.items():
        process_chapter(chapter_id, config, blocks, rels)
    return 0


def read_docx(path: Path) -> tuple[list[Block], dict[str, str]]:
    with zipfile.ZipFile(path) as docx:
        root = ET.fromstring(docx.read("word/document.xml"))
        rels = read_relationships(docx)
    body = root.find("w:body", NS)
    if body is None:
        return [], rels
    blocks: list[Block] = []
    for child in list(body):
        tag = strip_ns(child.tag)
        if tag == "p":
            blocks.append(parse_paragraph(child))
        elif tag == "tbl":
            blocks.append(parse_table(child))
    return blocks, rels


def read_relationships(docx: zipfile.ZipFile) -> dict[str, str]:
    root = ET.fromstring(docx.read("word/_rels/document.xml.rels"))
    result: dict[str, str] = {}
    for rel in root.findall("rel:Relationship", NS):
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rel_id and target:
            result[rel_id] = target
    return result


def parse_paragraph(node: ET.Element) -> Block:
    text = clean_text("".join(item.text or "" for item in node.findall(".//w:t", NS)))
    rel_ids = [
        str(blip.attrib[f"{{{NS['r']}}}embed"])
        for blip in node.findall(".//a:blip", NS)
        if f"{{{NS['r']}}}embed" in blip.attrib
    ]
    return Block(kind="paragraph", text=text, rel_ids=rel_ids, rows=[])


def parse_table(node: ET.Element) -> Block:
    rows: list[list[str]] = []
    for tr in node.findall("./w:tr", NS):
        cells = [clean_text("".join(tc.itertext())) for tc in tr.findall("./w:tc", NS)]
        if any(cells):
            rows.append(cells)
    text = "\n".join(" | ".join(row) for row in rows)
    return Block(kind="table", text=text, rel_ids=[], rows=rows)


def process_chapter(
    chapter_id: str,
    config: dict[str, Any],
    blocks: list[Block],
    rels: dict[str, str],
) -> None:
    chapter_blocks = chapter_slice(blocks, str(config["marker"]), str(config["next_marker"]))
    raw_path = Path(config["raw"])
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    resources = {
        str(row.get("resource_id")): row
        for row in data.get("Resources", [])
        if isinstance(row, dict) and row.get("resource_id")
    }

    asset_dir = ROOT / "assets" / chapter_id / "images"
    asset_dir.mkdir(parents=True, exist_ok=True)
    figure_candidates = collect_figure_candidates(chapter_blocks, rels)
    copied = bind_figures(
        chapter_id,
        figure_candidates,
        dict(config["figure_resources"]),
        resources,
        asset_dir,
    )
    structured_tables = bind_tables(
        chapter_id,
        chapter_blocks,
        dict(config["table_resources"]),
        resources,
    )
    raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report_dir = ROOT / "output" / f"{chapter_id}_rag_engine" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{chapter_id}_word_asset_binding_report.json"
    report_path.write_text(
        json.dumps(
            {
                "chapter_id": chapter_id,
                "docx": str(DOCX),
                "chapter_blocks": len(chapter_blocks),
                "figure_candidates": figure_candidates,
                "copied_figures": copied,
                "structured_tables": structured_tables,
                "unmapped_figure_numbers": sorted(
                    set(figure_candidates) - set(config["figure_resources"])
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"{chapter_id}: candidates={len(figure_candidates)} "
        f"copied={len(copied)} tables={len(structured_tables)} report={report_path}"
    )


def chapter_slice(blocks: list[Block], marker: str, next_marker: str) -> list[Block]:
    start_candidates = [
        index
        for index, block in enumerate(blocks)
        if block.text.startswith(marker) and not re.search(r"\d+$", block.text)
    ]
    if not start_candidates:
        start_candidates = [index for index, block in enumerate(blocks) if block.text.startswith(marker)]
    if not start_candidates:
        raise ValueError(f"Cannot find chapter marker: {marker}")
    start = start_candidates[-1]
    end_candidates = [
        index
        for index, block in enumerate(blocks[start + 1 :], start + 1)
        if block.text.startswith(next_marker)
    ]
    end = end_candidates[0] if end_candidates else len(blocks)
    return blocks[start:end]


def collect_figure_candidates(blocks: list[Block], rels: dict[str, str]) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for index, block in enumerate(blocks):
        if not block.rel_ids:
            continue
        label, context, distance = nearest_label(blocks, index, FIGURE_RE)
        if not label or label in candidates:
            continue
        rel_id = next((item for item in block.rel_ids if item in rels), "")
        if not rel_id:
            continue
        candidates[label] = {
            "label": f"图 {label}",
            "context": context,
            "distance": distance,
            "rel_id": rel_id,
            "source_media": rels[rel_id],
            "image_block_index": index,
        }
    return candidates


def nearest_label(
    blocks: list[Block],
    index: int,
    pattern: re.Pattern[str],
    max_distance: int = 8,
) -> tuple[str, str, int]:
    for distance in range(0, max_distance + 1):
        indexes = [index] if distance == 0 else [index - distance, index + distance]
        for candidate_index in indexes:
            if candidate_index < 0 or candidate_index >= len(blocks):
                continue
            text = blocks[candidate_index].text
            match = pattern.search(text)
            if match:
                return f"{match.group(1)}-{match.group(2)}", text, distance
    return "", "", -1


def bind_figures(
    chapter_id: str,
    candidates: dict[str, dict[str, Any]],
    mapping: dict[str, str],
    resources: dict[str, dict[str, Any]],
    asset_dir: Path,
) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    with zipfile.ZipFile(DOCX) as docx:
        for figure_no, resource_id in mapping.items():
            candidate = candidates.get(figure_no)
            row = resources.get(resource_id)
            if not candidate or row is None:
                continue
            media_name = str(candidate["source_media"])
            if not media_name.startswith("word/"):
                media_name = "word/" + media_name.lstrip("/")
            if media_name not in docx.namelist():
                continue
            suffix = Path(media_name).suffix.lower() or ".png"
            output_path = asset_dir / f"{resource_id}{suffix}"
            with docx.open(media_name) as src, output_path.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            relative_path = output_path.relative_to(ROOT).as_posix()
            row["file_path"] = relative_path
            row["status"] = "bound"
            row["resource_type"] = "image"
            row["binding_source"] = DOCX.name
            row["binding_note"] = f"依据正式稿图 {figure_no} 邻近正文自动绑定。"
            row["reference_aliases"] = unique_list(
                (row.get("reference_aliases") or [])
                + [f"图{figure_no}", f"图 {figure_no}", figure_no]
            )
            copied.append(
                {
                    "figure_no": figure_no,
                    "resource_id": resource_id,
                    "file_path": relative_path,
                    "context": candidate["context"],
                    "distance": candidate["distance"],
                    "source_media": media_name,
                }
            )
    return copied


def bind_tables(
    chapter_id: str,
    blocks: list[Block],
    mapping: dict[str, str],
    resources: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    structured: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        if block.kind != "table" or not block.rows:
            continue
        label, context, distance = nearest_label(blocks, index, TABLE_RE)
        resource_id = mapping.get(label)
        row = resources.get(resource_id or "")
        if not label or row is None:
            continue
        columns = block.rows[0]
        table_rows = [
            {columns[col]: cells[col] if col < len(cells) else "" for col in range(len(columns))}
            for cells in block.rows[1:]
        ]
        detail = {
            "label": f"表{label}",
            "label_key": label,
            "title": str(row.get("title") or f"表{label}"),
            "columns": columns,
            "rows": table_rows,
            "context_before": context,
            "related_answer_cards": related_cards(row, resources),
            "source": f"output/{chapter_id}_rag_engine/reports/{chapter_id}_word_extract.txt",
            "source_document": DOCX.name,
            "extraction_status": "extracted" if columns and table_rows else "needs_manual_review",
        }
        row["table_detail"] = detail
        row["status"] = "structured" if detail["extraction_status"] == "extracted" else row.get("status")
        row["reference_aliases"] = unique_list(
            (row.get("reference_aliases") or [])
            + [f"表{label}", f"表 {label}", label]
        )
        structured.append(
            {
                "table_no": label,
                "resource_id": resource_id,
                "columns": len(columns),
                "rows": len(table_rows),
                "context": context,
                "distance": distance,
            }
        )
    return structured


def related_cards(row: dict[str, Any], resources: dict[str, dict[str, Any]]) -> list[str]:
    del resources
    value = row.get("related_answer_cards")
    return value if isinstance(value, list) else []


def unique_list(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u3000", " ")).strip()


def strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


if __name__ == "__main__":
    raise SystemExit(main())
