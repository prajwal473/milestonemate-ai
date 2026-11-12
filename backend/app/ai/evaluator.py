import json

from app.ai.llm.factory import get_llm_client
from app.ai.prompts.evaluate_v1 import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from app.ai.schemas import EvaluationReportModelOutput
from app.ai.postprocess import (
    verify_evidence,
    build_evaluation_report,
)


class EvaluationServiceError(Exception):
    """Raised when AI evaluation fails.

    The original exception is preserved and chained via __cause__.
    The error message is kept generic so internal details are not
    exposed to API clients.
    """
    pass


EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "model_confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
        },
        "criteria_results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": [
                            "MET",
                            "PARTIALLY_MET",
                            "NOT_MET",
                            "CANNOT_DETERMINE",
                        ],
                    },
                    "reasoning": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file": {"type": "string"},
                                "quote": {"type": "string"},
                                "verified": {"type": "boolean"},
                            },
                            "required": ["file", "quote"],
                        },
                    },
                    "gap": {"type": ["string", "null"]},
                },
                "required": [
                    "criterion_id",
                    "status",
                    "reasoning",
                    "evidence",
                ],
            },
        },
        "missing_requirements": {
            "type": "array",
            "items": {"type": "string"},
        },
        "unverifiable_items": {
            "type": "array",
            "items": {"type": "string"},
        },
        "risks": {
            "type": "array",
            "items": {"type": "string"},
        },
        "next_steps": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "summary",
        "model_confidence",
        "criteria_results",
        "missing_requirements",
        "unverifiable_items",
        "risks",
        "next_steps",
    ],
}


def evaluate_deliverable(
    milestone_title: str,
    milestone_description: str,
    acceptance_criteria: list,
    deliverable_description: str,
    source_texts: dict | None = None,
    image_paths: list | None = None,
) -> dict:

    try:
        source_texts = source_texts or {}
        image_paths = image_paths or []

        criteria = [
            {
                "criterion_id": f"C{i + 1}",
                "text": str(item),
            }
            for i, item in enumerate(acceptance_criteria)
        ]

        submission = {
            "description": deliverable_description,
            "documents": source_texts,
            "images": [str(path) for path in image_paths],
        }

        user_prompt = USER_PROMPT_TEMPLATE.format(
            milestone=milestone_title + "\n" + milestone_description,
            criteria=json.dumps(criteria),
            submission=json.dumps(submission),
        )

        client = get_llm_client()

        result = client.generate_json(
            SYSTEM_PROMPT,
            user_prompt,
            EVALUATION_SCHEMA,
            temperature=0.2,
            images=image_paths,
        )

        report = EvaluationReportModelOutput.model_validate(result)

        expected_ids = {item["criterion_id"] for item in criteria}
        actual_ids = [
            item.criterion_id for item in report.criteria_results
        ]

        if (
            len(actual_ids) != len(expected_ids)
            or set(actual_ids) != expected_ids
        ):
            raise ValueError("Invalid or incomplete criterion IDs.")

        all_sources = {
            **source_texts,
            "submission_note": deliverable_description,
        }

        report = verify_evidence(
            report,
            source_texts=all_sources,
        )

        has_extracted_text = bool(
            deliverable_description.strip()
            or any(text.strip() for text in source_texts.values())
        )

        final_report = build_evaluation_report(
            report,
            required_ids=expected_ids,
            has_extracted_text=has_extracted_text,
        )

        return final_report.model_dump(mode="json")

    except Exception as exc:
        raise EvaluationServiceError(
            "AI evaluation failed. Please try again."
        ) from exc