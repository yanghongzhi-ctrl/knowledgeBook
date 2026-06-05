from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .retrieve import list_text, normalize, tokens


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_SCRIPT_ROOT = Path("assets/ch01/interactive_html")

SCRIPT_BINDINGS = [
    {
        "resource_id": "ch01_script_timeline",
        "file_name": "1.1设计阶段的演进.html",
        "title": "道路设计数字化演进时间轴",
        "related_kps": ["kp_ch01_001", "kp_ch01_003", "kp_ch01_010", "kp_ch01_017", "kp_ch01_025"],
        "keywords": ["阶段", "演进", "CAD", "BIM", "BIM+GIS", "数字孪生"],
    },
    {
        "resource_id": "ch01_script_cad_semantics",
        "file_name": "1.2CAD阶段图元语义与设计变更联动.html",
        "title": "CAD阶段图元语义与设计变更联动",
        "related_kps": ["kp_ch01_003", "kp_ch01_004", "kp_ch01_005", "kp_ch01_006"],
        "keywords": ["CAD", "图元", "工程语义", "变更联动"],
    },
    {
        "resource_id": "ch01_script_bim_prr",
        "file_name": "1.3道路BIM概念与特点.html",
        "title": "道路BIM构件语义与PRR机制",
        "related_kps": ["kp_ch01_010", "kp_ch01_011", "kp_ch01_012", "kp_ch01_015"],
        "keywords": ["BIM", "构件", "语义", "参数", "PRR"],
    },
    {
        "resource_id": "ch01_script_bim_gis_overlay",
        "file_name": "1.4BIM+GIS 图层叠加与路线适宜性分析.html",
        "title": "BIM+GIS图层叠加与路线适宜性分析",
        "related_kps": ["kp_ch01_017", "kp_ch01_018", "kp_ch01_019", "kp_ch01_020"],
        "keywords": ["BIM+GIS", "GIS", "图层", "空间分析", "适宜性"],
    },
    {
        "resource_id": "ch01_script_digital_twin",
        "file_name": "1.5数字孪生虚实闭环交互脚本.html",
        "title": "数字孪生虚实闭环脚本",
        "related_kps": ["kp_ch01_025", "kp_ch01_026", "kp_ch01_027", "kp_ch01_028"],
        "keywords": ["数字孪生", "虚实闭环", "实时感知", "仿真预测"],
    },
    {
        "resource_id": "ch01_script_concepts",
        "file_name": "1.6道路工程数字化设计理念.html",
        "title": "道路工程数字化设计四大理念脚本",
        "related_kps": ["kp_ch01_032", "kp_ch01_033", "kp_ch01_038", "kp_ch01_042", "kp_ch01_046", "kp_ch01_049"],
        "keywords": ["理念", "构件化", "参数化", "协同化", "生命周期化"],
    },
    {
        "resource_id": "ch01_script_tech_system",
        "file_name": "1.7道路工程数字化设计技术体系.html",
        "title": "道路工程数字化设计技术体系",
        "related_kps": ["kp_ch01_050", "kp_ch01_051", "kp_ch01_052", "kp_ch01_053"],
        "keywords": ["技术体系", "CAD", "BIM", "GIS", "数字孪生", "AI"],
    },
    {
        "resource_id": "ch01_script_model_flow",
        "file_name": "1.8以模型为核心的设计流程.html",
        "title": "以模型为核心的设计流程脚本",
        "related_kps": ["kp_ch01_062", "kp_ch01_063", "kp_ch01_064"],
        "keywords": ["模型", "流程", "数据贯通", "协同交付"],
    },
    {
        "resource_id": "ch01_script_data_control",
        "file_name": "1.9数据驱动的设计控制.html",
        "title": "数据驱动的设计控制脚本",
        "related_kps": ["kp_ch01_066", "kp_ch01_067", "kp_ch01_068"],
        "keywords": ["数据驱动", "规则校核", "设计控制", "要素联动"],
    },
    {
        "resource_id": "ch01_script_software_modes",
        "file_name": "1.10典型工具软件在各阶段应用模式.html",
        "title": "典型工具软件在各阶段应用模式",
        "related_kps": ["kp_ch01_050", "kp_ch01_054", "kp_ch01_055"],
        "keywords": ["工具软件", "阶段应用", "平台协同", "成果流转"],
    },
]

RESOURCE_INTENT_TERMS = (
    "资源",
    "素材",
    "脚本",
    "互动",
    "演示",
    "操作",
    "打开",
    "查看",
    "想看",
    "我想看",
    "怎么看",
    "怎么用",
    "如何使用",
    "图",
    "图片",
    "示意图",
    "流程图",
    "时间轴",
    "公式",
    "计算公式",
    "变量",
    "变量含义",
    "式",
    "表",
    "表格",
    "对比表",
)

SCRIPT_INTENT_TERMS = ("脚本", "互动", "演示", "操作", "怎么看", "怎么用", "如何使用")
IMAGE_INTENT_TERMS = ("图", "图片", "示意图", "流程图")
FORMULA_INTENT_TERMS = ("公式", "计算公式", "变量", "变量含义", "式")
TABLE_INTENT_TERMS = ("表", "表格", "对比表")


def build_bound_resources(
    existing: list[dict[str, Any]],
    script_root: Path = PROJECT_SCRIPT_ROOT,
    check_root: Path | None = None,
) -> list[dict[str, Any]]:
    existing_by_id = {str(row.get("resource_id")): dict(row) for row in existing}
    resources: list[dict[str, Any]] = []
    if check_root is None:
        check_root = script_root if script_root.is_absolute() else PROJECT_ROOT / script_root

    chapter_ids = {str(row.get("chapter_id")) for row in existing if row.get("chapter_id")}
    if not chapter_ids or "ch01" in chapter_ids:
        for binding in SCRIPT_BINDINGS:
            resource_id = binding["resource_id"]
            row = existing_by_id.pop(resource_id, {})
            file_path = script_root / binding["file_name"]
            check_path = check_root / binding["file_name"]
            row.update(
                {
                    "resource_id": resource_id,
                    "chapter_id": "ch01",
                    "resource_type": "interactive_html",
                    "title": binding["title"],
                    "file_path": file_path.as_posix(),
                    "description": row.get("description")
                    or f"用于辅助理解{binding['title']}相关知识点。",
                    "related_kps": binding["related_kps"],
                    "keywords": binding["keywords"],
                    "teaching_use": row.get("teaching_use")
                    or "课堂讲授、自学复习和AI回答后资源推荐",
                    "qa_use": row.get("qa_use") or "当问题命中相关知识点时推荐",
                    "status": "bound" if check_path.exists() else "missing_file",
                }
            )
            resources.append(row)

    for row in existing_by_id.values():
        row = dict(row)
        row.setdefault("keywords", [])
        file_path = str(row.get("file_path") or "")
        check_path = Path(file_path)
        if file_path:
            if not check_path.is_absolute():
                check_path = PROJECT_ROOT / check_path
            row["status"] = "bound" if check_path.exists() else row.get("status") or "missing_file"
        else:
            row["status"] = row.get("status") or "placeholder_to_bind"
        resources.append(row)

    resources.sort(key=lambda item: (item.get("resource_type") != "interactive_html", item.get("resource_id", "")))
    return resources


def recommend_resources(card: dict[str, Any], resources: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    related_kps = set(str(kp) for kp in (card.get("related_kps") or []))
    card_tokens = tokens(
        " ".join(
            [
                str(card.get("canonical_question") or ""),
                list_text(card.get("answer_points")),
                list_text(card.get("must_include")),
            ]
        )
    )
    explicit_ids = set(str(x) for x in (card.get("recommended_resources") or []))

    scored: list[tuple[float, dict[str, Any]]] = []
    for resource in resources:
        score = 0.0
        resource_id = str(resource.get("resource_id") or "")
        if resource.get("suppress_recommendation") and resource_id not in explicit_ids:
            continue
        if resource_id in explicit_ids:
            score += 100
        resource_kps = resource.get("related_kps") or []
        if isinstance(resource_kps, str):
            resource_kps = [resource_kps]
        overlap = related_kps & set(str(kp) for kp in resource_kps)
        score += 25 * len(overlap)
        resource_tokens = tokens(
            " ".join(
                [
                    str(resource.get("title") or ""),
                    str(resource.get("description") or ""),
                    list_text(resource.get("keywords")),
                ]
            )
        )
        score += min(30, len(card_tokens & resource_tokens) * 3)
        if resource.get("status") == "bound":
            score += 5
        if score > 0:
            scored.append((score, resource))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [resource for _, resource in scored[:limit]]


def script_map_by_resource(scripts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(script.get("resource_id")): dict(script)
        for script in scripts
        if script.get("resource_id")
    }


def resource_intent_score(question: str) -> int:
    generic_terms = (
        "资源",
        "素材",
        "脚本",
        "互动",
        "演示",
        "操作",
        "打开",
        "查看",
        "想看",
        "我想看",
        "怎么看",
        "怎么用",
        "如何使用",
        "图片",
        "示意图",
        "流程图",
        "时间轴",
        "公式",
        "计算公式",
        "变量含义",
        "表格",
        "对比表",
        "比较表",
        "一览表",
    )
    score = sum(1 for term in generic_terms if term in question)
    score += 1 if _has_image_intent(question) else 0
    score += 1 if _has_formula_intent(question) else 0
    score += 1 if _has_table_intent(question) else 0
    return score


def _has_image_intent(question: str) -> bool:
    if any(term in question for term in ("图片", "示意图", "流程图", "图示", "插图", "看图")):
        return True
    return bool(re.search(r"图\s*\d+(?:[-.－—]\d+)?", question))


def _has_formula_intent(question: str) -> bool:
    if any(term in question for term in ("公式", "计算公式", "变量含义")):
        return True
    return bool(re.search(r"式\s*\d+(?:[-.－—]\d+)?", question))


def _has_table_intent(question: str) -> bool:
    if any(term in question for term in ("表格", "对比表", "比较表", "一览表", "看表")):
        return True
    return bool(re.search(r"表\s*\d+(?:[-.－—]\d+)?", question))


def compact_text(text: str) -> str:
    return re.sub(r"[\W_]+", "", (text or "").lower(), flags=re.UNICODE)


def phrase_matches(question: str, phrase: str) -> bool:
    q_compact = compact_text(question)
    phrase_compact = compact_text(phrase)
    if not q_compact or not phrase_compact:
        return False
    return compact_contains(q_compact, phrase_compact) or compact_contains(phrase_compact, q_compact)


def compact_contains(haystack: str, needle: str) -> bool:
    start = haystack.find(needle)
    if start < 0:
        return False
    end = start + len(needle)
    if needle[-1:].isdigit() and end < len(haystack) and haystack[end].isdigit():
        return False
    return True


def search_resources(
    question: str,
    resources: list[dict[str, Any]],
    scripts: list[dict[str, Any]],
    limit: int = 5,
) -> list[dict[str, Any]]:
    script_by_resource = script_map_by_resource(scripts)
    q_norm = normalize(question)
    q_tokens = tokens(question)
    intent_score = resource_intent_score(question)

    scored: list[dict[str, Any]] = []
    for resource in resources:
        resource_id = str(resource.get("resource_id") or "")
        resource_type = str(resource.get("resource_type") or "")
        type_conflict = _resource_type_conflicts_with_question(question, resource_type)
        script = script_by_resource.get(resource_id)
        score = 0.0
        reasons: list[str] = []

        title = str(resource.get("title") or "")
        title_norm = normalize(title)
        if (q_norm and title_norm and q_norm == title_norm) or phrase_matches(question, title):
            score += 90
            reasons.append("title_match")
        title_overlap = q_tokens & tokens(title)
        if title_overlap:
            score += min(50, len(title_overlap) * 6)
            reasons.append(f"title_token_overlap:{len(title_overlap)}")

        if resource_id and resource_id.lower() in question.lower():
            score += 90
            reasons.append("resource_id_match")

        if not type_conflict:
            for alias in resource.get("reference_aliases") or []:
                if phrase_matches(question, str(alias)):
                    score += 130
                    reasons.append("reference_alias")
                    break

        fig_score = 0 if type_conflict else _figure_reference_score(question, resource_id)
        if fig_score:
            score += fig_score
            reasons.append("figure_reference")

        formula_score = 0 if type_conflict else _formula_reference_score(question, resource_id)
        if formula_score:
            score += formula_score
            reasons.append("formula_reference")

        table_score = 0 if type_conflict else _table_reference_score(question, resource_id)
        if table_score:
            score += table_score
            reasons.append("table_reference")

        trigger_questions = list(resource.get("trigger_questions") or [])
        if script:
            trigger_questions.extend(script.get("trigger_questions") or [])
        for trigger in trigger_questions:
            trigger_norm = normalize(str(trigger))
            trigger_text = str(trigger)
            if not trigger_norm and not compact_text(trigger_text):
                continue
            if q_norm and q_norm == trigger_norm:
                score += 120
                reasons.append("exact_trigger")
                break
            if q_norm and (q_norm in trigger_norm or trigger_norm in q_norm):
                score += 80
                reasons.append("partial_trigger")
                break
            if phrase_matches(question, trigger_text):
                score += 80
                reasons.append("partial_trigger")
                break

        resource_text = " ".join(
            [
                resource_id,
                title,
                str(resource.get("description") or ""),
                str(resource.get("qa_use") or ""),
                str(resource.get("teaching_use") or ""),
                list_text(resource.get("keywords")),
                list_text(resource.get("related_kps")),
                list_text(trigger_questions),
                list_text(script or {}),
            ]
        )
        overlap = q_tokens & tokens(resource_text)
        if overlap:
            score += min(70, len(overlap) * 4)
            reasons.append(f"token_overlap:{len(overlap)}")

        keyword_hits = 0
        for keyword in resource.get("keywords") or []:
            keyword_norm = normalize(str(keyword))
            if (q_norm and keyword_norm and q_norm == keyword_norm) or phrase_matches(question, str(keyword)):
                keyword_hits += 1
        if keyword_hits:
            score += min(60, keyword_hits * 20)
            reasons.append(f"keyword_exact:{keyword_hits}")

        script_intent = any(term in question for term in SCRIPT_INTENT_TERMS)
        image_intent = any(term in question for term in IMAGE_INTENT_TERMS)
        formula_intent = any(term in question for term in FORMULA_INTENT_TERMS)
        table_intent = any(term in question for term in TABLE_INTENT_TERMS)
        if resource_type == "interactive_html" and script_intent:
            score += 60
            reasons.append("script_intent")
        if resource_type == "image" and image_intent:
            score += 35
            reasons.append("image_intent")
        if resource_type == "formula" and formula_intent:
            score += 45
            reasons.append("formula_intent")
        if resource_type == "table" and table_intent:
            score += 45
            reasons.append("table_intent")
        if resource_type == "image" and script_intent:
            score -= 35
            reasons.append("script_intent_penalty")
        if resource_type == "formula" and image_intent and not formula_intent:
            score -= 25
            reasons.append("image_intent_penalty")
        if resource_type == "table" and image_intent and not table_intent:
            score -= 20
            reasons.append("image_intent_penalty")
        if type_conflict:
            score -= 160
            reasons.append("resource_type_conflict")
        if intent_score:
            score += min(20, intent_score * 4)
            reasons.append("resource_intent")
        if resource.get("status") == "bound":
            score += 5
            reasons.append("bound")

        if score > 0:
            if resource.get("suppress_recommendation") and not any(
                reason in reasons for reason in ("title_match", "resource_id_match", "reference_alias")
            ):
                continue
            scored.append(
                {
                    "score": score,
                    "reasons": reasons,
                    "resource": resource,
                    "interactive_script": script,
                }
            )

    scored.sort(key=lambda item: float(item["score"]), reverse=True)
    return scored[:limit]


def _resource_type_conflicts_with_question(question: str, resource_type: str) -> bool:
    intended_types: set[str] = set()
    if _has_image_intent(question):
        intended_types.add("image")
    if _has_formula_intent(question):
        intended_types.add("formula")
    if _has_table_intent(question):
        intended_types.add("table")
    return bool(intended_types) and resource_type in {"image", "formula", "table"} and resource_type not in intended_types


def _figure_reference_score(question: str, resource_id: str) -> int:
    match = re.search(r"(?:ch\d+_)?fig[_-](\d+)[_-](\d+)", resource_id)
    if not match:
        return 0
    suffix = f"{match.group(1)}-{match.group(2)}"
    aliases = {suffix, suffix.replace("-", "."), suffix.replace("-", "_")}
    aliases.update({f"图{item}" for item in aliases})
    aliases.update({f"图 {item}" for item in aliases})
    aliases.update({f"图{item}" for item in aliases})
    aliases.update({f"图 {item}" for item in aliases})
    return 120 if any(_figure_alias_matches(question, alias) for alias in aliases) else 0


def _formula_reference_score(question: str, resource_id: str) -> int:
    match = re.search(r"(?:ch\d+_)?formula[_-](\d+)[_-](\d+)", resource_id)
    if not match:
        return 0
    suffix = f"{match.group(1)}-{match.group(2)}"
    compact_question = compact_text(question)
    aliases = {
        f"公式{suffix}",
        f"公式{suffix.replace('-', '.')}",
        f"公式{suffix.replace('-', '_')}",
        f"式{suffix}",
        f"式{suffix.replace('-', '.')}",
        f"式{suffix.replace('-', '_')}",
    }
    for alias in aliases:
        compact_alias = compact_text(alias)
        start = compact_question.find(compact_alias)
        if start < 0:
            continue
        end = start + len(compact_alias)
        if end >= len(compact_question) or not compact_question[end].isdigit():
            return 130
    return 0


def _table_reference_score(question: str, resource_id: str) -> int:
    match = re.search(r"(?:ch\d+_)?table[_-](\d+)[_-](\d+)", resource_id)
    if not match:
        return 0
    suffix = f"{match.group(1)}-{match.group(2)}"
    compact_question = compact_text(question)
    aliases = {
        f"表{suffix}",
        f"表{suffix.replace('-', '.')}",
        f"表{suffix.replace('-', '_')}",
        f"表格{suffix}",
        f"对比表{suffix}",
    }
    for alias in aliases:
        compact_alias = compact_text(alias)
        start = compact_question.find(compact_alias)
        if start < 0:
            continue
        end = start + len(compact_alias)
        if end >= len(compact_question) or not compact_question[end].isdigit():
            return 130
    return 0


def _figure_alias_matches(question: str, alias: str) -> bool:
    pattern = rf"(?<![0-9]){re.escape(alias)}(?![0-9])"
    return re.search(pattern, question) is not None
