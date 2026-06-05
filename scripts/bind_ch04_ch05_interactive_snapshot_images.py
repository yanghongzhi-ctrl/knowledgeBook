from __future__ import annotations

import base64
import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


SNAPSHOTS: dict[str, list[dict[str, Any]]] = {
    "ch04": [
        {
            "resource_id": "res_ch04_003",
            "html_prefix": "4.4",
            "extract": ("json", "DATA", ["tab1", "image"]),
            "source_label": "DATA.tab1.image",
            "figure_no": "4-2",
            "description": "用于说明设计范式在设计思维、建模对象、协作方式和成果形态四个层面的构成。",
            "keywords": ["图4-2", "设计范式", "四要素", "正向设计理念"],
            "aliases": ["图4-2", "图4.2", "图 4-2", "设计范式的四要素"],
        },
        {
            "resource_id": "res_ch04_004",
            "html_prefix": "4.4",
            "extract": ("json", "DATA", ["tab2", "image"]),
            "source_label": "DATA.tab2.image",
            "figure_no": "4-3",
            "description": "用于说明道路设计从图纸表达、CAD辅助到BIM正向设计的范式演变。",
            "keywords": ["图4-3", "设计范式", "演变过程", "正向设计"],
            "aliases": ["图4-3", "图4.3", "图 4-3", "设计范式的演变过程"],
        },
        {
            "resource_id": "res_ch04_005",
            "html_prefix": "4.4",
            "extract": ("json", "DATA", ["tab3", "image"]),
            "source_label": "DATA.tab3.image",
            "figure_no": "4-4",
            "description": "用于说明道路BIM正向设计中模型驱动、规则约束、参数联动和成果交付的流程关系。",
            "keywords": ["图4-4", "道路BIM", "正向设计流程", "模型驱动"],
            "aliases": ["图4-4", "图4.4", "图 4-4", "道路BIM正向设计流程"],
        },
        {
            "resource_id": "res_ch04_006",
            "html_prefix": "4.5",
            "extract": ("json", "slides", [1, "image"]),
            "source_label": "slides[1].image",
            "figure_no": "4-5",
            "description": "用于说明道路BIM构件体系的设施、子设施、构件层级组织及其信息构成。",
            "keywords": ["图4-5", "构件体系", "层级组织", "信息构成模型"],
            "aliases": ["图4-5", "图4.5", "图 4-5", "构件层级体系及信息构成模型"],
        },
        {
            "resource_id": "res_ch04_008",
            "html_prefix": "4.6",
            "extract": ("img_alt", "道路BIM参数化驱动机制主图"),
            "source_label": "img[alt=PRR main]",
            "figure_no": "4-6",
            "description": "用于说明参数、规则、结果之间的动态驱动关系及道路BIM参数化设计逻辑。",
            "keywords": ["图4-6", "PRR", "参数", "规则", "结果", "动态驱动机制"],
            "aliases": ["图4-6", "图4.6", "图 4-6", "PRR动态驱动机制"],
        },
        {
            "resource_id": "res_ch04_009",
            "html_prefix": "4.7",
            "extract": ("img_alt", "道路BIM参数化建模应用模式主配图"),
            "source_label": "img[alt=parameterized mode]",
            "figure_no": "4-8",
            "description": "用于说明道路BIM参数化建模在模板驱动、约束驱动、规则驱动和自动化生成中的应用模式。",
            "keywords": ["图4-8", "参数化建模", "应用模式", "模板驱动", "规则驱动"],
            "aliases": ["图4-8", "图4.8", "图 4-8", "参数化建模的应用模式"],
        },
        {
            "resource_id": "res_ch04_010",
            "html_prefix": "4.8",
            "extract": ("img_alt", "道路BIM正向设计成果表达与交付主配图"),
            "source_label": "img[alt=delivery main]",
            "figure_no": "",
            "description": "用于说明道路BIM正向设计成果表达与交付的综合流程。",
            "keywords": ["成果交付", "成果表达", "交付流程", "道路BIM"],
            "aliases": ["成果交付流程示意", "道路BIM正向设计成果表达与交付"],
        },
    ],
    "ch05": [
        {
            "resource_id": "fig_5_3",
            "html_prefix": "5.2",
            "extract": ("json", "IMG", ["data"]),
            "source_label": "IMG.data",
            "figure_no": "5-3",
            "description": "展示GIS从数据采集、数据管理、空间分析到可视化输出的技术流程与功能模块。",
            "keywords": ["图5-3", "GIS", "技术流程", "功能模块", "数据流转"],
            "aliases": ["图5-3", "图5.3", "图 5-3", "GIS技术流程与功能模块"],
        },
        {
            "resource_id": "fig_5_15",
            "html_prefix": "5.8",
            "extract": ("regex", r"curvature:\{[^{}]*?image:'(data:image/[^']+)'"),
            "source_label": "THEORY.curvature.image",
            "figure_no": "5-15",
            "description": "用于说明地表曲率的凹凸变化及其在道路选线、排水和边坡判断中的含义。",
            "keywords": ["图5-15", "地表曲率", "DEM", "地形分析", "曲率图"],
            "aliases": ["图5-15", "图5.15", "图 5-15", "地表曲率图"],
        },
    ],
}

DEFERRED = {
    "ch04": {
        "res_ch04_011": "4.8脚本仅提供一张成果表达与交付综合主图，未发现可独立支撑CDE协同交付的静态图片。",
        "res_ch04_012": "4.8脚本仅提供一张成果表达与交付综合主图，未发现可独立支撑LOD与LOI阶段适配的静态图片。",
    }
}


def main() -> int:
    summary: dict[str, Any] = {}
    for chapter_id, bindings in SNAPSHOTS.items():
        summary[chapter_id] = bind_chapter(chapter_id, bindings)

    report_path = ROOT / "output/ch04_ch05_interactive_snapshot_bindings.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"report={report_path}")
    return 0


def bind_chapter(chapter_id: str, bindings: list[dict[str, Any]]) -> dict[str, Any]:
    raw_path = next((ROOT / "data/raw" / chapter_id).glob("*.json"))
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    resources = data.get("Resources", [])
    by_id = {
        str(row.get("resource_id")): row
        for row in resources
        if isinstance(row, dict) and row.get("resource_id")
    }
    asset_dir = ROOT / "assets" / chapter_id / "images"
    asset_dir.mkdir(parents=True, exist_ok=True)

    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    html_cache: dict[str, tuple[Path, str]] = {}

    for binding in bindings:
        resource_id = str(binding["resource_id"])
        row = by_id.get(resource_id)
        if row is None:
            skipped.append({"resource_id": resource_id, "reason": "resource_missing"})
            continue

        html_path, html = html_cache.setdefault(
            str(binding["html_prefix"]),
            load_html(chapter_id, str(binding["html_prefix"])),
        )
        data_uri = extract_data_uri(html, tuple(binding["extract"]))
        output_path = asset_dir / f"{resource_id}.png"
        size = save_data_uri_png(data_uri, output_path)
        apply_binding(row, binding, output_path, html_path, size)
        applied.append(
            {
                "resource_id": resource_id,
                "title": row.get("title"),
                "file_path": row.get("file_path"),
                "html": relative(html_path),
                "source_label": binding.get("source_label"),
                "size": {"width": size[0], "height": size[1]},
            }
        )

    for resource_id, note in DEFERRED.get(chapter_id, {}).items():
        row = by_id.get(resource_id)
        if row is None:
            continue
        row["status"] = "placeholder"
        row["binding_source"] = "deferred_interactive_asset_review"
        row["verification_note"] = note
        skipped.append({"resource_id": resource_id, "reason": note})

    raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "raw_path": relative(raw_path),
        "applied": applied,
        "skipped": skipped,
    }


def load_html(chapter_id: str, prefix: str) -> tuple[Path, str]:
    html_path = next((ROOT / "assets" / chapter_id / "interactive_html").glob(prefix + "*.html"))
    return html_path, html_path.read_text(encoding="utf-8", errors="ignore")


def extract_data_uri(html: str, spec: tuple[Any, ...]) -> str:
    kind = str(spec[0])
    if kind == "json":
        name = str(spec[1])
        path = list(spec[2])
        value = extract_js_json_value(html, name)
        for part in path:
            value = value[part]
        if not isinstance(value, str) or not value.startswith("data:image/"):
            raise ValueError(f"{name}.{path} is not an image data URI")
        return value
    if kind == "img_alt":
        alt = re.escape(str(spec[1]))
        pattern = rf"<img\b(?=[^>]*\balt=\"{alt}\")(?=[^>]*\bsrc=\"(data:image/[^\"]+)\")[^>]*>"
        match = re.search(pattern, html, re.S)
        if not match:
            raise ValueError(f"Cannot find img alt={spec[1]}")
        return match.group(1)
    if kind == "regex":
        match = re.search(str(spec[1]), html, re.S)
        if not match:
            raise ValueError(f"Cannot match image regex: {spec[1]}")
        return match.group(1)
    raise ValueError(f"Unsupported extractor: {kind}")


def extract_js_json_value(html: str, name: str) -> Any:
    marker = re.search(rf"\bconst\s+{re.escape(name)}\s*=", html)
    if not marker:
        raise ValueError(f"Cannot find const {name}")
    object_start = html.find("{", marker.end())
    array_start = html.find("[", marker.end())
    starts = [item for item in (object_start, array_start) if item >= 0]
    start = min(starts) if starts else -1
    if start < 0:
        raise ValueError(f"Cannot find JSON start for {name}")
    end = matching_bracket(html, start)
    return json.loads(html[start : end + 1])


def matching_bracket(text: str, start: int) -> int:
    opening = text[start]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("Unclosed JSON value")


def save_data_uri_png(data_uri: str, output_path: Path) -> tuple[int, int]:
    header, payload = data_uri.split(",", 1)
    if not header.startswith("data:image/"):
        raise ValueError("Not an image data URI")
    raw = base64.b64decode(payload)
    with Image.open(BytesIO(raw)) as image:
        converted = image.convert("RGBA") if image.mode in {"P", "LA"} else image.convert("RGB")
        converted.save(output_path, format="PNG")
        return converted.size


def apply_binding(
    row: dict[str, Any],
    binding: dict[str, Any],
    output_path: Path,
    html_path: Path,
    size: tuple[int, int],
) -> None:
    figure_no = str(binding.get("figure_no") or "")
    row["file_path"] = relative(output_path)
    row["status"] = "bound"
    row["binding_source"] = "interactive_script_snapshot"
    row["source_html"] = relative(html_path)
    row["source_label"] = binding.get("source_label")
    row["image_detail"] = {
        "format": "png",
        "width": size[0],
        "height": size[1],
        "source": "interactive_script_embedded_data_uri",
        "figure_no": figure_no,
    }
    row["description"] = binding.get("description") or row.get("description") or ""
    row["qa_use"] = "当学生问题涉及该图示主题、图号或资源查看意图时推荐作为辅助资源。"
    row["verification_note"] = (
        "正式稿正文可确认该图示主题；正式稿未提供可稳定抽取的独立嵌入图片，"
        "本资源依据对应互动脚本内嵌教学图静态提取绑定。"
    )
    row["keywords"] = unique_list(list(row.get("keywords") or []) + list(binding.get("keywords") or []))
    row["reference_aliases"] = unique_list(
        list(row.get("reference_aliases") or []) + list(binding.get("aliases") or [])
    )
    if figure_no:
        row["formal_figure_no"] = figure_no


def unique_list(items: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
