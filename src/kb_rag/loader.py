from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_TABLES = {
    "Chapter_Structure",
    "Source_Chunks",
    "Knowledge_Points",
    "Answer_Cards",
    "Concept_Comparison",
    "Synonyms_Questions",
    "Knowledge_Relations",
    "Resources",
    "Interactive_Scripts",
    "Exercises",
    "QA_Evaluation_Testset",
    "RAG_Config",
    "Embedding_Corpus",
    "Prompt_Templates",
    "Quality_Checklist",
}


@dataclass(frozen=True)
class KnowledgePackage:
    path: Path
    data: dict[str, Any]

    @property
    def answer_cards(self) -> list[dict[str, Any]]:
        return list(self.data.get("Answer_Cards", []))

    @property
    def knowledge_points(self) -> list[dict[str, Any]]:
        return list(self.data.get("Knowledge_Points", []))

    @property
    def source_chunks(self) -> list[dict[str, Any]]:
        return list(self.data.get("Source_Chunks", []))

    @property
    def qa_cases(self) -> list[dict[str, Any]]:
        return list(self.data.get("QA_Evaluation_Testset", []))

    @property
    def resource_eval_cases(self) -> list[dict[str, Any]]:
        return list(self.data.get("Resource_Evaluation_Testset", []))

    @property
    def rag_config(self) -> list[dict[str, Any]]:
        return list(self.data.get("RAG_Config", []))

    @property
    def synonyms(self) -> list[dict[str, Any]]:
        return list(self.data.get("Synonyms_Questions", []))

    @property
    def resources(self) -> list[dict[str, Any]]:
        return list(self.data.get("Resources", []))

    @property
    def interactive_scripts(self) -> list[dict[str, Any]]:
        return list(self.data.get("Interactive_Scripts", []))

    @property
    def operation_tasks(self) -> list[dict[str, Any]]:
        return list(self.data.get("Operation_Tasks", []))

    @property
    def operation_steps(self) -> list[dict[str, Any]]:
        return list(self.data.get("Operation_Steps", []))

    @property
    def common_errors(self) -> list[dict[str, Any]]:
        return list(self.data.get("Common_Errors", []))

    @property
    def video_segments(self) -> list[dict[str, Any]]:
        return list(self.data.get("Video_Segments", []))

    @property
    def screenshot_resources(self) -> list[dict[str, Any]]:
        return list(self.data.get("Screenshot_Resources", []))


def load_package(path: str | Path) -> KnowledgePackage:
    package_path = Path(path)
    with package_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Knowledge package root must be a JSON object: {package_path}")
    return KnowledgePackage(package_path, data)


def write_json(path: str | Path, value: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def table_counts(package: KnowledgePackage) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, value in package.data.items():
        counts[name] = len(value) if isinstance(value, list) else 1
    return counts
