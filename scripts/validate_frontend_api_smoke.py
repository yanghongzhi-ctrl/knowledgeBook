from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHAPTERS = ("ch01", "ch02", "ch03", "ch04", "ch05", "ch06", "ch07", "ch08", "ch09", "ch10", "ch11")
OPERATION_CHAPTERS = {"ch06", "ch07", "ch08", "ch09"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the local frontend API contract.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8768")
    parser.add_argument("--raw-dir", default=str(ROOT / "data/raw"))
    parser.add_argument("--no-db", action="store_true", help="Use keyword mode instead of the frontend default db mode.")
    args = parser.parse_args()

    api_base = args.api_base.rstrip("/")
    raw_dir = Path(args.raw_dir)
    failures: list[dict[str, Any]] = []

    try:
        health = get_json(f"{api_base}/health")
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"health request failed: {exc}"}, ensure_ascii=False, indent=2))
        return 1

    expected = set(DEFAULT_CHAPTERS)
    loaded = {str(item.get("chapter_id")) for item in health.get("chapters", [])}
    if not health.get("ok"):
        failures.append({"check": "health_ok", "actual": health})
    if not expected.issubset(loaded):
        failures.append({"check": "loaded_chapters", "expected": sorted(expected), "actual": sorted(loaded)})

    samples = load_samples(raw_dir)
    for chapter_id, sample in sorted(samples.items()):
        payload = {
            "question": sample["question"],
            "chapter_id": chapter_id,
            "auto_chapter": True,
            "use_db": not args.no_db,
        }
        data = post_json(f"{api_base}/ask", payload)
        if data.get("chapter_id") != chapter_id:
            failures.append(
                {
                    "check": "ask_chapter",
                    "chapter_id": chapter_id,
                    "question": sample["question"],
                    "expected": chapter_id,
                    "actual": data.get("chapter_id"),
                }
            )
        if data.get("answer_id") != sample["answer_id"]:
            failures.append(
                {
                    "check": "ask_answer",
                    "chapter_id": chapter_id,
                    "question": sample["question"],
                    "expected": sample["answer_id"],
                    "actual": data.get("answer_id"),
                }
            )
        if not str(data.get("answer") or "").strip():
            failures.append({"check": "ask_answer_text", "chapter_id": chapter_id, "answer_id": data.get("answer_id")})
        if not isinstance(data.get("recommended_resources"), list):
            failures.append({"check": "ask_resources_shape", "chapter_id": chapter_id})
        if not isinstance(data.get("trace"), dict):
            failures.append({"check": "ask_trace_shape", "chapter_id": chapter_id})

        detail = get_json(f"{api_base}/answer-card?{urlencode({'chapter_id': chapter_id, 'id': sample['answer_id']})}")
        if detail.get("answer_card", {}).get("answer_id") != sample["answer_id"]:
            failures.append(
                {
                    "check": "answer_card_detail",
                    "chapter_id": chapter_id,
                    "expected": sample["answer_id"],
                    "actual": detail.get("answer_card", {}).get("answer_id"),
                }
            )

        resources = get_json(f"{api_base}/resources?{urlencode({'chapter_id': chapter_id})}").get("resources", [])
        if not resources:
            failures.append({"check": "resources_nonempty", "chapter_id": chapter_id})
        if not any(item.get("available") for item in resources):
            failures.append({"check": "resources_available", "chapter_id": chapter_id})

        if chapter_id in OPERATION_CHAPTERS:
            operation_payload = get_json(f"{api_base}/operation-tasks?{urlencode({'chapter_id': chapter_id})}")
            tasks = operation_payload.get("tasks", [])
            if not tasks:
                failures.append({"check": "operation_tasks_nonempty", "chapter_id": chapter_id})
            else:
                first_task_id = str(tasks[0].get("task_id") or "")
                detail = get_json(
                    f"{api_base}/operation-task?{urlencode({'chapter_id': chapter_id, 'id': first_task_id})}"
                )
                if detail.get("task", {}).get("task_id") != first_task_id:
                    failures.append(
                        {
                            "check": "operation_task_detail",
                            "chapter_id": chapter_id,
                            "expected": first_task_id,
                            "actual": detail.get("task", {}).get("task_id"),
                        }
                    )
                if not detail.get("steps"):
                    failures.append({"check": "operation_task_steps", "chapter_id": chapter_id, "task_id": first_task_id})
                media_summary = detail.get("media_summary")
                if not isinstance(media_summary, dict):
                    failures.append({"check": "operation_task_media_summary", "chapter_id": chapter_id, "task_id": first_task_id})

    cross = samples["ch01"]
    cross_payload = {
        "question": cross["question"],
        "chapter_id": "ch02",
        "auto_chapter": True,
        "use_db": not args.no_db,
    }
    cross_data = post_json(f"{api_base}/ask", cross_payload)
    if cross_data.get("chapter_id") != "ch01" or cross_data.get("answer_id") != cross["answer_id"]:
        failures.append(
            {
                "check": "cross_chapter_auto_route",
                "expected": {"chapter_id": "ch01", "answer_id": cross["answer_id"]},
                "actual": {"chapter_id": cross_data.get("chapter_id"), "answer_id": cross_data.get("answer_id")},
                "question": cross["question"],
            }
        )

    summary = {
        "ok": not failures,
        "api_base": api_base,
        "retriever": "keyword" if args.no_db else "postgres_pgvector_hybrid",
        "chapters": sorted(samples),
        "checks": len(samples) * 5 + len(OPERATION_CHAPTERS) * 4 + 3,
        "failures": failures,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if failures else 0


def load_samples(raw_dir: Path) -> dict[str, dict[str, str]]:
    samples: dict[str, dict[str, str]] = {}
    for chapter_id in DEFAULT_CHAPTERS:
        package_path = next((raw_dir / chapter_id).glob("*.json"), None)
        if not package_path:
            raise SystemExit(f"No package JSON found for {chapter_id} under {raw_dir}")
        data = json.loads(package_path.read_text(encoding="utf-8"))
        card = next((item for item in data.get("Answer_Cards", []) if item.get("canonical_question")), None)
        if not card:
            raise SystemExit(f"No answer card sample found in {package_path}")
        samples[chapter_id] = {
            "question": str(card["canonical_question"]),
            "answer_id": str(card["answer_id"]),
        }
    return samples


def get_json(url: str) -> dict[str, Any]:
    return request_json(Request(url, method="GET"))


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    return request_json(request)


def request_json(request: Request) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {message}") from exc
    except URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc
    return json.loads(raw)


if __name__ == "__main__":
    raise SystemExit(main())
