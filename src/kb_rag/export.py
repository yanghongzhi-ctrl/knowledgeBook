from __future__ import annotations

from pathlib import Path

from .loader import KnowledgePackage, write_json


TABLE_TO_FILE = {
    "Answer_Cards": "answer_cards.json",
    "Knowledge_Points": "knowledge_points.json",
    "Source_Chunks": "source_chunks.json",
    "QA_Evaluation_Testset": "qa_evaluation_testset.json",
    "Resource_Evaluation_Testset": "resource_evaluation_testset.json",
    "RAG_Config": "rag_config.json",
    "Resources": "resource_index.json",
    "Interactive_Scripts": "interactive_scripts.json",
    "Embedding_Corpus": "embedding_corpus.json",
    "Synonyms_Questions": "synonym_questions.json",
    "Knowledge_Relations": "knowledge_relations.json",
    "Concept_Comparison": "concept_comparisons.json",
    "Exercises": "exercises.json",
    "Operation_Tasks": "operation_tasks.json",
    "Operation_Steps": "operation_steps.json",
    "Command_Cards": "command_cards.json",
    "Software_Objects": "software_objects.json",
    "Parameter_Settings": "parameter_settings.json",
    "Common_Errors": "common_errors.json",
    "Video_Resources": "video_resources.json",
    "Video_Segments": "video_segments.json",
    "Screenshot_Resources": "screenshot_resources.json",
    "Resource_Relations": "resource_relations.json",
    "Question_Routing_Rules": "question_routing_rules.json",
    "Answer_Guardrails": "answer_guardrails.json",
}


def export_processed(package: KnowledgePackage, output_dir: str | Path) -> dict[str, int]:
    output = Path(output_dir)
    counts: dict[str, int] = {}
    for table, filename in TABLE_TO_FILE.items():
        rows = package.data.get(table, [])
        write_json(output / filename, rows)
        counts[filename] = len(rows) if isinstance(rows, list) else 1
    return counts
