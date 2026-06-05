from __future__ import annotations

import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]

CHAPTERS = {
    "ch02": {
        "docx": Path(r"D:\道路工程数字设计方法\文稿\第二章\第二章 道路建模的图形原理与三维表达.docx"),
        "raw": next((ROOT / "data/raw/ch02").glob("*.json")),
        "figure_prefix": "2",
        "resource_prefix": "ch02_fig_",
    },
    "ch03": {
        "docx": Path(r"D:\道路工程数字设计方法\文稿\第三章\第三章 道路CAD系统的设计原理.docx"),
        "raw": next((ROOT / "data/raw/ch03").glob("*.json")),
        "figure_prefix": "3",
        "resource_prefix": "fig_",
    },
}

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


@dataclass
class Block:
    kind: str
    text: str
    rel_ids: list[str]


@dataclass
class ImageMatch:
    figure_no: str
    caption: str
    rel_id: str
    source_name: str
    target_path: str
    resource_id: str


def main() -> int:
    for chapter_id, config in CHAPTERS.items():
        process_chapter(chapter_id, config)
    return 0


def process_chapter(chapter_id: str, config: dict[str, object]) -> None:
    docx_path = Path(config["docx"])
    raw_path = Path(config["raw"])
    figure_prefix = str(config["figure_prefix"])
    resource_prefix = str(config["resource_prefix"])

    blocks, rels = read_docx_blocks(docx_path)
    matches = match_images(blocks, rels, figure_prefix, resource_prefix)
    text_lines = [block.text for block in blocks if block.text.strip()]
    captions = [line for line in text_lines if is_caption(line, figure_prefix)]

    asset_dir = ROOT / "assets" / chapter_id / "images"
    asset_dir.mkdir(parents=True, exist_ok=True)
    copied = copy_matched_images(docx_path, matches, asset_dir)

    data = json.loads(raw_path.read_text(encoding="utf-8"))
    updated = update_resources(data, chapter_id, matches, copied)
    raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report_dir = ROOT / "output" / f"{chapter_id}_rag_engine" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / f"{chapter_id}_word_extract.txt").write_text("\n".join(text_lines) + "\n", encoding="utf-8")
    (report_dir / f"{chapter_id}_word_asset_report.json").write_text(
        json.dumps(
            {
                "chapter_id": chapter_id,
                "docx": str(docx_path),
                "paragraph_or_table_blocks": len(text_lines),
                "captions": captions,
                "image_matches": [
                    {
                        "figure_no": match.figure_no,
                        "caption": match.caption,
                        "resource_id": match.resource_id,
                        "file_path": copied.get(match.resource_id),
                        "source_name": match.source_name,
                    }
                    for match in matches
                ],
                "updated_resources": updated,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"{chapter_id}: text_blocks={len(text_lines)} captions={len(captions)} "
        f"matched_images={len(matches)} updated_resources={updated}"
    )


def read_docx_blocks(path: Path) -> tuple[list[Block], dict[str, str]]:
    with zipfile.ZipFile(path) as docx:
        rels = read_relationships(docx)
        root = ET.fromstring(docx.read("word/document.xml"))

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
    rels: dict[str, str] = {}
    root = ET.fromstring(docx.read("word/_rels/document.xml.rels"))
    for rel in root.findall("rel:Relationship", NS):
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rel_id and target:
            rels[rel_id] = target
    return rels


def parse_paragraph(node: ET.Element) -> Block:
    texts = [text for text in node.itertext()]
    rel_ids = [
        blip.attrib.get(f"{{{NS['r']}}}embed")
        for blip in node.findall(".//a:blip", NS)
        if blip.attrib.get(f"{{{NS['r']}}}embed")
    ]
    return Block(kind="paragraph", text=clean_text("".join(texts)), rel_ids=[str(item) for item in rel_ids])


def parse_table(node: ET.Element) -> Block:
    rows: list[str] = []
    for tr in node.findall(".//w:tr", NS):
        cells = []
        for tc in tr.findall("./w:tc", NS):
            cells.append(clean_text("".join(tc.itertext())))
        if any(cells):
            rows.append(" | ".join(cells))
    return Block(kind="table", text="\n".join(rows), rel_ids=[])


def match_images(
    blocks: list[Block],
    rels: dict[str, str],
    figure_prefix: str,
    resource_prefix: str,
) -> list[ImageMatch]:
    matches: list[ImageMatch] = []
    used_rel_ids: set[str] = set()
    caption_re = re.compile(rf"图\s*{re.escape(figure_prefix)}[.-](\d+(?:-\d+)?)\s*[：:、.\s]*(.+)?")

    for index, block in enumerate(blocks):
        if not block.rel_ids:
            continue
        caption = find_near_caption(blocks, index, caption_re)
        if not caption:
            continue
        figure_no, title = caption
        rel_id = next((item for item in block.rel_ids if item not in used_rel_ids), block.rel_ids[0])
        if rel_id not in rels:
            continue
        used_rel_ids.add(rel_id)
        normalized = figure_no.replace("-", "_")
        resource_id = f"{resource_prefix}{figure_prefix}_{normalized}"
        if resource_prefix == "ch02_fig_":
            resource_id = f"ch02_fig_{figure_prefix}_{normalized}"
        matches.append(
            ImageMatch(
                figure_no=f"{figure_prefix}-{figure_no}",
                caption=f"图{figure_prefix}-{figure_no} {title or ''}".strip(),
                rel_id=rel_id,
                source_name=rels[rel_id],
                target_path=rels[rel_id],
                resource_id=resource_id,
            )
        )
    return dedupe_matches(matches)


def find_near_caption(
    blocks: list[Block],
    image_index: int,
    caption_re: re.Pattern[str],
) -> tuple[str, str] | None:
    for offset in range(0, 7):
        for index in (image_index + offset, image_index - offset):
            if index < 0 or index >= len(blocks):
                continue
            text = blocks[index].text.strip()
            if not text:
                continue
            match = caption_re.search(text)
            if match:
                return match.group(1), clean_text(match.group(2) or "")
    return None


def dedupe_matches(matches: list[ImageMatch]) -> list[ImageMatch]:
    result: list[ImageMatch] = []
    seen: set[str] = set()
    for match in matches:
        if match.resource_id in seen:
            continue
        seen.add(match.resource_id)
        result.append(match)
    return result


def copy_matched_images(docx_path: Path, matches: list[ImageMatch], asset_dir: Path) -> dict[str, str]:
    copied: dict[str, str] = {}
    with zipfile.ZipFile(docx_path) as docx:
        for match in matches:
            media_name = match.target_path
            if not media_name.startswith("word/"):
                media_name = "word/" + media_name.lstrip("/")
            suffix = Path(media_name).suffix.lower() or ".png"
            filename = f"{match.resource_id}{suffix}"
            output_path = asset_dir / filename
            with docx.open(media_name) as src, output_path.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            copied[match.resource_id] = output_path.relative_to(ROOT).as_posix()
    return copied


def update_resources(
    data: dict[str, object],
    chapter_id: str,
    matches: list[ImageMatch],
    copied: dict[str, str],
) -> int:
    resources = data.get("Resources", [])
    if not isinstance(resources, list):
        return 0

    by_id = {
        str(row.get("resource_id")): row
        for row in resources
        if isinstance(row, dict) and row.get("resource_id")
    }
    updated = 0
    for match in matches:
        row = by_id.get(match.resource_id)
        if row is None and chapter_id == "ch03":
            row = by_id.get(match.resource_id.replace("fig_3_", "ch03_fig_3_"))
        if row is None:
            continue
        file_path = copied.get(match.resource_id)
        if not file_path:
            continue
        row["file_path"] = file_path
        row["status"] = "bound"
        row["resource_type"] = "image"
        row["caption_or_name"] = match.caption
        row["title"] = str(row.get("title") or match.caption).strip()
        keywords = row.get("keywords")
        if not isinstance(keywords, list) or not keywords:
            row["keywords"] = keywords_from_caption(match.caption)
        updated += 1
    return updated


def is_caption(text: str, figure_prefix: str) -> bool:
    return bool(re.search(rf"图\s*{re.escape(figure_prefix)}[.-]\d+", text))


def keywords_from_caption(caption: str) -> list[str]:
    text = re.sub(r"^图\s*\d+[.-]\d+(?:-\d+)?\s*", "", caption).strip()
    parts = re.split(r"[，,、/与和及\s]+", text)
    return [part for part in parts if len(part) >= 2][:8]


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u3000", " ")).strip()


def strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


if __name__ == "__main__":
    raise SystemExit(main())
