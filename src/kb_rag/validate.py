from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .loader import KnowledgePackage, REQUIRED_TABLES
from .retrieve import normalize


ANSWER_CARD_REQUIRED = {
    "answer_id",
    "chapter_id",
    "section_id",
    "canonical_question",
    "question_type",
    "answer_mode",
    "answer_points",
    "must_include",
    "avoid_content",
    "status",
}

KNOWLEDGE_POINT_REQUIRED = {
    "kp_id",
    "chapter_id",
    "section_id",
    "title",
    "definition",
    "key_points",
    "status",
}

QA_REQUIRED = {
    "test_id",
    "question",
    "expected_answer_card",
    "expected_answer_points",
    "should_not_include",
    "required_response_mode",
}


@dataclass
class ValidationReport:
    errors: list[str]
    warnings: list[str]
    counts: dict[str, int]

    @property
    def ok(self) -> bool:
        return not self.errors


def _missing(row: dict[str, Any], required: set[str]) -> list[str]:
    return sorted(name for name in required if name not in row or row[name] in (None, ""))


def validate_package(package: KnowledgePackage) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    counts = {
        name: len(value) if isinstance(value, list) else 1
        for name, value in package.data.items()
    }

    missing_tables = sorted(REQUIRED_TABLES - set(package.data))
    for table in missing_tables:
        errors.append(f"Missing required table: {table}")

    for table in sorted(REQUIRED_TABLES & set(package.data)):
        if not isinstance(package.data[table], list):
            errors.append(f"Table {table} must be a list")

    ids: dict[str, set[str]] = {
        "answer_id": set(),
        "kp_id": set(),
        "chunk_id": set(),
        "test_id": set(),
        "resource_id": set(),
        "script_id": set(),
        "embedding_id": set(),
        "resource_test_id": set(),
    }
    qa_question_targets: dict[str, set[str]] = {}
    canonical_question_targets: dict[str, set[str]] = {}

    for idx, row in enumerate(package.answer_cards, 1):
        missing = _missing(row, ANSWER_CARD_REQUIRED)
        if missing:
            errors.append(f"Answer_Cards[{idx}] missing fields: {', '.join(missing)}")
        answer_id = str(row.get("answer_id", ""))
        if answer_id in ids["answer_id"]:
            errors.append(f"Duplicate answer_id: {answer_id}")
        ids["answer_id"].add(answer_id)
        if not row.get("answer_points"):
            errors.append(f"Answer card {answer_id} has empty answer_points")
        if not row.get("must_include"):
            warnings.append(f"Answer card {answer_id} has empty must_include")
        if row.get("status") != "checked":
            warnings.append(f"Answer card {answer_id} status is not checked")
        question_key = normalize(str(row.get("canonical_question", "")))
        if question_key:
            canonical_question_targets.setdefault(question_key, set()).add(answer_id)

    for idx, row in enumerate(package.knowledge_points, 1):
        missing = _missing(row, KNOWLEDGE_POINT_REQUIRED)
        if missing:
            errors.append(f"Knowledge_Points[{idx}] missing fields: {', '.join(missing)}")
        kp_id = str(row.get("kp_id", ""))
        if kp_id in ids["kp_id"]:
            errors.append(f"Duplicate kp_id: {kp_id}")
        ids["kp_id"].add(kp_id)

    for idx, row in enumerate(package.source_chunks, 1):
        chunk_id = str(row.get("chunk_id", ""))
        if not chunk_id:
            errors.append(f"Source_Chunks[{idx}] missing chunk_id")
        if chunk_id in ids["chunk_id"]:
            errors.append(f"Duplicate chunk_id: {chunk_id}")
        ids["chunk_id"].add(chunk_id)
        if row.get("usable_for_answer") != "no_direct_output":
            warnings.append(f"Source chunk {chunk_id} is not marked no_direct_output")

    for idx, row in enumerate(package.qa_cases, 1):
        missing = _missing(row, QA_REQUIRED)
        if missing:
            errors.append(f"QA_Evaluation_Testset[{idx}] missing fields: {', '.join(missing)}")
        test_id = str(row.get("test_id", ""))
        if test_id in ids["test_id"]:
            errors.append(f"Duplicate test_id: {test_id}")
        ids["test_id"].add(test_id)
        expected = row.get("expected_answer_card")
        if expected and expected not in ids["answer_id"]:
            warnings.append(f"QA case {test_id} references unknown answer card: {expected}")
        question_key = normalize(str(row.get("question", "")))
        if question_key and expected:
            qa_question_targets.setdefault(question_key, set()).add(str(expected))

    for idx, row in enumerate(package.resources, 1):
        resource_id = str(row.get("resource_id", ""))
        if not resource_id:
            errors.append(f"Resources[{idx}] missing resource_id")
        if resource_id in ids["resource_id"]:
            errors.append(f"Duplicate resource_id: {resource_id}")
        ids["resource_id"].add(resource_id)
        _validate_resource_path(package, row, resource_id, errors, warnings)

    for idx, row in enumerate(package.interactive_scripts, 1):
        script_id = str(row.get("script_id", ""))
        if not script_id:
            errors.append(f"Interactive_Scripts[{idx}] missing script_id")
        if script_id in ids["script_id"]:
            errors.append(f"Duplicate script_id: {script_id}")
        ids["script_id"].add(script_id)
        resource_id = str(row.get("resource_id", ""))
        if resource_id and resource_id not in ids["resource_id"]:
            errors.append(f"Interactive script {script_id} references unknown resource: {resource_id}")

    source_ids = {
        "answer_card": ids["answer_id"],
        "knowledge_point": ids["kp_id"],
        "resource": ids["resource_id"],
    }
    for idx, row in enumerate(package.data.get("Embedding_Corpus", []), 1):
        embedding_id = str(row.get("embedding_id", ""))
        if not embedding_id:
            errors.append(f"Embedding_Corpus[{idx}] missing embedding_id")
        if embedding_id in ids["embedding_id"]:
            errors.append(f"Duplicate embedding_id: {embedding_id}")
        ids["embedding_id"].add(embedding_id)
        source_type = str(row.get("source_type", ""))
        source_id = str(row.get("source_id", ""))
        embedding_text = str(row.get("embedding_text", "")).strip()
        if not source_type or not source_id:
            errors.append(f"Embedding record {embedding_id} is missing source_type or source_id")
        elif source_type in source_ids and source_id not in source_ids[source_type]:
            errors.append(f"Embedding record {embedding_id} references unknown {source_type}: {source_id}")
        if not embedding_text:
            errors.append(f"Embedding record {embedding_id} has empty embedding_text")
        elif embedding_text == source_id:
            warnings.append(f"Embedding record {embedding_id} uses source_id as embedding_text")

    for idx, row in enumerate(package.resource_eval_cases, 1):
        test_id = str(row.get("test_id", ""))
        if not test_id:
            errors.append(f"Resource_Evaluation_Testset[{idx}] missing test_id")
        if test_id in ids["resource_test_id"]:
            errors.append(f"Duplicate resource evaluation test_id: {test_id}")
        ids["resource_test_id"].add(test_id)
        expected = str(row.get("expected_resource_id", ""))
        if expected and expected not in ids["resource_id"]:
            errors.append(f"Resource evaluation case {test_id} references unknown resource: {expected}")

    for question_key, targets in sorted(qa_question_targets.items()):
        if len(targets) > 1:
            warnings.append(
                "QA testset has ambiguous duplicate question "
                f"'{question_key}' mapped to multiple answer cards: {', '.join(sorted(targets))}"
            )

    for question_key, targets in sorted(canonical_question_targets.items()):
        if len(targets) > 1:
            warnings.append(
                "Answer cards have duplicate canonical question "
                f"'{question_key}': {', '.join(sorted(targets))}"
            )

    return ValidationReport(errors=errors, warnings=warnings, counts=counts)


def _validate_resource_path(
    package: KnowledgePackage,
    row: dict[str, Any],
    resource_id: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    file_path = str(row.get("file_path") or "").strip()
    status = str(row.get("status") or "").strip()
    if not file_path:
        if status == "bound":
            errors.append(f"Bound resource {resource_id} has no file_path")
        return

    path = Path(file_path)
    if path.is_absolute():
        warnings.append(f"Resource {resource_id} uses an absolute file_path: {file_path}")
        check_path = path
    else:
        check_path = _project_root(package.path) / path
    if status == "bound" and not check_path.exists():
        errors.append(f"Bound resource {resource_id} file does not exist: {file_path}")


def _project_root(package_path: Path) -> Path:
    for parent in [package_path.parent, *package_path.parents]:
        if (parent / "src").is_dir() and (parent / "data").is_dir():
            return parent
    return Path.cwd()
