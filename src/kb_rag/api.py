from __future__ import annotations

import argparse
import json
from collections import Counter
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .db_eval import eval_failures, latest_eval_runs
from .db_retrieve import DEFAULT_DATABASE_URL, DEFAULT_VERSION_ID, DbHybridAnswerRetriever
from .hybrid import DEFAULT_VECTOR_PATH, HybridAnswerRetriever
from .loader import KnowledgePackage, load_package
from .render import render_answer
from .resources import (
    PROJECT_ROOT,
    build_bound_resources,
    recommend_resources,
    resource_intent_score,
    script_map_by_resource,
    search_resources,
)
from .retrieve import AnswerRetriever, RetrievalHit, confidence, normalize, tokens


DEFAULT_PACKAGE = Path("data/raw/ch01/第1章_道路工程数字化设计概述_知识库_v1.0完备版.json")


DEFAULT_CHAPTER_ID = "ch01"
DEFAULT_CHAPTERS = ("ch01", "ch02", "ch03", "ch04", "ch05", "ch06", "ch07", "ch08", "ch09", "ch10", "ch11")
DEFAULT_PACKAGE = next((PROJECT_ROOT / "data/raw/ch01").glob("*.json"), DEFAULT_PACKAGE)
AUTO_CHAPTER_MIN_SCORE = 70.0
AUTO_CHAPTER_MARGIN = 45.0
AUTO_CHAPTER_STRONG_SCORE = 110.0
AUTO_CHAPTER_STRONG_MARGIN = 35.0
SOURCE_REVIEW_BOUNDARY_PATH = PROJECT_ROOT / "output" / "ch10_ch11_source_boundary_review_2026-06-05.json"
SOURCE_REVIEW_APPROVAL_PATHS = {
    "template": PROJECT_ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.template.json",
    "draft": PROJECT_ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.draft.json",
    "formal": PROJECT_ROOT / "data" / "review" / "ch10_ch11_source_boundary_manual_approvals.json",
    "proposed": PROJECT_ROOT / "data" / "review" / "ch10_p1_source_boundary_manual_approvals.proposed.json",
}
SOURCE_REVIEW_ALLOWED_DECISIONS = {
    "",
    "confirm_candidate_anchor",
    "confirm_teaching_summary",
    "confirm_boundary_fragment",
    "split_required",
    "reject_candidate",
    "manual_anchor_pending",
}


class ApiState:
    def __init__(self, package: KnowledgePackage, database_url: str | None = None, version_id: str = DEFAULT_VERSION_ID):
        self.package = package
        self.chapter_id = _chapter_id(package)
        self.retriever = AnswerRetriever(package)
        self.hybrid_retriever: HybridAnswerRetriever | None = None
        self.db_hybrid_retriever: DbHybridAnswerRetriever | None = None
        self.database_url = database_url
        self.version_id = version_id
        self.resources = build_bound_resources(package.resources)
        self.script_by_resource = script_map_by_resource(package.interactive_scripts)
        self.direct_question_matches = build_direct_question_matches(package, self.chapter_id)
        self.video_by_id = {
            str(row.get("video_id")): row
            for row in package.data.get("Video_Resources", [])
            if isinstance(row, dict) and row.get("video_id")
        }
        self.video_segment_by_id = {
            str(row.get("segment_id") or row.get("video_segment_id")): row
            for row in package.video_segments
            if isinstance(row, dict) and (row.get("segment_id") or row.get("video_segment_id"))
        }
        self.screenshot_by_id = {
            str(row.get("screenshot_id")): row
            for row in package.screenshot_resources
            if isinstance(row, dict) and row.get("screenshot_id")
        }

    def hybrid(self) -> HybridAnswerRetriever:
        if self.hybrid_retriever is None:
            self.hybrid_retriever = HybridAnswerRetriever(self.package, vector_path=DEFAULT_VECTOR_PATH)
        return self.hybrid_retriever

    def db_hybrid(self) -> DbHybridAnswerRetriever:
        if self.db_hybrid_retriever is None:
            self.db_hybrid_retriever = DbHybridAnswerRetriever(
                self.package,
                dsn=self.database_url or DEFAULT_DATABASE_URL,
                version_id=self.version_id,
            )
        return self.db_hybrid_retriever


def make_handler(states: dict[str, ApiState], default_chapter_id: str = DEFAULT_CHAPTER_ID):
    class Handler(BaseHTTPRequestHandler):
        server_version = "RoadKbRag/0.1"

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            state = _select_state(states, params, default_chapter_id)

            if parsed.path == "/health":
                self._json(
                    {
                        "ok": True,
                        "chapter": state.chapter_id,
                        "chapters": health_chapters(states),
                        "answer_cards": len(state.package.answer_cards),
                        "qa_cases": len(state.package.qa_cases),
                        "resources": len(state.resources),
                        "version_id": state.version_id,
                        "database_enabled": bool(state.database_url),
                    }
                )
                return

            if parsed.path == "/ask":
                question = (params.get("q") or params.get("question") or [""])[0].strip()
                if not question:
                    self._json({"error": "Missing q parameter"}, status=HTTPStatus.BAD_REQUEST)
                    return
                top_k = int((params.get("top_k") or ["5"])[0])
                use_vectors = _truthy((params.get("use_vectors") or ["false"])[0])
                use_db = _truthy((params.get("use_db") or ["false"])[0])
                if _auto_chapter_enabled(params):
                    self._json(
                        answer_payload_auto(
                            states,
                            state,
                            question,
                            top_k=top_k,
                            use_vectors=use_vectors,
                            use_db=use_db,
                        )
                    )
                else:
                    self._json(answer_payload(state, question, top_k=top_k, use_vectors=use_vectors, use_db=use_db))
                return

            if parsed.path == "/resources":
                self._json({"resources": enriched_resources(state)})
                return

            if parsed.path == "/interactive-scripts":
                self._json({"interactive_scripts": interactive_scripts_payload(state)})
                return

            if parsed.path == "/operation-tasks":
                self._json(operation_tasks_payload(state))
                return

            if parsed.path == "/operation-task":
                task_id = (params.get("id") or params.get("task_id") or [""])[0].strip()
                detail = operation_task_detail(state, task_id)
                if not detail:
                    self._json({"error": "Operation task not found"}, status=HTTPStatus.NOT_FOUND)
                    return
                self._json(detail)
                return

            if parsed.path == "/answer-card":
                answer_id = (params.get("id") or params.get("answer_id") or [""])[0].strip()
                detail = answer_card_detail(state, answer_id)
                if not detail:
                    self._json({"error": "Answer card not found"}, status=HTTPStatus.NOT_FOUND)
                    return
                self._json(detail)
                return

            if parsed.path == "/eval-runs":
                limit = int((params.get("limit") or ["5"])[0])
                try:
                    self._json({"runs": latest_eval_runs(dsn=state.database_url or DEFAULT_DATABASE_URL, limit=limit)})
                except Exception as exc:  # pragma: no cover - defensive API boundary
                    self._json({"error": str(exc)}, status=HTTPStatus.SERVICE_UNAVAILABLE)
                return

            if parsed.path == "/eval-failures":
                run_id = (params.get("run_id") or [""])[0].strip() or None
                limit = int((params.get("limit") or ["20"])[0])
                try:
                    self._json({"failures": eval_failures(dsn=state.database_url or DEFAULT_DATABASE_URL, run_id=run_id, limit=limit)})
                except Exception as exc:  # pragma: no cover - defensive API boundary
                    self._json({"error": str(exc)}, status=HTTPStatus.SERVICE_UNAVAILABLE)
                return

            if parsed.path == "/source-review-approvals":
                target = (params.get("target") or ["draft"])[0].strip() or "draft"
                payload = source_review_approval_payload(target)
                status = HTTPStatus.OK if payload.get("ok", True) else HTTPStatus.BAD_REQUEST
                self._json(payload, status=status)
                return

            self._json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path not in {"/ask", "/source-review-approvals"}:
                self._json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length).decode("utf-8") if length else "{}"
                payload = json.loads(body)
            except (ValueError, json.JSONDecodeError):
                self._json({"error": "Invalid JSON body"}, status=HTTPStatus.BAD_REQUEST)
                return

            if parsed.path == "/source-review-approvals":
                params = parse_qs(parsed.query)
                target = str(payload.get("target") or (params.get("target") or ["draft"])[0] or "draft").strip()
                result = save_source_review_approvals(target, payload)
                status = HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST
                self._json(result, status=status)
                return

            question = str(payload.get("question") or payload.get("q") or "").strip()
            if not question:
                self._json({"error": "Missing question"}, status=HTTPStatus.BAD_REQUEST)
                return
            state = _select_state(states, payload, default_chapter_id)
            top_k = int(payload.get("top_k") or 5)
            use_vectors = _truthy(payload.get("use_vectors"))
            use_db = _truthy(payload.get("use_db"))
            if _auto_chapter_enabled(payload):
                self._json(
                    answer_payload_auto(
                        states,
                        state,
                        question,
                        top_k=top_k,
                        use_vectors=use_vectors,
                        use_db=use_db,
                    )
                )
            else:
                self._json(answer_payload(state, question, top_k=top_k, use_vectors=use_vectors, use_db=use_db))

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT.value)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            return

        def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status.value)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _select_state(states: dict[str, ApiState], values: object, default_chapter_id: str) -> ApiState:
    chapter_id = default_chapter_id
    if isinstance(values, dict):
        raw = values.get("chapter_id") or values.get("chapter")
        if isinstance(raw, list):
            raw = raw[0] if raw else None
        if raw:
            chapter_id = str(raw)
    return states.get(chapter_id) or states[default_chapter_id]


def source_review_approval_path(target: str) -> Path | None:
    return SOURCE_REVIEW_APPROVAL_PATHS.get(str(target or "").strip())


def source_review_approval_payload(target: str) -> dict[str, Any]:
    path = source_review_approval_path(target)
    if path is None:
        return {
            "ok": False,
            "error": f"Unknown source review approval target: {target}",
            "allowed_targets": sorted(SOURCE_REVIEW_APPROVAL_PATHS),
        }
    if not path.exists():
        return {
            "ok": True,
            "target": target,
            "path": str(path),
            "exists": False,
            "payload": None,
            "validation": {
                "ok": True,
                "errors": [],
                "warnings": ["Approval file is missing."],
                "summary": {},
            },
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "target": target,
            "path": str(path),
            "exists": True,
            "error": f"Could not read approval file: {exc}",
        }
    validation = validate_source_review_approval_payload(payload)
    return {
        "ok": validation["ok"],
        "target": target,
        "path": str(path),
        "exists": True,
        "payload": payload,
        "validation": validation,
    }


def save_source_review_approvals(target: str, payload: dict[str, Any]) -> dict[str, Any]:
    if target not in {"draft", "formal"}:
        return {
            "ok": False,
            "error": "Only draft and formal approval targets can be written through the API.",
            "target": target,
        }
    if target == "formal" and payload.get("confirm_write_formal") is not True:
        return {
            "ok": False,
            "target": target,
            "error": "Writing formal approvals requires confirm_write_formal=true in the JSON body.",
        }
    validation = validate_source_review_approval_payload(payload)
    if not validation["ok"]:
        return {
            "ok": False,
            "target": target,
            "validation": validation,
            "error": "Approval payload failed validation.",
        }
    path = SOURCE_REVIEW_APPROVAL_PATHS[target]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "target": target,
        "path": str(path),
        "validation": validation,
    }


def validate_source_review_approval_payload(payload: object) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "errors": ["Approval payload must be a JSON object."],
            "warnings": [],
            "summary": {},
        }

    known = known_source_review_items()
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        errors.append("approvals.decisions must be a list")
        decisions = []

    counts: Counter[str] = Counter()
    applied_counts: Counter[str] = Counter()
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(decisions, 1):
        if not isinstance(item, dict):
            errors.append(f"decisions[{index}] must be an object")
            continue
        chapter_id = str(item.get("chapter_id") or "").strip()
        chunk_id = str(item.get("chunk_id") or "").strip()
        decision = str(item.get("decision") or "").strip()
        key = (chapter_id, chunk_id)
        counts[decision] += 1
        if decision:
            applied_counts[decision] += 1
        if not chapter_id or not chunk_id:
            errors.append(f"decisions[{index}] missing chapter_id or chunk_id")
            continue
        if key in seen:
            errors.append(f"Duplicate approval decision for {chapter_id}/{chunk_id}")
        seen.add(key)
        known_item = known.get(key)
        if known_item is None:
            errors.append(f"Unknown review item: {chapter_id}/{chunk_id}")
            continue
        if decision not in SOURCE_REVIEW_ALLOWED_DECISIONS:
            errors.append(f"{chapter_id}/{chunk_id} has invalid decision: {decision}")
            continue
        if not decision:
            continue
        _validate_source_review_decision_status(
            chapter_id,
            chunk_id,
            decision,
            str(known_item.get("review_status") or ""),
            warnings,
        )
        if decision.startswith("confirm_"):
            _validate_source_review_paragraph_span(chapter_id, chunk_id, item, errors)
            if not str(item.get("reviewer_notes") or "").strip():
                warnings.append(f"{chapter_id}/{chunk_id} confirmation has no reviewer_notes")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "items": len(decisions),
            "decisions_by_value": dict(sorted(counts.items())),
            "non_empty_decisions": sum(applied_counts.values()),
            "non_empty_by_value": dict(sorted(applied_counts.items())),
        },
    }


def known_source_review_items() -> dict[tuple[str, str], dict[str, Any]]:
    if not SOURCE_REVIEW_BOUNDARY_PATH.exists():
        return {}
    boundary = json.loads(SOURCE_REVIEW_BOUNDARY_PATH.read_text(encoding="utf-8"))
    known: dict[tuple[str, str], dict[str, Any]] = {}
    for chapter_id, chapter in (boundary.get("chapters") or {}).items():
        if not isinstance(chapter, dict):
            continue
        for item in chapter.get("source_boundary_reviews") or []:
            if isinstance(item, dict):
                known[(str(chapter_id), str(item.get("chunk_id") or ""))] = item
    return known


def _validate_source_review_decision_status(
    chapter_id: str,
    chunk_id: str,
    decision: str,
    expected_status: str,
    warnings: list[str],
) -> None:
    expected_decisions = {
        "candidate_anchor_review": {"confirm_candidate_anchor", "reject_candidate", "manual_anchor_pending"},
        "term_supported_summary_review": {"confirm_teaching_summary", "reject_candidate", "manual_anchor_pending"},
        "boundary_fragment_review": {"confirm_boundary_fragment", "split_required", "manual_anchor_pending"},
        "manual_anchor_required": {"manual_anchor_pending", "confirm_candidate_anchor", "reject_candidate"},
    }
    allowed = expected_decisions.get(expected_status, set())
    if allowed and decision not in allowed:
        warnings.append(
            f"{chapter_id}/{chunk_id} decision {decision} is unusual for review_status {expected_status}; "
            f"usual values: {sorted(allowed)}"
        )


def _validate_source_review_paragraph_span(
    chapter_id: str,
    chunk_id: str,
    item: dict[str, Any],
    errors: list[str],
) -> None:
    start = item.get("approved_paragraph_start")
    end = item.get("approved_paragraph_end")
    try:
        start_num = int(start)
        end_num = int(end)
    except (TypeError, ValueError):
        errors.append(f"{chapter_id}/{chunk_id} confirmation requires numeric approved_paragraph_start/end")
        return
    if start_num <= 0 or end_num < start_num:
        errors.append(f"{chapter_id}/{chunk_id} has invalid approved paragraph range: {start}-{end}")


def _auto_chapter_enabled(values: object) -> bool:
    if not isinstance(values, dict):
        return False
    raw = values.get("auto_chapter") or values.get("auto")
    if raw is None:
        raw = values.get("chapter_id") or values.get("chapter")
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return False
    return str(raw).strip().lower() in {"1", "true", "yes", "on", "auto", "all"}


def _chapter_id(package: KnowledgePackage) -> str:
    for rows in (package.answer_cards, package.knowledge_points, package.resources):
        for row in rows:
            if isinstance(row, dict) and row.get("chapter_id"):
                return str(row["chapter_id"])
    return DEFAULT_CHAPTER_ID


def _version_id(chapter_id: str) -> str:
    return f"{chapter_id}_kb_v1.0"


def _package_paths() -> list[Path]:
    paths: list[Path] = []
    for chapter_id in DEFAULT_CHAPTERS:
        path = next((PROJECT_ROOT / "data/raw" / chapter_id).glob("*.json"), None)
        if path:
            paths.append(path)
    return paths


def health_chapters(states: dict[str, ApiState]) -> list[dict[str, object]]:
    return [
        {
            "chapter_id": chapter_id,
            "version_id": state.version_id,
            "answer_cards": len(state.package.answer_cards),
            "qa_cases": len(state.package.qa_cases),
            "resources": len(state.resources),
        }
        for chapter_id, state in sorted(states.items())
    ]


def answer_card_detail(state: ApiState, answer_id: str) -> dict[str, object] | None:
    card = next((item for item in state.package.answer_cards if item.get("answer_id") == answer_id), None)
    if not card:
        return None

    related_kps = set(str(kp) for kp in (card.get("related_kps") or []))
    evidence_chunks = set(str(chunk) for chunk in (card.get("evidence_chunks") or []))
    kps = [kp for kp in state.package.knowledge_points if str(kp.get("kp_id")) in related_kps]
    chunks = [chunk for chunk in state.package.source_chunks if str(chunk.get("chunk_id")) in evidence_chunks]
    resources = recommend_resources(card, state.resources)
    qa_cases = [
        case
        for case in state.package.qa_cases
        if str(case.get("expected_answer_card") or "") == answer_id
    ][:20]
    return {
        "answer_card": card,
        "rendered_answer": render_answer(card),
        "knowledge_points": kps,
        "source_chunks": chunks,
        "recommended_resources": [_resource_payload(item, state.script_by_resource.get(str(item.get("resource_id")))) for item in resources],
        "qa_cases": qa_cases,
    }


def enriched_resources(state: ApiState) -> list[dict[str, object]]:
    return [
        _resource_payload(item, state.script_by_resource.get(str(item.get("resource_id"))))
        for item in state.resources
    ]


def interactive_scripts_payload(state: ApiState) -> list[dict[str, object]]:
    resources = {
        str(row.get("resource_id")): _resource_payload(
            row,
            state.script_by_resource.get(str(row.get("resource_id"))),
        )
        for row in state.resources
    }
    scripts = []
    for row in state.package.interactive_scripts:
        item = dict(row)
        item["resource"] = resources.get(str(row.get("resource_id")))
        scripts.append(item)
    return scripts


def operation_tasks_payload(state: ApiState) -> dict[str, object]:
    steps_by_task = _group_by(state.package.operation_steps, "task_id")
    errors_by_task = _group_errors_by_task(state.package.common_errors)
    answers_by_task = _group_by(state.package.answer_cards, "related_task")
    tasks = []
    for row in state.package.operation_tasks:
        if not isinstance(row, dict):
            continue
        task_id = str(row.get("task_id") or "")
        task_steps = sorted(steps_by_task.get(task_id, []), key=_step_sort_key)
        task_errors = errors_by_task.get(task_id, [])
        task_answers = answers_by_task.get(task_id, [])
        resources = _resources_for_operation_task(state, row, task_answers, limit=3)
        tasks.append(
            {
                "task_id": task_id,
                "chapter_id": row.get("chapter_id") or state.chapter_id,
                "section_id": row.get("section_id"),
                "task_name": row.get("task_name") or row.get("title") or task_id,
                "task_goal": row.get("task_goal") or row.get("goal") or row.get("description") or "",
                "prerequisite": row.get("prerequisite") or row.get("precondition") or "",
                "output_result": row.get("output_result") or row.get("expected_output") or "",
                "difficulty": row.get("difficulty") or "",
                "related_kps": _as_list(row.get("related_kps")),
                "step_count": len(task_steps),
                "error_count": len(task_errors),
                "answer_count": len(task_answers),
                "resource_count": len(resources),
                "primary_resource": resources[0] if resources else None,
            }
        )
    return {
        "chapter_id": state.chapter_id,
        "task_count": len(tasks),
        "step_count": len(state.package.operation_steps),
        "error_count": len(state.package.common_errors),
        "tasks": tasks,
    }


def operation_task_detail(state: ApiState, task_id: str) -> dict[str, object] | None:
    task = next((row for row in state.package.operation_tasks if str(row.get("task_id") or "") == task_id), None)
    if not task:
        return None
    steps = sorted(
        [row for row in state.package.operation_steps if str(row.get("task_id") or "") == task_id],
        key=_step_sort_key,
    )
    step_ids = {str(row.get("step_id") or "") for row in steps}
    errors = [
        row
        for row in state.package.common_errors
        if str(row.get("task_id") or row.get("related_task") or "") == task_id
        or str(row.get("related_step") or "") in step_ids
    ]
    answers = [
        row
        for row in state.package.answer_cards
        if str(row.get("related_task") or "") == task_id
    ][:20]
    resources = _resources_for_operation_task(state, task, answers, limit=8)
    return {
        "chapter_id": state.chapter_id,
        "task": task,
        "steps": [_operation_step_payload(row, state) for row in steps],
        "errors": [_common_error_payload(row, state) for row in errors],
        "answer_cards": [
            {
                "answer_id": row.get("answer_id"),
                "canonical_question": row.get("canonical_question"),
                "answer_mode": row.get("answer_mode"),
                "must_include": row.get("must_include") or [],
            }
            for row in answers
        ],
        "recommended_resources": resources,
        "media_summary": _operation_media_summary(state, steps, errors),
    }


def _operation_step_payload(row: dict[str, object], state: ApiState) -> dict[str, object]:
    screenshot_id = str(row.get("screenshot_id") or "")
    video_segment_id = str(row.get("video_segment_id") or "")
    return {
        "step_id": row.get("step_id"),
        "task_id": row.get("task_id"),
        "step_no": row.get("step_no") or row.get("step_order"),
        "step_title": row.get("step_title") or row.get("title") or row.get("action"),
        "action": row.get("action") or row.get("operation") or "",
        "command": row.get("command") or "",
        "parameter": row.get("parameter") or row.get("parameters") or "",
        "expected_result": row.get("expected_result") or "",
        "check_point": row.get("check_point") or row.get("must_check") or "",
        "screenshot_id": screenshot_id,
        "video_segment_id": video_segment_id,
        "screenshot": _screenshot_payload(state, screenshot_id),
        "video_segment": _video_segment_payload(state, video_segment_id),
    }


def _common_error_payload(row: dict[str, object], state: ApiState) -> dict[str, object]:
    video_segment_id = str(row.get("video_segment_id") or row.get("related_video_segment") or "")
    return {
        "error_id": row.get("error_id"),
        "task_id": row.get("task_id") or row.get("related_task"),
        "related_step": row.get("related_step") or "",
        "phenomenon": row.get("phenomenon") or row.get("error_phenomenon") or row.get("error_symptom") or row.get("title") or "",
        "cause": row.get("cause") or row.get("possible_cause") or row.get("possible_causes") or row.get("reason") or "",
        "solution": row.get("solution") or row.get("fix") or row.get("handling") or row.get("solution_steps") or "",
        "check_method": row.get("check_method") or row.get("diagnosis") or "",
        "video_segment_id": video_segment_id,
        "video_segment": _video_segment_payload(state, video_segment_id),
    }


def _video_segment_payload(state: ApiState, segment_id: str) -> dict[str, object] | None:
    segment_id = str(segment_id or "").strip()
    if not segment_id:
        return None
    row = state.video_segment_by_id.get(segment_id)
    if not row:
        return {
            "segment_id": segment_id,
            "available": False,
            "status": "missing_metadata",
        }
    video = state.video_by_id.get(str(row.get("video_id") or ""))
    file_path = str((video or {}).get("file_path") or row.get("file_path") or "")
    check_path = Path(file_path)
    if file_path and not check_path.is_absolute():
        check_path = PROJECT_ROOT / file_path
    exists = bool(file_path) and check_path.exists()
    status = str(row.get("status") or (video or {}).get("status") or "")
    placeholder = _placeholder_status(status) or _placeholder_status(str((video or {}).get("status") or ""))
    return {
        "segment_id": row.get("segment_id") or row.get("video_segment_id") or segment_id,
        "video_id": row.get("video_id"),
        "title": row.get("title") or (video or {}).get("title") or segment_id,
        "file_path": file_path,
        "url_path": "/" + file_path.replace("\\", "/") if file_path else "",
        "start_time": row.get("start_time") or row.get("start_sec") or "",
        "end_time": row.get("end_time") or row.get("end_sec") or "",
        "status": status or "placeholder",
        "exists": exists,
        "available": exists and not placeholder,
    }


def _screenshot_payload(state: ApiState, screenshot_id: str) -> dict[str, object] | None:
    screenshot_id = str(screenshot_id or "").strip()
    if not screenshot_id:
        return None
    row = state.screenshot_by_id.get(screenshot_id)
    if not row:
        return {
            "screenshot_id": screenshot_id,
            "available": False,
            "status": "missing_metadata",
        }
    file_path = str(row.get("file_path") or "")
    check_path = Path(file_path)
    if file_path and not check_path.is_absolute():
        check_path = PROJECT_ROOT / file_path
    exists = bool(file_path) and check_path.exists()
    status = str(row.get("status") or "")
    return {
        "screenshot_id": row.get("screenshot_id") or screenshot_id,
        "title": row.get("title") or screenshot_id,
        "file_path": file_path,
        "url_path": "/" + file_path.replace("\\", "/") if file_path else "",
        "status": status or "placeholder",
        "exists": exists,
        "available": exists and not _placeholder_status(status),
    }


def _operation_media_summary(
    state: ApiState,
    steps: list[dict[str, object]],
    errors: list[dict[str, object]],
) -> dict[str, int]:
    video_ids = {
        str(row.get("video_segment_id") or row.get("related_video_segment") or "")
        for row in [*steps, *errors]
        if str(row.get("video_segment_id") or row.get("related_video_segment") or "").strip()
    }
    screenshot_ids = {
        str(row.get("screenshot_id") or "")
        for row in steps
        if str(row.get("screenshot_id") or "").strip()
    }
    video_payloads = [_video_segment_payload(state, item) for item in video_ids]
    screenshot_payloads = [_screenshot_payload(state, item) for item in screenshot_ids]
    return {
        "video_segments": len(video_ids),
        "available_video_segments": sum(1 for item in video_payloads if item and item.get("available")),
        "screenshots": len(screenshot_ids),
        "available_screenshots": sum(1 for item in screenshot_payloads if item and item.get("available")),
    }


def _placeholder_status(status: str) -> bool:
    text = str(status or "").strip().lower()
    return (
        not text
        or text.startswith("placeholder")
        or text.startswith("needs_")
        or "待" in text
        or "placeholder" in text
    )


def _render_operation_answer(state: ApiState, card: dict[str, object]) -> dict[str, object] | None:
    task_id = str(card.get("related_task") or "")
    if not task_id:
        return None
    detail = operation_task_detail(state, task_id)
    if not detail:
        return None

    task = detail.get("task") or {}
    steps = detail.get("steps") or []
    errors = detail.get("errors") or []
    mode = str(card.get("answer_mode") or "")
    question_type = str(card.get("question_type") or "")
    task_name = str(task.get("task_name") or task.get("title") or task_id)
    lines = [
        f"针对“{card.get('canonical_question') or task_name}”，可按操作任务“{task_name}”来处理。",
        "",
    ]

    goal = str(task.get("task_goal") or "")
    prerequisite = str(task.get("prerequisite") or "")
    output_result = str(task.get("output_result") or "")
    if goal:
        lines.append(f"- 操作目标：{goal}")
    if prerequisite:
        lines.append(f"- 前置条件：{prerequisite}")
    if output_result:
        lines.append(f"- 预期成果：{output_result}")
    if goal or prerequisite or output_result:
        lines.append("")

    if mode == "troubleshoot" or "error" in question_type:
        lines.extend(_operation_error_lines(errors, card))
        lines.append("")
        lines.extend(_operation_check_lines(steps, card))
    elif mode == "checklist" or "checklist" in question_type:
        lines.extend(_operation_check_lines(steps, card))
        if errors:
            lines.append("")
            lines.append("常见风险：")
            lines.extend(f"- {item.get('phenomenon') or item.get('error_id')}" for item in errors[:3])
    else:
        lines.append("操作步骤：")
        lines.extend(_operation_step_lines(steps, card))
        if errors:
            lines.append("")
            lines.append("容易出错的地方：")
            lines.extend(_operation_error_summary_lines(errors[:3]))

    resources = detail.get("recommended_resources") or []
    if resources:
        lines.append("")
        lines.append("建议配合资源：")
        lines.extend(f"- {item.get('title') or item.get('resource_id')}" for item in resources[:3])

    media_summary = detail.get("media_summary") or {}
    media_lines = _operation_media_lines(detail)
    if media_lines:
        lines.append("")
        lines.extend(media_lines)

    return {
        "answer": "\n".join(str(line) for line in lines if line is not None).strip(),
        "answer_mode": mode or "operation",
        "trace": {
            "renderer": "operation_task",
            "task_id": task_id,
            "step_count": len(steps),
            "error_count": len(errors),
            "resource_count": len(resources),
            "media_summary": media_summary,
        },
    }


def _operation_question_match(state: ApiState, question: str) -> dict[str, object] | None:
    intent = _operation_intent(question)
    if not intent:
        return None
    q_norm = normalize(question)
    best: dict[str, object] | None = None
    best_score = 0.0
    for task in state.package.operation_tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("task_id") or "")
        task_name = str(task.get("task_name") or task.get("title") or "")
        if not task_id or not task_name:
            continue
        name_norm = normalize(task_name)
        goal_norm = normalize(str(task.get("task_goal") or ""))
        score = 0.0
        reasons: list[str] = []
        if name_norm and name_norm in q_norm:
            score += 140
            reasons.append("task_name_match")
        elif q_norm and q_norm in name_norm:
            score += 100
            reasons.append("question_in_task_name")
        elif goal_norm and len(set(tokens(question)) & tokens(task_name)) >= 2:
            score += 60
            reasons.append("task_token_overlap")
        if goal_norm and (set(tokens(question)) & tokens(str(task.get("task_goal") or ""))):
            score += 15
            reasons.append("goal_overlap")
        if score > best_score:
            best_score = score
            best = {"task": task, "score": score, "reasons": reasons, "intent": intent}
    if not best or best_score < 80:
        return None
    card = _operation_card_for_task(state, str(best["task"].get("task_id") or ""), str(best["intent"]))
    best["card"] = card
    return best


def _operation_intent(question: str) -> str:
    q_norm = normalize(question)
    error_terms = ["失败", "错误", "异常", "不显示", "不正确", "错位", "输出为空", "不能", "无法", "排查", "怎么办"]
    checklist_terms = ["检查", "核对", "注意", "要点"]
    step_terms = ["如何", "怎么", "怎样", "步骤", "操作", "怎么做", "流程", "创建", "设置", "导入", "添加", "生成"]
    if any(normalize(term) in q_norm for term in error_terms):
        return "troubleshoot"
    if any(normalize(term) in q_norm for term in checklist_terms):
        return "checklist"
    if any(normalize(term) in q_norm for term in step_terms):
        return "step"
    return ""


def _operation_card_for_task(state: ApiState, task_id: str, intent: str) -> dict[str, object] | None:
    cards = [
        card
        for card in state.package.answer_cards
        if isinstance(card, dict) and str(card.get("related_task") or "") == task_id
    ]
    if not cards:
        return None
    preferred_modes = {
        "troubleshoot": ["troubleshoot"],
        "checklist": ["checklist"],
        "step": ["step"],
    }.get(intent, ["step"])
    for mode in preferred_modes:
        match = next((card for card in cards if str(card.get("answer_mode") or "") == mode), None)
        if match:
            return match
    return cards[0]


def _should_answer_with_operation(
    operation_match: dict[str, object],
    hits: list[object],
    resource_hits: list[dict[str, object]],
) -> bool:
    card = operation_match.get("card")
    task = operation_match.get("task")
    task_id = str(task.get("task_id") or "") if isinstance(task, dict) else ""
    if not task_id:
        return False
    if card:
        card_id = str(card.get("answer_id") or "")
        if hits and hits[0].answer_id == card_id:
            return True
    top_related_task = str(hits[0].card.get("related_task") or "") if hits else ""
    if top_related_task == task_id:
        return True
    if float(operation_match.get("score") or 0) >= 120:
        return True
    if resource_hits:
        top_resource = resource_hits[0].get("resource") or {}
        if isinstance(top_resource, dict) and top_resource.get("suppress_recommendation"):
            return True
    return False


def _operation_match_payload(
    state: ApiState,
    question: str,
    operation_match: dict[str, object],
    hits: list[object],
    resource_hits: list[dict[str, object]],
    hybrid_trace: object | None,
    use_vectors: bool,
    use_db: bool,
) -> dict[str, object]:
    task = operation_match["task"]
    card = operation_match.get("card") or {
        "answer_id": f"operation:{task.get('task_id')}",
        "canonical_question": question,
        "answer_mode": operation_match.get("intent") or "step",
        "question_type": f"operation_{operation_match.get('intent') or 'step'}",
        "related_task": task.get("task_id"),
        "answer_points": [],
    }
    operation_answer = _render_operation_answer(state, card) or {"answer": render_answer(card), "trace": None}
    detail = operation_task_detail(state, str(task.get("task_id") or ""))
    resources = detail.get("recommended_resources", []) if detail else [_resource_hit_payload(hit, state) for hit in resource_hits]
    answer_id = str(card.get("answer_id") or f"operation:{task.get('task_id')}")
    return {
        "question": question,
        "chapter_id": state.chapter_id,
        "answer_id": answer_id,
        "confidence": "high",
        "answer_mode": card.get("answer_mode") or operation_match.get("intent") or "step",
        "answer": operation_answer["answer"],
        "top_hits": _top_hit_payloads(hits),
        "recommended_resources": resources,
        "trace": {
            "retrieval_order": [
                "Operation_Tasks",
                "Operation_Steps",
                "Common_Errors",
                "Answer_Cards",
                "Resources",
            ],
            "selected_answer_id": answer_id,
            "selected_task_id": task.get("task_id"),
            "selected_score": round(float(operation_match.get("score") or 0), 3),
            "selected_reasons": operation_match.get("reasons") or [],
            "candidate_count": len(hits),
            "resource_count": len(resources),
            "resource_direct_count": len(resource_hits),
            "operation_answer": operation_answer.get("trace"),
            "source_chunks_policy": "evidence_only_no_direct_output",
            "retriever": _retriever_name(use_vectors=use_vectors, use_db=use_db),
            "hybrid": {
                "keyword_top": hybrid_trace.keyword_top,
                "vector_top": hybrid_trace.vector_top,
            }
            if hybrid_trace
            else None,
        },
    }


def _operation_step_lines(steps: list[dict[str, object]], card: dict[str, object]) -> list[str]:
    fallback = [str(item) for item in (card.get("answer_points") or []) if str(item).strip()]
    if not steps:
        return [f"步骤{index}：{point}" for index, point in enumerate(fallback, 1)] or ["- 暂无结构化步骤。"]
    lines = []
    for index, step in enumerate(steps, 1):
        title = str(step.get("step_title") or f"步骤 {index}")
        command = str(step.get("command") or "").strip()
        expected = str(step.get("expected_result") or "").strip()
        check = str(step.get("check_point") or "").strip()
        detail_parts = []
        if command:
            detail_parts.append(f"命令/工具：{command}")
        if expected:
            detail_parts.append(f"结果：{expected}")
        if check:
            detail_parts.append(f"检查：{check}")
        video = step.get("video_segment")
        if isinstance(video, dict) and video.get("available"):
            detail_parts.append(f"视频：{video.get('title') or video.get('segment_id')} {video.get('start_time') or ''}-{video.get('end_time') or ''}".strip())
        screenshot = step.get("screenshot")
        if isinstance(screenshot, dict) and screenshot.get("available"):
            detail_parts.append(f"截图：{screenshot.get('title') or screenshot.get('screenshot_id')}")
        suffix = f"（{'；'.join(detail_parts)}）" if detail_parts else ""
        lines.append(f"步骤{index}：{title}{suffix}")
    return lines


def _operation_check_lines(steps: list[dict[str, object]], card: dict[str, object]) -> list[str]:
    checks = []
    for step in steps:
        title = str(step.get("step_title") or "").strip()
        expected = str(step.get("expected_result") or "").strip()
        check = str(step.get("check_point") or "").strip()
        if check:
            checks.append(f"- {title}：{check}")
        elif expected:
            checks.append(f"- {title}：确认{expected}")
    if checks:
        return ["检查要点：", *checks[:8]]
    points = [str(item) for item in (card.get("must_include") or card.get("answer_points") or []) if str(item).strip()]
    return ["检查要点：", *(f"- {point}" for point in points[:8])] if points else ["检查要点：", "- 暂无结构化检查项。"]


def _operation_error_lines(errors: list[dict[str, object]], card: dict[str, object]) -> list[str]:
    if not errors:
        points = [str(item) for item in (card.get("answer_points") or []) if str(item).strip()]
        return ["排查顺序：", *(f"- {point}" for point in points[:8])] if points else ["排查顺序：", "- 暂无结构化错误记录。"]
    lines = ["排查顺序："]
    for index, item in enumerate(errors[:5], 1):
        phenomenon = str(item.get("phenomenon") or item.get("error_id") or f"问题 {index}")
        cause = str(item.get("cause") or "").strip()
        solution = str(item.get("solution") or "").strip()
        related_step = str(item.get("related_step") or "").strip()
        line = f"- {phenomenon}"
        details = []
        if cause:
            details.append(f"可能原因：{cause}")
        if solution:
            details.append(f"处理：{solution}")
        if related_step:
            details.append(f"关联步骤：{related_step}")
        if details:
            line += f"（{'；'.join(details)}）"
        lines.append(line)
    return lines


def _operation_error_summary_lines(errors: list[dict[str, object]]) -> list[str]:
    lines = []
    for item in errors:
        phenomenon = str(item.get("phenomenon") or item.get("error_id") or "").strip()
        solution = str(item.get("solution") or "").strip()
        if phenomenon and solution:
            lines.append(f"- {phenomenon}：{solution}")
        elif phenomenon:
            lines.append(f"- {phenomenon}")
    return lines


def _operation_media_lines(detail: dict[str, object]) -> list[str]:
    summary = detail.get("media_summary") or {}
    video_total = int(summary.get("video_segments") or 0)
    video_available = int(summary.get("available_video_segments") or 0)
    screenshot_total = int(summary.get("screenshots") or 0)
    screenshot_available = int(summary.get("available_screenshots") or 0)
    if not video_total and not screenshot_total:
        return []
    if video_available or screenshot_available:
        lines = ["可用媒体："]
        for step in detail.get("steps") or []:
            video = step.get("video_segment")
            screenshot = step.get("screenshot")
            title = step.get("step_title") or step.get("step_id")
            if isinstance(video, dict) and video.get("available"):
                lines.append(f"- {title}：视频片段 {video.get('title') or video.get('segment_id')} {video.get('start_time') or ''}-{video.get('end_time') or ''}".strip())
            if isinstance(screenshot, dict) and screenshot.get("available"):
                lines.append(f"- {title}：截图 {screenshot.get('title') or screenshot.get('screenshot_id')}")
        return lines[:8]
    return [
        f"媒体状态：本任务已预留 {video_total} 个视频片段和 {screenshot_total} 张截图位置，正式视频/截图绑定后即可在任务详情中播放或查看。"
    ]


def _resources_for_operation_task(
    state: ApiState,
    task: dict[str, object],
    answers: list[dict[str, object]],
    limit: int,
) -> list[dict[str, object]]:
    seen: set[str] = set()
    results: list[dict[str, object]] = []
    query_text = " ".join(
        str(value or "")
        for value in [
            task.get("task_name"),
            task.get("task_goal"),
            task.get("output_result"),
            *_as_list(task.get("related_kps")),
        ]
    )
    for answer in answers:
        for resource in recommend_resources(answer, state.resources):
            resource_id = str(resource.get("resource_id") or "")
            if resource_id and resource_id not in seen:
                seen.add(resource_id)
                results.append(_resource_payload(resource, state.script_by_resource.get(resource_id)))
                if len(results) >= limit:
                    return results
    for hit in search_resources(query_text, state.resources, state.package.interactive_scripts, limit=limit):
        resource = hit["resource"]
        resource_id = str(resource.get("resource_id") or "")
        if resource_id and resource_id not in seen:
            seen.add(resource_id)
            results.append(_resource_payload(resource, state.script_by_resource.get(resource_id)))
            if len(results) >= limit:
                return results
    return results


def _group_by(rows: list[dict[str, object]], field: str) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get(field) or "")
        if key:
            grouped.setdefault(key, []).append(row)
    return grouped


def _group_errors_by_task(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        task_id = str(row.get("task_id") or row.get("related_task") or "")
        if task_id:
            grouped.setdefault(task_id, []).append(row)
    return grouped


def _step_sort_key(row: dict[str, object]) -> tuple[int, str]:
    raw = row.get("step_no") or row.get("step_order") or row.get("order") or row.get("step_id") or ""
    number = 9999
    for part in str(raw).replace("_", " ").split():
        if part.isdigit():
            number = int(part)
            break
    return number, str(row.get("step_id") or "")


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [part.strip() for part in str(value).replace("；", ";").split(";") if part.strip()]


def build_direct_question_matches(package: KnowledgePackage, chapter_id: str) -> dict[str, list[dict[str, object]]]:
    matches: dict[str, list[dict[str, object]]] = {}
    for card in package.answer_cards:
        answer_id = str(card.get("answer_id") or "")
        canonical = str(card.get("canonical_question") or "")
        canonical_norm = normalize(canonical)
        if canonical_norm:
            matches.setdefault(canonical_norm, []).append(
                {
                    "chapter_id": chapter_id,
                    "answer_id": answer_id,
                    "match_type": "canonical_question",
                    "canonical_question": canonical,
                    "priority": 120,
                }
            )
        for pattern in card.get("student_question_patterns", []) or []:
            pattern_norm = normalize(str(pattern or ""))
            if pattern_norm:
                matches.setdefault(pattern_norm, []).append(
                    {
                        "chapter_id": chapter_id,
                        "answer_id": answer_id,
                        "match_type": "student_question_pattern",
                        "canonical_question": canonical,
                        "priority": 180,
                    }
                )
    return matches


def _resource_payload(item: dict[str, object], script: dict[str, object] | None = None) -> dict[str, object]:
    file_path = str(item.get("file_path") or "")
    check_path = Path(file_path)
    if file_path and not check_path.is_absolute():
        check_path = PROJECT_ROOT / check_path
    exists = bool(file_path) and check_path.exists()
    formula_detail = item.get("formula_detail")
    table_detail = item.get("table_detail")
    structured_formula = (
        item.get("resource_type") == "formula"
        and isinstance(formula_detail, dict)
        and bool(formula_detail.get("expression"))
    )
    structured_table = (
        item.get("resource_type") == "table"
        and isinstance(table_detail, dict)
        and bool(table_detail.get("columns"))
        and bool(table_detail.get("rows"))
    )
    row = dict(item)
    row["exists"] = exists
    row["available"] = exists or structured_formula or structured_table
    row["url_path"] = "/" + file_path.replace("\\", "/") if file_path else ""
    if script:
        row["interactive_script"] = script
    return row


def answer_payload_auto(
    states: dict[str, ApiState],
    preferred_state: ApiState,
    question: str,
    top_k: int = 5,
    use_vectors: bool = False,
    use_db: bool = False,
) -> dict[str, object]:
    selected_state, routing = route_chapter(states, preferred_state, question)
    payload = answer_payload(
        selected_state,
        question,
        top_k=top_k,
        use_vectors=use_vectors,
        use_db=use_db,
    )
    payload["chapter_id"] = selected_state.chapter_id
    payload["requested_chapter_id"] = preferred_state.chapter_id
    trace = payload.get("trace")
    if isinstance(trace, dict):
        trace["chapter_routing"] = routing
    else:
        payload["trace"] = {"chapter_routing": routing}
    return payload


def route_chapter(
    states: dict[str, ApiState],
    preferred_state: ApiState,
    question: str,
) -> tuple[ApiState, dict[str, object]]:
    direct_state, direct_routing = _direct_chapter_route(states, preferred_state, question)
    if direct_state is not None:
        return direct_state, direct_routing

    resource_intent = resource_intent_score(question)
    candidates: list[dict[str, object]] = []
    best_state = preferred_state
    best_score = -1.0
    preferred_score = 0.0

    for chapter_id, state in sorted(states.items()):
        answer_hits = state.retriever.search(question, top_k=1)
        answer_hit = answer_hits[0] if answer_hits else None
        answer_score = float(answer_hit.score) if answer_hit else 0.0
        resource_score = 0.0
        resource_id = None
        if resource_intent:
            resource_hits = search_resources(question, state.resources, state.package.interactive_scripts, limit=1)
            if resource_hits:
                resource_score = float(resource_hits[0]["score"])
                resource_id = resource_hits[0]["resource"].get("resource_id")
        score = max(answer_score, resource_score) if resource_intent else answer_score
        candidate = {
            "chapter_id": state.chapter_id,
            "score": round(score, 3),
            "answer_score": round(answer_score, 3),
            "resource_score": round(resource_score, 3),
            "answer_id": answer_hit.answer_id if answer_hit else None,
            "resource_id": resource_id,
            "canonical_question": answer_hit.card.get("canonical_question") if answer_hit else None,
        }
        candidates.append(candidate)
        if state.chapter_id == preferred_state.chapter_id:
            preferred_score = score
        if score > best_score:
            best_score = score
            best_state = state

    selected_state = preferred_state
    decision = "keep_preferred"
    margin = best_score - preferred_score
    if best_state.chapter_id != preferred_state.chapter_id:
        strong_match = best_score >= AUTO_CHAPTER_STRONG_SCORE and margin >= AUTO_CHAPTER_STRONG_MARGIN
        clear_margin = best_score >= AUTO_CHAPTER_MIN_SCORE and margin >= AUTO_CHAPTER_MARGIN
        if strong_match or clear_margin:
            selected_state = best_state
            decision = "switch_strong_match" if strong_match else "switch_clear_margin"

    return selected_state, {
        "requested_chapter_id": preferred_state.chapter_id,
        "resolved_chapter_id": selected_state.chapter_id,
        "decision": decision,
        "best_score": round(best_score, 3),
        "preferred_score": round(preferred_score, 3),
        "resource_intent": resource_intent,
        "candidates": candidates,
    }


def _direct_chapter_route(
    states: dict[str, ApiState],
    preferred_state: ApiState,
    question: str,
) -> tuple[ApiState | None, dict[str, object]]:
    q_norm = normalize(question)
    if not q_norm:
        return None, {}

    matches: list[dict[str, object]] = []
    for _chapter_id, state in sorted(states.items()):
        matches.extend(state.direct_question_matches.get(q_norm, []))

    if not matches:
        return None, {}

    max_priority = max(float(match["priority"]) for match in matches)
    strongest = [match for match in matches if float(match["priority"]) == max_priority]
    chapters = {str(match["chapter_id"]) for match in strongest}
    if len(chapters) == 1:
        selected_chapter = next(iter(chapters))
        selected_state = states.get(selected_chapter)
        if selected_state:
            return selected_state, _direct_routing_payload(
                preferred_state,
                selected_state,
                "switch_direct_match" if selected_state.chapter_id != preferred_state.chapter_id else "keep_direct_match",
                strongest,
            )

    preferred_matches = [match for match in strongest if match["chapter_id"] == preferred_state.chapter_id]
    if preferred_matches:
        return preferred_state, _direct_routing_payload(
            preferred_state,
            preferred_state,
            "keep_direct_match_tie",
            strongest,
        )

    return None, {}


def _direct_routing_payload(
    preferred_state: ApiState,
    selected_state: ApiState,
    decision: str,
    matches: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "requested_chapter_id": preferred_state.chapter_id,
        "resolved_chapter_id": selected_state.chapter_id,
        "decision": decision,
        "best_score": None,
        "preferred_score": None,
        "resource_intent": 0,
        "direct_matches": matches,
        "candidates": [
            {
                "chapter_id": match["chapter_id"],
                "answer_id": match["answer_id"],
                "canonical_question": match["canonical_question"],
                "match_type": match["match_type"],
                "score": match["priority"],
            }
            for match in matches
        ],
    }


def answer_payload(
    state: ApiState,
    question: str,
    top_k: int = 5,
    use_vectors: bool = False,
    use_db: bool = False,
) -> dict[str, object]:
    resource_hits = search_resources(question, state.resources, state.package.interactive_scripts, limit=5)
    resource_intent = resource_intent_score(question)

    if use_db:
        hits, hybrid_trace = state.db_hybrid().search_with_trace(question, top_k=top_k)
    elif use_vectors:
        hits, hybrid_trace = state.hybrid().search_with_trace(question, top_k=top_k)
    else:
        hits = state.retriever.search(question, top_k=top_k)
        hybrid_trace = None

    operation_match = _operation_question_match(state, question)
    if operation_match and _should_answer_with_operation(operation_match, hits, resource_hits):
        return _operation_match_payload(
            state,
            question,
            operation_match,
            hits,
            resource_hits,
            hybrid_trace,
            use_vectors=use_vectors,
            use_db=use_db,
        )

    direct_hit = _direct_answer_hit(state, question, hits)
    if direct_hit is not None:
        hits = [direct_hit, *[hit for hit in hits if hit.answer_id != direct_hit.answer_id]]

    if _should_answer_with_resource(question, hits, resource_hits, resource_intent):
        top_resource = resource_hits[0]
        resources = [_resource_hit_payload(hit, state) for hit in resource_hits]
        return {
            "question": question,
            "chapter_id": state.chapter_id,
            "answer_id": f"resource:{top_resource['resource'].get('resource_id')}",
            "confidence": "high" if float(top_resource["score"]) >= 110 else "medium",
            "answer_mode": "resource_guidance",
            "answer": _render_resource_answer(top_resource),
            "top_hits": _top_hit_payloads(hits),
            "recommended_resources": resources,
            "trace": {
                "retrieval_order": [
                    "Resources",
                    "Interactive_Scripts",
                    "Answer_Cards",
                    "Knowledge_Points",
                    "Source_Chunks",
                ],
                "selected_answer_id": f"resource:{top_resource['resource'].get('resource_id')}",
                "selected_resource_id": top_resource["resource"].get("resource_id"),
                "selected_score": round(float(top_resource["score"]), 3),
                "selected_reasons": top_resource["reasons"],
                "candidate_count": len(hits),
                "resource_count": len(resources),
                "resource_intent": resource_intent,
                "source_chunks_policy": "evidence_only_no_direct_output",
                "retriever": _retriever_name(use_vectors=use_vectors, use_db=use_db),
                "answer_retrieval_kept_for_reference": True,
                "hybrid": {
                    "keyword_top": hybrid_trace.keyword_top,
                    "vector_top": hybrid_trace.vector_top,
                }
                if hybrid_trace
                else None,
            },
        }
    if not hits:
        return {
            "question": question,
            "chapter_id": state.chapter_id,
            "answer": "教材知识库未找到直接答案。",
            "top_hits": [],
            "recommended_resources": [_resource_hit_payload(hit, state) for hit in resource_hits],
            "trace": {
                "retrieval_order": [
                    "Answer_Cards",
                    "Knowledge_Points",
                    "Concept_Comparison",
                    "Exercises",
                    "Source_Chunks",
                    "Resources",
                ],
                "selected_answer_id": None,
                "fallback": True,
                "retriever": _retriever_name(use_vectors=use_vectors, use_db=use_db),
                "resource_count": len(resource_hits),
            },
        }
    top = hits[0]
    recommended = recommend_resources(top.card, state.resources)
    top_hits = _top_hit_payloads(hits)
    resources = [
        _resource_payload(item, state.script_by_resource.get(str(item.get("resource_id"))))
        for item in recommended
    ]
    operation_answer = _render_operation_answer(state, top.card)
    answer_text = operation_answer["answer"] if operation_answer else render_answer(top.card)
    answer_mode = operation_answer["answer_mode"] if operation_answer else top.card.get("answer_mode")
    return {
        "question": question,
        "chapter_id": state.chapter_id,
        "answer_id": top.answer_id,
        "confidence": confidence(top.score),
        "answer_mode": answer_mode,
        "answer": answer_text,
        "top_hits": top_hits,
        "recommended_resources": resources,
        "trace": {
            "retrieval_order": [
                "Answer_Cards",
                "Knowledge_Points",
                "Concept_Comparison",
                "Exercises",
                "Source_Chunks",
                "Resources",
            ],
            "selected_answer_id": top.answer_id,
            "selected_score": round(top.score, 3),
            "selected_reasons": top.reasons,
            "candidate_count": len(hits),
            "resource_count": len(resources),
            "resource_direct_count": len(resource_hits),
            "operation_answer": operation_answer["trace"] if operation_answer else None,
            "source_chunks_policy": "evidence_only_no_direct_output",
            "retriever": _retriever_name(use_vectors=use_vectors, use_db=use_db),
            "hybrid": {
                "keyword_top": hybrid_trace.keyword_top,
                "vector_top": hybrid_trace.vector_top,
            }
            if hybrid_trace
            else None,
        },
    }


def _direct_answer_hit(state: ApiState, question: str, hits: list[object]) -> RetrievalHit | None:
    q_norm = normalize(question)
    matches = state.direct_question_matches.get(q_norm, [])
    if not matches:
        return None
    best = max(matches, key=lambda match: float(match.get("priority") or 0))
    answer_id = str(best.get("answer_id") or "")
    if not answer_id:
        return None
    existing = next((hit for hit in hits if getattr(hit, "answer_id", "") == answer_id), None)
    if existing is not None:
        score = max(float(getattr(existing, "score", 0.0)), float(best.get("priority") or 0) + 220.0)
        reasons = unique_strings(["direct_question_override", *list(getattr(existing, "reasons", []) or [])])
        return RetrievalHit(answer_id=answer_id, score=score, reasons=reasons, card=getattr(existing, "card"))
    card = next((item for item in state.package.answer_cards if str(item.get("answer_id") or "") == answer_id), None)
    if card is None:
        return None
    return RetrievalHit(
        answer_id=answer_id,
        score=float(best.get("priority") or 0) + 220.0,
        reasons=["direct_question_override", str(best.get("match_type") or "direct_question")],
        card=card,
    )


def unique_strings(values: list[object]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _top_hit_payloads(hits: list[object]) -> list[dict[str, object]]:
    return [
        {
            "answer_id": hit.answer_id,
            "score": round(hit.score, 3),
            "confidence": confidence(hit.score),
            "reasons": hit.reasons,
            "canonical_question": hit.card.get("canonical_question"),
            "answer_mode": hit.card.get("answer_mode"),
        }
        for hit in hits
    ]


def _resource_hit_payload(hit: dict[str, object], state: ApiState) -> dict[str, object]:
    resource = hit["resource"]
    payload = _resource_payload(
        resource,
        state.script_by_resource.get(str(resource.get("resource_id"))),
    )
    payload["match_score"] = round(float(hit["score"]), 3)
    payload["match_reasons"] = hit["reasons"]
    return payload


def _should_answer_with_resource(
    question: str,
    hits: list[object],
    resource_hits: list[dict[str, object]],
    resource_intent: int,
) -> bool:
    if not resource_hits:
        return False
    top_resource_score = float(resource_hits[0]["score"])
    top_answer_score = float(hits[0].score) if hits else 0.0
    top_resource_reasons = set(str(reason) for reason in (resource_hits[0].get("reasons") or []))
    if top_resource_score >= 180 and "exact_trigger" in top_resource_reasons:
        return True
    if resource_intent >= 1 and top_resource_score >= 180 and "title_match" in top_resource_reasons:
        return True
    if "我想看" in question and resource_intent >= 1 and top_resource_score >= 80:
        return True
    if resource_intent >= 1 and top_resource_score >= 120:
        return True
    if resource_intent >= 2 and top_resource_score >= 55:
        return True
    if resource_intent >= 1 and top_resource_score >= 90 and top_answer_score < 110:
        return True
    if not hits and top_resource_score >= 45:
        return True
    return False


def _render_resource_answer(hit: dict[str, object]) -> str:
    resource = hit["resource"]
    script = hit.get("interactive_script")
    title = str(resource.get("title") or resource.get("resource_id") or "学习资源")
    resource_type = str(resource.get("resource_type") or "")
    type_label = {
        "interactive_html": "互动脚本",
        "image": "教材图片",
        "formula": "结构化公式",
        "table": "结构化表格",
    }.get(resource_type, resource_type or "学习资源")
    lines = [
        "这个问题更适合先查看配套学习资源。",
        f"- 推荐资源：**{title}**",
        f"- 资源类型：{type_label}",
    ]
    description = str(resource.get("description") or "")
    if description:
        lines.append(f"- 资源说明：{description}")
    if script:
        theme = script.get("interaction_theme")
        if theme:
            lines.append(f"- 互动主题：{theme}")
        steps = script.get("operation_steps") or []
        if steps:
            lines.append("- 建议操作：")
            lines.extend(f"- {step}" for step in steps[:4])
    elif resource_type == "formula":
        detail = resource.get("formula_detail") or {}
        if isinstance(detail, dict):
            expression = detail.get("expression")
            if expression:
                expression_lines = _formula_expression_lines(expression)
                if len(expression_lines) == 1:
                    lines.append(f"- 公式表达：`{expression_lines[0]}`")
                else:
                    lines.append("- 公式表达：")
                    lines.extend(f"- `{item}`" for item in expression_lines[:8])
            variables = detail.get("variables") or []
            if variables:
                lines.append("- 变量说明：")
                lines.extend(f"- {item}" for item in variables[:4])
            context = detail.get("context_before") or detail.get("context_after")
            if context:
                lines.append(f"- 使用语境：{context}")
    elif resource_type == "table":
        detail = resource.get("table_detail") or {}
        if isinstance(detail, dict):
            label = detail.get("label")
            columns = detail.get("columns") or []
            rows = detail.get("rows") or []
            context = detail.get("context_before")
            if label:
                lines.append(f"- 表格编号：{label}")
            if columns:
                lines.append(f"- 对比维度：{'、'.join(str(item) for item in columns[:6])}")
            if rows:
                lines.append(f"- 表格条目：{len(rows)} 条")
            if context:
                lines.append(f"- 使用语境：{context}")
    elif resource_type == "image":
        keywords = resource.get("keywords") or []
        if keywords:
            lines.append(f"- 看图要点：{'、'.join(str(item) for item in keywords[:6])}")
    related_kps = resource.get("related_kps") or []
    if related_kps:
        lines.append(f"- 关联知识点：{'、'.join(str(item) for item in related_kps[:6])}")
    if resource_type == "formula":
        lines.append("- 可在右侧资源卡片中查看结构化公式详情。")
    elif resource_type == "table":
        lines.append("- 可在右侧资源卡片中查看结构化表格详情。")
    else:
        lines.append("- 可在右侧“推荐资源”卡片中打开文件。")
    return "\n".join(lines)


def _formula_expression_lines(expression: object) -> list[str]:
    text = str(expression or "").strip()
    if not text:
        return []
    parts = [part.strip() for part in text.replace("\r", "\n").replace("&", "\n").splitlines()]
    lines = [part for part in parts if part]
    return lines or [text]


def _truthy(value: object) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


def _retriever_name(use_vectors: bool, use_db: bool) -> str:
    if use_db:
        return "postgres_pgvector_hybrid"
    if use_vectors:
        return "hybrid"
    return "keyword"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local Road KB RAG API")
    parser.add_argument("--package", default=str(DEFAULT_PACKAGE))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--database-url", default=None, help="Enable PostgreSQL/pgvector retrieval for use_db=true")
    parser.add_argument("--version-id", default=DEFAULT_VERSION_ID)
    args = parser.parse_args()

    default_package = str(DEFAULT_PACKAGE)
    package_paths = _package_paths() if args.package == default_package else [Path(args.package)]
    states: dict[str, ApiState] = {}
    for package_path in package_paths:
        package = load_package(package_path)
        chapter_id = _chapter_id(package)
        version_id = args.version_id if args.version_id != DEFAULT_VERSION_ID and len(package_paths) == 1 else _version_id(chapter_id)
        states[chapter_id] = ApiState(package, database_url=args.database_url, version_id=version_id)
    if DEFAULT_CHAPTER_ID not in states:
        first_chapter = next(iter(states))
        states[DEFAULT_CHAPTER_ID] = states[first_chapter]
    server = ThreadingHTTPServer((args.host, args.port), make_handler(states))
    loaded = ", ".join(sorted(set(states) - ({DEFAULT_CHAPTER_ID} if states.get(DEFAULT_CHAPTER_ID) in list(states.values())[1:] else set())))
    print(f"Road KB RAG API listening on http://{args.host}:{args.port} chapters={loaded}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
