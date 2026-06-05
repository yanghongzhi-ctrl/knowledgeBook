from __future__ import annotations

import json
import re
import zipfile
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
    },
    "ch05": {
        "marker": "GIS理论基础与空间分析方法",
        "next_marker": "AutoCAD绘图基础与应用技巧",
        "raw": next((ROOT / "data/raw/ch05").glob("*.json")),
    },
}

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
}


def main() -> int:
    blocks = read_docx_blocks(DOCX)
    for chapter_id, config in CHAPTERS.items():
        text_lines = extract_chapter(blocks, str(config["marker"]), str(config["next_marker"]))
        verify_package(chapter_id, Path(config["raw"]), text_lines)
    return 0


def read_docx_blocks(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as docx:
        root = ET.fromstring(docx.read("word/document.xml"))
    blocks: list[str] = []
    for paragraph in root.findall(".//w:p", NS):
        text = paragraph_text(paragraph)
        if text:
            blocks.append(text)
    return blocks


def paragraph_text(paragraph: ET.Element) -> str:
    parts = [
        node.text or ""
        for node in paragraph.iter()
        if strip_namespace(node.tag) == "t"
    ]
    return clean_text("".join(parts))


def strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def extract_chapter(blocks: list[str], marker: str, next_marker: str) -> list[str]:
    start_candidates = [
        index
        for index, text in enumerate(blocks)
        if text.startswith(marker) and not re.search(r"\d+$", text)
    ]
    if not start_candidates:
        start_candidates = [index for index, text in enumerate(blocks) if text.startswith(marker)]
    if not start_candidates:
        raise ValueError(f"Cannot find chapter marker: {marker}")
    start = start_candidates[-1]
    end_candidates = [index for index, text in enumerate(blocks[start + 1 :], start + 1) if text.startswith(next_marker)]
    end = end_candidates[0] if end_candidates else len(blocks)
    return blocks[start:end]


def verify_package(chapter_id: str, raw_path: Path, text_lines: list[str]) -> None:
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    word_text = "\n".join(text_lines)
    normalized_word = normalize_text(word_text)
    counts = {"exact": 0, "partial": 0, "concept_supported": 0, "unverified": 0, "empty": 0}
    for row in data.get("Source_Chunks", []):
        if not isinstance(row, dict):
            continue
        excerpt = str(row.get("source_excerpt") or row.get("chunk_summary") or "").strip()
        status = verification_status(excerpt, normalized_word)
        row["word_verification"] = status
        row["verification_source"] = DOCX.name
        counts[status] += 1

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        data["metadata"] = metadata
    metadata["word_manuscript"] = DOCX.name
    metadata["word_verification"] = counts

    raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_dir = ROOT / "output" / f"{chapter_id}_rag_engine" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / f"{chapter_id}_word_extract.txt").write_text(word_text + "\n", encoding="utf-8")
    (report_dir / f"{chapter_id}_word_verification.json").write_text(
        json.dumps(
            {
                "chapter_id": chapter_id,
                "docx": str(DOCX),
                "text_blocks": len(text_lines),
                "text_characters": len(word_text),
                "source_chunk_verification": counts,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{chapter_id}: blocks={len(text_lines)} chars={len(word_text)} verification={counts}")


def verification_status(excerpt: str, normalized_word: str) -> str:
    normalized_excerpt = normalize_text(excerpt)
    if not normalized_excerpt:
        return "empty"
    if normalized_excerpt in normalized_word:
        return "exact"
    probe_length = min(40, len(normalized_excerpt))
    if probe_length >= 16 and normalized_excerpt[:probe_length] in normalized_word:
        return "partial"
    window = min(20, len(normalized_excerpt))
    if window >= 12:
        step = max(1, window // 2)
        for start in range(0, len(normalized_excerpt) - window + 1, step):
            if normalized_excerpt[start : start + window] in normalized_word:
                return "partial"
    support_window = min(8, len(normalized_excerpt))
    if support_window >= 6:
        matches = 0
        for start in range(0, len(normalized_excerpt) - support_window + 1, support_window):
            if normalized_excerpt[start : start + support_window] in normalized_word:
                matches += 1
            if matches >= 2:
                return "concept_supported"
    return "unverified"


def normalize_text(text: str) -> str:
    return re.sub(r"[\s，。；：、“”‘’（）()《》〈〉【】\[\]—\-·]", "", text)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u3000", " ")).strip()


if __name__ == "__main__":
    raise SystemExit(main())
