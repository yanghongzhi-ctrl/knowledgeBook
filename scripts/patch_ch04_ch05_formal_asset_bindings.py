from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image

import extract_bind_ch04_ch05_word_assets as word_assets


ROOT = Path(__file__).resolve().parents[1]
DOCX = word_assets.DOCX

CH04_BINDINGS = {
    "res_ch04_002": {
        "media": ["word/media/image52.png"],
        "title": "图4-1 BIM内涵与基本特征",
        "figure_no": "4-1",
        "section_id": "ch04_sec01",
        "description": "展示BIM构件与参数化建模、信息集成、协同流程、4D/5D集成、可视化仿真、平台集成和全生命周期理念。",
    },
    "res_ch04_013": {
        "media": ["word/media/image58.jpeg"],
        "title": "图4-7 道路BIM参数类型及控制逻辑",
        "figure_no": "4-7",
        "section_id": "ch04_sec05",
        "description": "展示道路BIM参数类型、属性继承和联动控制逻辑。",
    },
}

CH05_BINDINGS = {
    "fig_5_1": {
        "media": ["word/media/image60.tiff"],
        "title": "图5-1 GIS的组成要素",
        "figure_no": "5-1",
        "section_id": "ch05_sec01",
        "description": "展示GIS由硬件、软件、数据、方法和人员构成。",
    },
    "fig_5_4": {
        "media": ["word/media/image63.png", "word/media/image64.png", "word/media/image65.png"],
        "title": "图5-4 按投影面形状的投影方式",
        "figure_no": "5-4",
        "section_id": "ch05_sec01",
        "description": "展示圆柱投影、圆锥投影和方位投影。",
    },
    "fig_5_5": {
        "media": ["word/media/image66.tiff"],
        "title": "图5-5 按投影面与地球相对位置的投影方式",
        "figure_no": "5-5",
        "section_id": "ch05_sec01",
        "description": "展示正轴、横轴和斜轴投影。",
    },
    "fig_5_7": {
        "media": ["word/media/image68.tiff"],
        "title": "图5-7 拓扑关系概念与原理图",
        "figure_no": "5-7",
        "section_id": "ch05_sec01",
        "description": "展示矢量数据模型中的邻接、包含和连通等拓扑关系。",
    },
    "fig_5_9": {
        "media": ["word/media/image70.tiff"],
        "title": "图5-9 点、线、面的缓冲区",
        "figure_no": "5-9",
        "section_id": "ch05_sec02",
        "description": "展示点、线、面要素的缓冲区形态。",
    },
    "fig_5_11": {
        "media": ["word/media/image72.tiff"],
        "title": "图5-11 栅格重分类",
        "figure_no": "5-11",
        "section_id": "ch05_sec02",
        "description": "展示按规则为栅格像元重新赋值的过程。",
    },
    "fig_5_14": {
        "media": ["word/media/image75.tiff"],
        "title": "图5-14 坡度和坡向图",
        "figure_no": "5-14",
        "section_id": "ch05_sec02",
        "description": "展示坡度和坡向提取结果的颜色编码表达。",
    },
    "fig_5_17": {
        "media": ["word/media/image78.tiff"],
        "title": "图5-17 视域分析原理",
        "figure_no": "5-17",
        "section_id": "ch05_sec02",
        "description": "展示观察点、目标点、地形遮挡和通视判断原理。",
    },
    "fig_5_18": {
        "media": ["word/media/image79.png"],
        "title": "图5-18 公路沿线累积视域分析",
        "figure_no": "5-18",
        "section_id": "ch05_sec02",
        "description": "展示公路沿线累积视域分析结果。",
    },
    "fig_5_19": {
        "media": ["word/media/image80.jpeg"],
        "title": "图5-19 空间分布模式",
        "figure_no": "5-19",
        "section_id": "ch05_sec03",
        "description": "展示正相关、负相关和零相关三类空间分布模式。",
    },
    "fig_5_20": {
        "media": ["word/media/image81.jpeg"],
        "title": "图5-20 灾害点的局部自相关分析",
        "figure_no": "5-20",
        "section_id": "ch05_sec03",
        "description": "展示灾害点热点、冷点和局部空间自相关分析。",
    },
    "fig_5_21": {
        "media": ["word/media/image82.tiff"],
        "title": "图5-21 变异函数的典型参数",
        "figure_no": "5-21",
        "section_id": "ch05_sec03",
        "description": "展示块金值、基台值和变程等变异函数参数。",
    },
    "fig_5_22": {
        "media": ["word/media/image83.tiff"],
        "title": "图5-22 趋势面拟合与残差分析",
        "figure_no": "5-22",
        "section_id": "ch05_sec03",
        "description": "展示趋势面拟合与残差分析。",
    },
    "fig_5_23": {
        "media": ["word/media/image84.tiff"],
        "title": "图5-23 网络数据集的核心要素",
        "figure_no": "5-23",
        "section_id": "ch05_sec04",
        "description": "展示边、节点、转向和阻抗等网络数据集核心要素。",
    },
    "fig_5_24": {
        "media": ["word/media/image85.tiff"],
        "title": "图5-24 Dijkstra算法与A*算法的原理",
        "figure_no": "5-24",
        "section_id": "ch05_sec04",
        "description": "展示Dijkstra算法与A*算法的路径搜索原理。",
    },
    "fig_5_25": {
        "media": ["word/media/image86.jpeg"],
        "title": "图5-25 OD成本矩阵分析流程",
        "figure_no": "5-25",
        "section_id": "ch05_sec04",
        "description": "展示OD成本矩阵的输入、参数、求解与输出流程。",
    },
}


def main() -> int:
    blocks, _ = word_assets.read_docx(DOCX)
    summary = {
        "ch04": patch_chapter("ch04", CH04_BINDINGS, blocks),
        "ch05": patch_chapter("ch05", CH05_BINDINGS, blocks),
    }
    report = ROOT / "output/ch04_ch05_formal_asset_bindings.json"
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"report={report}")
    return 0


def patch_chapter(
    chapter_id: str,
    bindings: dict[str, dict[str, Any]],
    blocks: list[word_assets.Block],
) -> dict[str, Any]:
    raw_path = next((ROOT / "data/raw" / chapter_id).glob("*.json"))
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    resources = data.get("Resources", [])
    if not isinstance(resources, list):
        raise ValueError(f"{chapter_id} Resources must be a list")
    by_id = {
        str(row.get("resource_id")): row
        for row in resources
        if isinstance(row, dict) and row.get("resource_id")
    }

    corrections: list[dict[str, str]] = []
    if chapter_id == "ch04":
        correct_ch04_resources(by_id, corrections)
    else:
        correct_ch05_resources(by_id, corrections)

    applied: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    asset_dir = ROOT / "assets" / chapter_id / "images"
    asset_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(DOCX) as docx:
        for resource_id, binding in bindings.items():
            row = by_id.get(resource_id)
            if row is None:
                row = new_image_resource(chapter_id, resource_id, binding)
                resources.append(row)
                by_id[resource_id] = row
            media_names = list(binding["media"])
            if any(name not in docx.namelist() for name in media_names):
                missing.append({"resource_id": resource_id, "media": media_names})
                continue
            output_path = asset_dir / f"{resource_id}.png"
            images = [load_docx_image(docx, name) for name in media_names]
            save_images_as_png(images, output_path)
            for image in images:
                image.close()
            apply_image_binding(row, binding, output_path)
            applied.append(
                {
                    "resource_id": resource_id,
                    "title": row["title"],
                    "file_path": row["file_path"],
                    "media": media_names,
                }
            )

    structured_tables = apply_formal_tables(chapter_id, data, blocks)
    raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "applied": applied,
        "missing": missing,
        "corrections": corrections,
        "structured_tables": structured_tables,
    }


def correct_ch04_resources(
    by_id: dict[str, dict[str, Any]],
    corrections: list[dict[str, str]],
) -> None:
    row = by_id.get("res_ch04_009")
    if row is not None:
        old_title = str(row.get("title") or "")
        row["title"] = "图4-8 参数化建模的应用模式"
        row["description"] = "图4-8 参数化建模的应用模式用于支撑第四章相关知识点的图表化理解。"
        row["reference_aliases"] = ["图4-8", "图4.8", "图 4-8", "4-8"]
        row["keywords"] = ["图4-8", "参数化建模", "应用模式"]
        row["verification_note"] = "正式稿正文将参数化建模应用模式标注为图4-8。"
        corrections.append({"resource_id": "res_ch04_009", "from": old_title, "to": row["title"]})


def correct_ch05_resources(
    by_id: dict[str, dict[str, Any]],
    corrections: list[dict[str, str]],
) -> None:
    legacy = by_id.pop("fig_5_10", None)
    if legacy is not None:
        legacy["resource_id"] = "fig_5_9"
        by_id["fig_5_9"] = legacy
        corrections.append({"resource_id": "fig_5_10", "from": "fig_5_10", "to": "fig_5_9"})

    legacy_comparison = by_id.pop("table_5_2", None)
    comparison = legacy_comparison or by_id.get("table_ch05_dijkstra_astar")
    if comparison is not None:
        comparison["resource_id"] = "table_ch05_dijkstra_astar"
        comparison["title"] = "Dijkstra 与 A* 算法比较表（知识库整理）"
        comparison["description"] = "依据第五章正文整理的算法比较表，不作为教材编号表引用。"
        comparison["status"] = "structured"
        comparison["verification_note"] = "正式稿未发现表5-2编号；该资源为知识库整理表。"
        comparison["reference_aliases"] = []
        comparison["table_detail"] = {
            "label": "知识库整理表",
            "label_key": "ch05-dijkstra-astar",
            "title": comparison["title"],
            "columns": ["比较维度", "Dijkstra算法", "A*算法"],
            "rows": [
                {"比较维度": "搜索策略", "Dijkstra算法": "全面扩展", "A*算法": "利用启发式函数朝目标搜索"},
                {"比较维度": "适用任务", "Dijkstra算法": "单源多点最短路径", "A*算法": "点对点快速导航"},
            ],
            "context_before": "GIS平台中常用Dijkstra算法与A*算法求解最短路径。",
            "source_document": DOCX.name,
            "extraction_status": "knowledge_base_summary",
        }
        by_id["table_ch05_dijkstra_astar"] = comparison
        if legacy_comparison is not None:
            corrections.append(
                {"resource_id": "table_5_2", "from": "table_5_2", "to": "table_ch05_dijkstra_astar"}
            )

    for resource_id, row in by_id.items():
        if row.get("resource_type") != "image":
            continue
        path = str(row.get("file_path") or "")
        if path.startswith("chapter_05/resources/"):
            row["file_path"] = ""
            row["status"] = "placeholder"
            row["verification_note"] = "原初稿文件路径未在项目中找到，等待正式稿资源绑定。"


def new_image_resource(
    chapter_id: str,
    resource_id: str,
    binding: dict[str, Any],
) -> dict[str, Any]:
    return {
        "resource_id": resource_id,
        "chapter_id": chapter_id,
        "section_id": binding["section_id"],
        "resource_type": "image",
        "title": binding["title"],
        "file_path": "",
        "description": binding["description"],
        "related_kps": [],
        "qa_use": "用于教材图解、AI回答推荐和互动脚本资源绑定。",
        "status": "placeholder",
        "keywords": keywords(binding["title"]),
    }


def apply_image_binding(
    row: dict[str, Any],
    binding: dict[str, Any],
    output_path: Path,
) -> None:
    figure_no = str(binding["figure_no"])
    row["title"] = binding["title"]
    row["description"] = binding["description"]
    row["section_id"] = binding["section_id"]
    row["file_path"] = output_path.relative_to(ROOT).as_posix()
    row["status"] = "bound"
    row["resource_type"] = "image"
    row["binding_source"] = DOCX.name
    row["binding_note"] = f"依据正式稿图{figure_no}及邻近正文人工确认绑定。"
    row["reference_aliases"] = [f"图{figure_no}", f"图 {figure_no}", figure_no]
    row["keywords"] = unique_list((row.get("keywords") or []) + keywords(binding["title"]))


def load_docx_image(docx: zipfile.ZipFile, media_name: str) -> Image.Image:
    with docx.open(media_name) as src:
        image = Image.open(src)
        image.load()
    return image.convert("RGB")


def save_images_as_png(images: list[Image.Image], output_path: Path) -> None:
    if len(images) == 1:
        images[0].save(output_path, format="PNG")
        return
    gap = 24
    max_height = max(image.height for image in images)
    width = sum(image.width for image in images) + gap * (len(images) - 1)
    canvas = Image.new("RGB", (width, max_height), "white")
    x = 0
    for image in images:
        y = (max_height - image.height) // 2
        canvas.paste(image, (x, y))
        x += image.width + gap
    canvas.save(output_path, format="PNG")
    canvas.close()


def apply_formal_tables(
    chapter_id: str,
    data: dict[str, Any],
    blocks: list[word_assets.Block],
) -> list[dict[str, Any]]:
    config = word_assets.CHAPTERS[chapter_id]
    chapter_blocks = word_assets.chapter_slice(blocks, config["marker"], config["next_marker"])
    table_mapping = {"ch04": {"4-1": "res_ch04_001", "4-2": "res_ch04_007"}, "ch05": {"5-1": "table_5_1"}}[
        chapter_id
    ]
    resources = data.get("Resources", [])
    by_id = {
        str(row.get("resource_id")): row
        for row in resources
        if isinstance(row, dict) and row.get("resource_id")
    }
    applied: list[dict[str, Any]] = []
    for index, block in enumerate(chapter_blocks):
        if block.kind != "table" or not block.rows:
            continue
        label, context, _ = word_assets.nearest_label(chapter_blocks, index, word_assets.TABLE_RE)
        resource_id = table_mapping.get(label)
        if not resource_id:
            continue
        row = by_id.get(resource_id)
        if row is None:
            row = {
                "resource_id": resource_id,
                "chapter_id": chapter_id,
                "section_id": "ch05_sec01",
                "resource_type": "table",
                "title": "表5-1 GIS拓扑模型与BIM构件模型的差异",
                "file_path": "",
                "description": "比较GIS拓扑模型与BIM构件模型的关注焦点、基本单位和工程用途。",
                "related_kps": [],
                "qa_use": "用于教材表格查询、比较辨析和AI回答推荐。",
                "status": "placeholder",
                "keywords": ["表5-1", "GIS拓扑模型", "BIM构件模型", "差异"],
            }
            resources.append(row)
            by_id[resource_id] = row
        columns = block.rows[0]
        rows = [
            {columns[col]: cells[col] if col < len(cells) else "" for col in range(len(columns))}
            for cells in block.rows[1:]
        ]
        row["table_detail"] = {
            "label": f"表{label}",
            "label_key": label,
            "title": row["title"],
            "columns": columns,
            "rows": rows,
            "context_before": context,
            "source": f"output/{chapter_id}_rag_engine/reports/{chapter_id}_word_extract.txt",
            "source_document": DOCX.name,
            "extraction_status": "extracted",
        }
        row["status"] = "structured"
        row["reference_aliases"] = [f"表{label}", f"表 {label}", label]
        applied.append({"resource_id": resource_id, "table_no": label, "rows": len(rows), "columns": len(columns)})
    return applied


def keywords(title: str) -> list[str]:
    text = re.sub(r"^[图表]\s*\d+\s*[-－—.．]\s*\d+\s*", "", title).strip()
    return unique_list([title, text])


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
