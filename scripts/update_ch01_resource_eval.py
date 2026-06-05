from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "data/raw/ch01/第1章_道路工程数字化设计概述_知识库_v1.0完备版.json"

IMAGE_QUESTIONS = {
    "ch01_fig_1_1": [
        "图1-1说明了什么？",
        "第一章发展阶段图说明了什么？",
        "我想看道路数字化设计发展阶段图。",
    ],
    "ch01_fig_1_2": [
        "图1-2说明了什么？",
        "四大核心理念示意图怎么看？",
        "我想看构件化、参数化、协同化和生命周期化的示意图。",
    ],
    "ch01_fig_1_3": [
        "图1-3说明了什么？",
        "数字化技术体系图怎么看？",
        "我想看CAD、BIM、GIS和数字孪生技术体系图。",
    ],
    "ch01_fig_1_4": [
        "图1-4说明了什么？",
        "以模型为核心的设计流程图怎么看？",
        "我想看模型驱动设计流程的示意图。",
    ],
}

SCRIPT_EXTRA_QUESTIONS = {
    "ch01_script_timeline": ["我想看道路设计数字化演进时间轴。"],
    "ch01_script_cad_semantics": ["我想看CAD图元语义与设计变更联动演示。"],
    "ch01_script_bim_prr": ["我想看PRR机制的互动演示。"],
    "ch01_script_bim_gis_overlay": ["我想看BIM+GIS图层叠加选线演示。"],
    "ch01_script_digital_twin": ["我想看数字孪生虚实闭环交互脚本。"],
    "ch01_script_concepts": ["我想看四大核心理念互动脚本。"],
    "ch01_script_tech_system": ["我想看道路工程数字化设计技术体系演示。"],
    "ch01_script_model_flow": ["我想看以模型为核心的设计流程脚本。"],
    "ch01_script_data_control": ["我想看数据驱动设计控制演示。"],
    "ch01_script_software_modes": ["我想看典型工具软件阶段应用模式脚本。"],
}

RESOURCE_INTENT_TERMS = (
    "脚本",
    "互动",
    "演示",
    "操作",
    "怎么看",
    "怎么用",
    "图",
    "示意图",
    "流程图",
    "我想看",
)


def main() -> int:
    data = json.loads(PACKAGE.read_text(encoding="utf-8"))
    resources = {str(row.get("resource_id")): row for row in data.get("Resources", [])}
    cases: list[dict[str, object]] = []
    seen_questions: set[str] = set()

    for script in data.get("Interactive_Scripts", []):
        resource_id = str(script.get("resource_id") or "")
        resource = resources.get(resource_id, {})
        title = str(resource.get("title") or script.get("title") or resource_id)
        questions = [
            f"{title}怎么看？",
            f"{title}怎么操作？",
            f"我想看{title}。",
        ]
        questions.extend(
            question
            for question in script.get("trigger_questions") or []
            if any(term in str(question) for term in RESOURCE_INTENT_TERMS)
        )
        questions.extend(SCRIPT_EXTRA_QUESTIONS.get(resource_id, []))
        for index, question in enumerate(_dedupe(questions), 1):
            if question in seen_questions:
                continue
            seen_questions.add(question)
            cases.append(
                {
                    "test_id": f"res_eval_{resource_id}_{index:02d}",
                    "chapter_id": "ch01",
                    "question": question,
                    "expected_resource_id": resource_id,
                    "expected_resource_type": "interactive_html",
                    "expected_answer_mode": "resource_guidance",
                    "related_kps": resource.get("related_kps") or script.get("related_kps") or [],
                    "resource_intent": "interactive_script",
                    "pass_rule": "top1_resource_and_mode",
                }
            )

    for resource_id, questions in IMAGE_QUESTIONS.items():
        resource = resources.get(resource_id, {})
        for index, question in enumerate(questions, 1):
            if question in seen_questions:
                continue
            seen_questions.add(question)
            cases.append(
                {
                    "test_id": f"res_eval_{resource_id}_{index:02d}",
                    "chapter_id": "ch01",
                    "question": question,
                    "expected_resource_id": resource_id,
                    "expected_resource_type": "image",
                    "expected_answer_mode": "resource_guidance",
                    "related_kps": resource.get("related_kps") or [],
                    "resource_intent": "image",
                    "pass_rule": "top1_resource_and_mode",
                }
            )

    data["Resource_Evaluation_Testset"] = cases
    PACKAGE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"resource_eval_cases={len(cases)}")
    print(f"package={PACKAGE}")
    return 0


def _dedupe(values: list[object]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
