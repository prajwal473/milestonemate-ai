import json

from google import genai
from google.genai import types

from app.core.config import settings


class EvaluationServiceError(Exception):
    pass


def evaluate_deliverable(
    milestone_title: str,
    milestone_description: str,
    acceptance_criteria: list[str],
    deliverable_description: str,
) -> dict:

    if not settings.gemini_api_key:
        raise EvaluationServiceError("Gemini API key is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = f"""
You are an impartial freelance project quality evaluator.

Evaluate the submitted deliverable against the milestone requirements.

MILESTONE:
{milestone_title}

MILESTONE DESCRIPTION:
{milestone_description}

ACCEPTANCE CRITERIA:
{json.dumps(acceptance_criteria)}

FREELANCER SUBMISSION:
{deliverable_description}

IMPORTANT RULES:
- Evaluate only evidence actually provided.
- Do not assume that a feature exists just because the freelancer claims it.
- Do not claim to have opened or inspected external URLs.
- Clearly identify criteria that cannot be verified.
- Be objective and fair.
- The client makes the final acceptance decision.
- Your recommendation is advisory only.
"""

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema={
                    "type": "object",
                    "properties": {
                        "score": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100
                        },
                        "summary": {
                            "type": "string"
                        },
                        "criteria_results": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "criterion": {"type": "string"},
                                    "status": {
                                        "type": "string",
                                        "enum": [
                                            "met",
                                            "partially_met",
                                            "not_met",
                                            "unverified"
                                        ]
                                    },
                                    "evidence": {"type": "string"}
                                },
                                "required": [
                                    "criterion",
                                    "status",
                                    "evidence"
                                ]
                            }
                        },
                        "missing_requirements": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "recommendation": {
                            "type": "string",
                            "enum": [
                                "approve",
                                "request_revision",
                                "manual_review"
                            ]
                        }
                    },
                    "required": [
                        "score",
                        "summary",
                        "criteria_results",
                        "missing_requirements",
                        "recommendation"
                    ]
                },
                temperature=0.2,
            ),
        )

        if not response.text:
            raise EvaluationServiceError(
                "Gemini returned an empty evaluation."
            )

        result = json.loads(response.text)

        if not 0 <= result["score"] <= 100:
            raise EvaluationServiceError("Invalid evaluation score.")

        if len(result["criteria_results"]) != len(acceptance_criteria):
            raise EvaluationServiceError(
                "Evaluation did not cover every acceptance criterion."
            )

        return result

    except EvaluationServiceError:
        raise

    except Exception as exc:
        print("\n--- GEMINI EVALUATION ERROR ---")
        print(type(exc).__name__)
        print(str(exc))

        raise EvaluationServiceError(
        	"AI evaluation failed. Please try again."
        ) from exc