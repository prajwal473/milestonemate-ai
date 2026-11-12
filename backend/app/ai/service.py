from app.ai.llm.factory import get_llm_client
from app.ai.prompts.clarify_v1 import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app.ai.schemas import ClarificationResult


CLARIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string"
        },
        "missing_information": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "question": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["LOW", "MEDIUM", "HIGH"]
                    }
                },
                "required": [
                    "id",
                    "question",
                    "why_it_matters",
                    "severity"
                ],
                "additionalProperties": False
            }
        },
        "clarification_questions": {
            "type": "array",
            "items": {"type": "string"}
        },
        "is_ready_for_agreement": {
            "type": "boolean"
        }
    },
    "required": [
        "summary",
        "missing_information",
        "clarification_questions",
        "is_ready_for_agreement"
    ],
    "additionalProperties": False
}


def clarify_project(brief: str, extraction: dict | None = None) -> dict:
    if not brief or not brief.strip():
        raise ValueError("Project brief cannot be empty.")

    client = get_llm_client()

    prompt = USER_PROMPT_TEMPLATE.format(
        brief=brief.strip(),
        extraction=extraction or {}
    )

    response = client.generate_json(
        system=SYSTEM_PROMPT,
        user=prompt,
        schema=CLARIFICATION_SCHEMA,
        temperature=0.2
    )

    result = ClarificationResult.model_validate(response)

    return result.model_dump(mode="json")