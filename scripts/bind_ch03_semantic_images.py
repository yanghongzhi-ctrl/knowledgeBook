from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = next((ROOT / "data/raw/ch03").glob("*.json"))
PREVIEW = ROOT / "output/ch03_rag_engine/word_media_preview/png"
ASSET_DIR = ROOT / "assets/ch03/images"


SEMANTIC_BINDINGS = {
    "fig_3_7": {
        "image": "image7.png",
        "rationale": "Word 媒体图为基本型平曲线计算图式。",
    },
    "fig_3_8": {
        "image": "image8.png",
        "rationale": "Word 媒体图为卵形曲线计算图式。",
    },
    "fig_3_9": {
        "image": "image9.png",
        "rationale": "Word 媒体图为双交点曲线计算图式。",
    },
    "fig_3_10": {
        "image": "image10.png",
        "rationale": "Word 媒体图为直线与圆曲线连接计算图式。",
    },
    "fig_3_11": {
        "image": "image11.png",
        "rationale": "Word 媒体图包含两反向圆曲线连接示意。",
    },
    "fig_3_12": {
        "image": "image11.png",
        "rationale": "Word 原稿在两同向圆曲线连接处复用同一组圆曲线连接示意。",
    },
    "fig_3_13": {
        "image": "image12.png",
        "rationale": "Word 媒体图包含 X/Y 坐标轴与逐桩主点，匹配坐标计算图式。",
    },
    "fig_3_15": {
        "image": "image13.png",
        "rationale": "Word 媒体图为纵断面计算流程图。",
    },
    "fig_3_16": {
        "image": "image14.png",
        "rationale": "Word 媒体图为纵断面计算图式。",
    },
    "fig_3_17": {
        "image": "image15.png",
        "rationale": "Word 媒体图为横断面 CAD 系统流程图。",
    },
    "fig_3_20": {
        "image": "image18.png",
        "rationale": "Word 媒体图为无中间带超高值计算图式。",
    },
    "fig_3_21": {
        "image": "image19.png",
        "rationale": "Word 媒体图为有中间带超高值计算图式。",
    },
    "fig_3_22": {
        "image": "image20.png",
        "rationale": "Word 媒体图为基本边坡线单元。",
    },
    "fig_3_23": {
        "image": "image21.png",
        "rationale": "Word 媒体图为横断面面积计算积距法。",
    },
    "fig_3_24": {
        "image": "image22.png",
        "rationale": "Word 媒体图为横断面面积计算坐标法。",
    },
    "fig_3_25": {
        "image": "image23.png",
        "rationale": "Word 媒体图为平均断面法体积计算。",
    },
    "fig_3_27": {
        "image": "image24.png",
        "rationale": "Word 媒体图为平面交叉口 CAD 系统结构。",
    },
    "fig_3_28": {
        "image": "image25.png",
        "rationale": "Word 媒体图为交叉口 Coons 曲面片划分图。",
    },
    "fig_3_29": {
        "image": "image26.png",
        "rationale": "Word 媒体图为人机交互交叉口立面设计流程图。",
    },
}


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(RAW.read_text(encoding="utf-8"))
    resources = data.get("Resources", [])
    by_id = {
        str(row.get("resource_id")): row
        for row in resources
        if isinstance(row, dict) and row.get("resource_id")
    }
    applied: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []

    for resource_id, binding in SEMANTIC_BINDINGS.items():
        row = by_id.get(resource_id)
        src = PREVIEW / binding["image"]
        if row is None or not src.exists():
            missing.append({"resource_id": resource_id, "source": str(src)})
            continue
        dst = ASSET_DIR / f"{resource_id}.png"
        shutil.copy2(src, dst)
        row["file_path"] = dst.relative_to(ROOT).as_posix()
        row["status"] = "bound"
        row["resource_type"] = "image"
        row["binding_note"] = binding["rationale"]
        row["caption_or_name"] = row.get("title") or resource_id
        keywords = row.get("keywords")
        if not isinstance(keywords, list) or not keywords:
            row["keywords"] = [str(row.get("title") or resource_id)]
        applied.append(
            {
                "resource_id": resource_id,
                "title": str(row.get("title") or ""),
                "file_path": row["file_path"],
                "source": str(src),
                "rationale": binding["rationale"],
            }
        )

    RAW.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output = ROOT / "output/ch03_rag_engine/reports/ch03_semantic_image_bindings.json"
    output.write_text(
        json.dumps({"applied": applied, "missing": missing}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"applied={len(applied)} missing={len(missing)} report={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
