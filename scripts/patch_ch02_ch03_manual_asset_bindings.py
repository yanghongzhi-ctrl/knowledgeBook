from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


MANUAL_BINDINGS = {
    "ch02": {
        "source_root": Path(r"D:\道路工程数字设计方法\文稿\第二章"),
        "raw": next((ROOT / "data/raw/ch02").glob("*.json")),
        "bindings": {
            "ch02_fig_2_1": "坐标系统.png",
            "ch02_fig_2_2": "图2.2.png",
            "ch02_fig_2_3": "构造、控制与辅助图元参考1.png",
            "ch02_fig_2_5": "三维布尔运算.png",
        },
    },
    "ch03": {
        "source_root": Path(r"D:\道路工程数字设计方法\文稿\第三章"),
        "raw": next((ROOT / "data/raw/ch03").glob("*.json")),
        "bindings": {
            "fig_3_1": "图3.1.png",
            "fig_3_2": "图3.2.png",
            "fig_3_18": "戴帽规则图.jpg",
            "fig_3_19": "超高图.jpg",
        },
    },
}


def main() -> int:
    summary: dict[str, dict[str, object]] = {}
    for chapter_id, config in MANUAL_BINDINGS.items():
        summary[chapter_id] = bind_chapter(chapter_id, config)
    out = ROOT / "output/ch02_ch03_manual_asset_bindings.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def bind_chapter(chapter_id: str, config: dict[str, object]) -> dict[str, object]:
    raw_path = Path(config["raw"])
    source_root = Path(config["source_root"])
    asset_dir = ROOT / "assets" / chapter_id / "images"
    asset_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(raw_path.read_text(encoding="utf-8"))
    resources = data.get("Resources", [])
    by_id = {
        str(row.get("resource_id")): row
        for row in resources
        if isinstance(row, dict) and row.get("resource_id")
    }
    applied: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []

    bindings = config["bindings"]
    assert isinstance(bindings, dict)
    if chapter_id == "ch03":
        _clear_uncertain_ch03_bindings(by_id, set(bindings))
    for resource_id, filename in bindings.items():
        src = source_root / filename
        row = by_id.get(resource_id)
        if row is None or not src.exists():
            missing.append({"resource_id": resource_id, "source": str(src)})
            continue
        suffix = src.suffix.lower() or ".png"
        dst = asset_dir / f"{resource_id}{suffix}"
        shutil.copy2(src, dst)
        row["file_path"] = dst.relative_to(ROOT).as_posix()
        row["status"] = "bound"
        row["resource_type"] = "image"
        row["caption_or_name"] = row.get("title") or resource_id
        keywords = row.get("keywords")
        if not isinstance(keywords, list) or not keywords:
            row["keywords"] = _keywords(str(row.get("title") or resource_id))
        applied.append({"resource_id": resource_id, "file_path": row["file_path"], "source": str(src)})

    raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"applied": applied, "missing": missing}


def _clear_uncertain_ch03_bindings(by_id: dict[str, dict[str, object]], keep: set[str]) -> None:
    for resource_id, row in by_id.items():
        if resource_id in keep or row.get("resource_type") != "image":
            continue
        file_path = str(row.get("file_path") or "")
        if file_path.startswith("assets/ch03/images/"):
            row["file_path"] = ""
            row["status"] = "placeholder"


def _keywords(title: str) -> list[str]:
    for prefix in ("图2-", "图3-", "表2-", "表3-"):
        if title.startswith(prefix):
            title = title[len(prefix) :].strip()
    return [title] if title else []


if __name__ == "__main__":
    raise SystemExit(main())
