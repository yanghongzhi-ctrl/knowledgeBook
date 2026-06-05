from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {
    "ch02": next((ROOT / "data/raw/ch02").glob("*.json")),
    "ch03": next((ROOT / "data/raw/ch03").glob("*.json")),
}


def main() -> int:
    for chapter_id, path in PACKAGES.items():
        data = json.loads(path.read_text(encoding="utf-8"))
        cases = build_cases(chapter_id, data)
        data["Resource_Evaluation_Testset"] = cases
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{chapter_id}: resource_eval_cases={len(cases)}")
    return 0


def build_cases(chapter_id: str, data: dict) -> list[dict]:
    cases: list[dict] = []
    seen: set[tuple[str, str]] = set()
    resources = data.get("Resources", [])

    for resource in resources:
        resource_id = str(resource.get("resource_id") or "")
        resource_type = str(resource.get("resource_type") or "")
        title = str(resource.get("title") or resource_id)
        if resource_type == "interactive_html":
            questions = [
                f"{title}怎么看？",
                f"{title}怎么操作？",
                f"我想看{title}。",
            ]
            intent = "interactive_script"
        elif resource_type == "image":
            figure = _figure_label(title, resource_id)
            questions = [
                f"{figure}说明了什么？",
                f"请查看{figure}：{title}说明了什么？",
            ]
            intent = "image"
        elif resource_type == "formula":
            label = _formula_label(resource, resource_id, title)
            questions = [
                f"我想看{label}。",
                f"{label}的变量含义是什么？",
            ]
            intent = "formula"
        elif resource_type == "table":
            label = _table_label(resource, resource_id, title)
            questions = [
                f"我想看{label}。",
                f"{label}对比了什么？",
                f"{title}怎么看？",
            ]
            intent = "table"
        else:
            continue

        for index, question in enumerate(_dedupe(questions), 1):
            key = (resource_id, question)
            if key in seen:
                continue
            seen.add(key)
            cases.append(
                {
                    "test_id": f"res_eval_{resource_id}_{index:02d}",
                    "chapter_id": chapter_id,
                    "question": question,
                    "expected_resource_id": resource_id,
                    "expected_resource_type": resource_type,
                    "expected_answer_mode": "resource_guidance",
                    "related_kps": resource.get("related_kps") or [],
                    "resource_intent": intent,
                    "pass_rule": "top1_resource_and_mode",
                }
            )
    return cases


def _figure_label(title: str, resource_id: str) -> str:
    match = re.search(r"图\s*(\d+[-－]\d+|\d+\.\d+)", title)
    if match:
        return "图" + match.group(1).replace("－", "-")
    match = re.search(r"fig[_-](\d+)[_-](\d+)", resource_id)
    if match:
        return f"图{match.group(1)}-{match.group(2)}"
    return title


def _formula_label(resource: dict, resource_id: str, title: str) -> str:
    detail = resource.get("formula_detail") or {}
    if isinstance(detail, dict) and detail.get("label"):
        return str(detail["label"])
    match = re.search(r"(?:formula|公式|式)[_\s（(]*(\d+)[_\-－\s]*(\d+)", resource_id + " " + title)
    if match:
        return f"公式（{match.group(1)}-{match.group(2)}）"
    return title


def _table_label(resource: dict, resource_id: str, title: str) -> str:
    detail = resource.get("table_detail") or {}
    if isinstance(detail, dict) and detail.get("label"):
        return str(detail["label"])
    match = re.search(r"(?:table|表)[_\s]*(\d+)[_\-－\s]*(\d+)", resource_id + " " + title)
    if match:
        return f"表{match.group(1)}-{match.group(2)}"
    return title


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        value = value.strip()
        if value and value not in result:
            result.append(value)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
