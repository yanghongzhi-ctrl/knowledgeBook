from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from .loader import KnowledgePackage


CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
ASCII_RE = re.compile(r"[a-zA-Z0-9+#_.-]+")


def normalize(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[，。！？；：、“”‘’（）()\[\]【】《》<>.,!?;:\"']", "", text)
    text = text.replace("|", "")
    return text


def tokens(text: str) -> set[str]:
    text = text or ""
    result: set[str] = set()
    for part in ASCII_RE.findall(text.lower()):
        if len(part) >= 2:
            result.add(part)
    for seq in CJK_RE.findall(text):
        if len(seq) == 1:
            result.add(seq)
        else:
            for size in (2, 3, 4):
                for i in range(0, max(0, len(seq) - size + 1)):
                    result.add(seq[i : i + size])
            if len(seq) <= 10:
                result.add(seq)
    return result


def list_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(list_text(v) for v in value)
    if isinstance(value, dict):
        return " ".join(f"{k} {list_text(v)}" for k, v in value.items())
    return str(value)


@dataclass
class RetrievalHit:
    answer_id: str
    score: float
    reasons: list[str]
    card: dict[str, Any]


class AnswerRetriever:
    def __init__(self, package: KnowledgePackage):
        self.package = package
        self.cards = package.answer_cards
        self.rag_by_object = {
            row.get("object_id"): row for row in package.rag_config if row.get("object_id")
        }
        self.synonyms_by_target: dict[str, list[dict[str, Any]]] = {}
        answer_ids = {str(card.get("answer_id")) for card in self.cards if card.get("answer_id")}
        canonical_to_ids: dict[str, list[str]] = {}
        for card in self.cards:
            if card.get("answer_id") and card.get("canonical_question"):
                canonical_to_ids.setdefault(normalize(str(card.get("canonical_question", ""))), []).append(
                    str(card.get("answer_id"))
                )
        for row in package.synonyms:
            raw_target = str(row.get("target_id") or "")
            target = raw_target
            if raw_target not in answer_ids:
                standard_id = str(row.get("standard_id") or "")
                if standard_id in answer_ids:
                    target = standard_id
                else:
                    canonical_ids = canonical_to_ids.get(normalize(raw_target), [])
                    target = canonical_ids[0] if len(canonical_ids) == 1 else raw_target
            if target:
                self.synonyms_by_target.setdefault(target, []).append(row)

    def search(self, question: str, top_k: int = 5) -> list[RetrievalHit]:
        q_norm = normalize(question)
        q_tokens = tokens(question)
        hits: list[RetrievalHit] = []

        for card in self.cards:
            answer_id = str(card.get("answer_id", ""))
            score = 0.0
            reasons: list[str] = []

            canonical = str(card.get("canonical_question", ""))
            canonical_norm = normalize(canonical)
            if q_norm and q_norm == canonical_norm:
                score += 120
                reasons.append("exact_canonical")
            elif q_norm and (q_norm in canonical_norm or canonical_norm in q_norm):
                score += 85
                reasons.append("partial_canonical")
            elif q_norm and _intent_core(q_norm) == _intent_core(canonical_norm):
                score += 110
                reasons.append("intent_core_canonical")

            pattern_norms = [
                normalize(str(pattern))
                for pattern in (card.get("student_question_patterns", []) or [])
                if normalize(str(pattern))
            ]
            if q_norm and any(q_norm == pattern_norm for pattern_norm in pattern_norms):
                score += 180
                reasons.append("exact_pattern")
            elif q_norm and any(
                q_norm in pattern_norm or pattern_norm in q_norm
                for pattern_norm in pattern_norms
            ):
                score += 75
                reasons.append("partial_pattern")
            elif q_norm and any(
                _intent_core(q_norm) == _intent_core(pattern_norm)
                for pattern_norm in pattern_norms
            ):
                score += 140
                reasons.append("intent_core_pattern")

            for syn in self.synonyms_by_target.get(answer_id, []):
                alias = str(syn.get("alias_or_question", ""))
                alias_norm = normalize(alias)
                if q_norm and q_norm == alias_norm:
                    priority = numeric_value(syn.get("priority"), default=1.0)
                    score += 70 + priority * 5
                    reasons.append("synonym")
                    break

            synonyms_text = list_text(
                [syn.get("alias_or_question", "") for syn in self.synonyms_by_target.get(answer_id, [])]
            )
            rag = self.rag_by_object.get(answer_id)
            focused_text = " ".join(
                [
                    canonical,
                    list_text(card.get("student_question_patterns")),
                    synonyms_text,
                ]
            )
            body_text = " ".join(
                [
                    list_text(card.get("answer_points")),
                    list_text(card.get("must_include")),
                    list_text(rag.get("index_text")) if rag else "",
                ]
            )
            focused_overlap = q_tokens & tokens(focused_text)
            if focused_overlap:
                overlap_score = min(72, len(focused_overlap) * 6)
                score += overlap_score
                reasons.append(f"focused_token_overlap:{len(focused_overlap)}")

            body_overlap = q_tokens & tokens(body_text)
            if body_overlap:
                overlap_score = min(18, len(body_overlap) * 1.5)
                score += overlap_score
                reasons.append(f"body_token_overlap:{len(body_overlap)}")

            intent_score, intent_reasons = _intent_disambiguation_score(question, focused_text, body_text)
            if intent_score:
                score += intent_score
                reasons.extend(intent_reasons)

            if q_norm:
                must_text = normalize(list_text(card.get("must_include")))
                if must_text and any(normalize(str(x)) in q_norm for x in card.get("must_include", []) or []):
                    score += 20
                    reasons.append("must_include_match")

            if rag:
                score += min(20, numeric_value(rag.get("retrieval_priority")) / 10)
                if rag.get("primary_output") is True:
                    score += 5

            if score > 0:
                hits.append(RetrievalHit(answer_id=answer_id, score=score, reasons=reasons, card=card))

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]


def confidence(score: float) -> str:
    if score >= 110:
        return "high"
    if score >= 70:
        return "medium"
    return "low"


def numeric_value(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else default


def _intent_core(text: str) -> str:
    core = text
    for phrase in (
        "请简要说明",
        "请按条目回答",
        "能不能按条目总结",
        "怎么理解",
        "是什么",
        "是哪些",
        "包括哪些要点",
        "包括哪些",
        "有哪些要点",
        "有哪些",
    ):
        core = core.replace(normalize(phrase), "")
    return core


def _intent_disambiguation_score(question: str, focused_text: str, body_text: str) -> tuple[float, list[str]]:
    """Prefer cards whose question/pattern names the user's scope and intent."""
    q_norm = normalize(question)
    focused_norm = normalize(focused_text)
    body_norm = normalize(body_text)
    score = 0.0
    reasons: list[str] = []

    for phrase in ("包括哪些要点", "有哪些要点", "流程", "区别", "作用"):
        phrase_norm = normalize(phrase)
        if phrase_norm and phrase_norm in q_norm and phrase_norm in focused_norm:
            score += 30
            reasons.append(f"intent_focus:{phrase}")

    for term in ("平面", "纵断面", "横断面", "交叉口", "人机分工"):
        term_norm = normalize(term)
        if term_norm and term_norm in q_norm:
            if term_norm in focused_norm:
                score += 35
                reasons.append(f"scope_focus:{term}")
            elif term_norm in body_norm:
                score -= 15
                reasons.append(f"scope_body_only:{term}")

    if "功能" in q_norm:
        if "功能" in focused_norm:
            score += 25
            reasons.append("intent_focus:功能")
        elif "功能" in body_norm:
            score -= 5
            reasons.append("intent_body_only:功能")

    if "内容" in q_norm and "原则" not in q_norm and "原则" in focused_norm:
        score -= 40
        reasons.append("intent_mismatch:内容_vs_原则")

    if "原则" in q_norm and "内容" not in q_norm and "内容" in focused_norm:
        score -= 30
        reasons.append("intent_mismatch:原则_vs_内容")

    return score, reasons


def coverage(expected_points: list[Any], answer_text: str) -> float:
    if not expected_points:
        return 1.0
    answer_norm = normalize(answer_text)
    matched = 0
    for point in expected_points:
        point_norm = normalize(str(point))
        if point_norm and (point_norm in answer_norm or _soft_contains(point_norm, answer_norm)):
            matched += 1
    return matched / len(expected_points)


def _soft_contains(point_norm: str, answer_norm: str) -> bool:
    if len(point_norm) <= 4:
        return point_norm in answer_norm
    point_terms = tokens(point_norm)
    answer_terms = tokens(answer_norm)
    if not point_terms:
        return False
    return len(point_terms & answer_terms) / max(1, len(point_terms)) >= 0.65
