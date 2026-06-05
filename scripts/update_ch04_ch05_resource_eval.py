from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {
    "ch04": next((ROOT / "data/raw/ch04").glob("*.json")),
    "ch05": next((ROOT / "data/raw/ch05").glob("*.json")),
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
    for resource in data.get("Resources", []):
        if not isinstance(resource, dict):
            continue
        resource_id = str(resource.get("resource_id") or "")
        resource_type = str(resource.get("resource_type") or "")
        title = str(resource.get("title") or resource_id)
        if not resource_id:
            continue
        if resource_type == "interactive_html":
            questions = [f"{title}怎么看？", f"{title}怎么操作？", f"我想看{title}。"]
            intent = "interactive_script"
        elif resource_type == "image":
            label = resource_label(title, resource_id, "图")
            if label == title and not re.search(r"图\s*\d+[-—.]\d+", title):
                questions = [f"我想看{title}。", f"{title}怎么看？"]
            else:
                questions = [f"{label}说明了什么？", f"我想看{label}。"]
            intent = "image"
        elif resource_type == "table":
            label = resource_label(title, resource_id, "表")
            questions = [f"{label}对比了什么？", f"我想看{label}。", f"{title}怎么看？"]
            intent = "table"
        elif resource_type == "formula":
            label = resource_label(title, resource_id, "公式")
            questions = [f"我想看{label}。", f"{label}的变量含义是什么？"]
            intent = "formula"
        else:
            continue
        for index, question in enumerate(dedupe(questions), 1):
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


def resource_label(title: str, resource_id: str, fallback: str) -> str:
    match = re.search(r"(图|表|公式)\s*\d+[-—.]\d+", title)
    if match:
        return match.group(0).replace(" ", "").replace("—", "-").replace(".", "-")
    match = re.search(r"(?:fig|table|formula)[_-](\d+)[_-](\d+)", resource_id)
    if match:
        return f"{fallback}{match.group(1)}-{match.group(2)}"
    return title


def dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        value = value.strip()
        if value and value not in result:
            result.append(value)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
