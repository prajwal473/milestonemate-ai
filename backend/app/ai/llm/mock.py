import ast
import json
import re
from typing import Any

from app.ai.llm.base import LLMClient


class MockClient(LLMClient):

    def generate_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        *,
        temperature: float = 0.2,
        max_output_tokens: int = 4096,
        images: list | None = None,
    ) -> dict:

        def generate_value(field):
            if "enum" in field:
                return field["enum"][0]

            field_type = field.get("type")

            if isinstance(field_type, list):
                if "string" in field_type:
                    return "Mock response"
                if "number" in field_type:
                    return 0.0
                return None

            if field_type == "string":
                return "Mock response"
            if field_type == "integer":
                return 1
            if field_type == "number":
                return 0.8
            if field_type == "boolean":
                return True
            if field_type == "array":
                return []
            if field_type == "object":
                return generate_object(field)

            return None

        def generate_object(obj):
            properties = obj.get("properties", {})
            required = obj.get("required", [])

            return {
                key: generate_value(properties[key])
                for key in required
                if key in properties
            }

        result = generate_object(schema)

        # Realistic mock response for clarification requests.
        if "missing_information" in result:
            result = {
                "summary": (
                    "The project brief describes an online shopping "
                    "application, but some important requirements "
                    "need clarification."
                ),
                "missing_information": [
                    {
                        "id": "Q1",
                        "question": "What is the expected project deadline?",
                        "why_it_matters": (
                            "A deadline is needed to plan the project "
                            "timeline and milestones."
                        ),
                        "severity": "HIGH",
                    },
                    {
                        "id": "Q2",
                        "question": (
                            "Which payment gateways should the application support?"
                        ),
                        "why_it_matters": (
                            "The payment gateway affects integration "
                            "requirements and development effort."
                        ),
                        "severity": "MEDIUM",
                    },
                    {
                        "id": "Q3",
                        "question": (
                            "Should the application support Android, "
                            "iOS, or both?"
                        ),
                        "why_it_matters": (
                            "The target platforms determine the "
                            "development approach."
                        ),
                        "severity": "HIGH",
                    },
                ],
                "clarification_questions": [
                    "What is the expected project deadline?",
                    "Which payment gateways should the application support?",
                    "Should the application support Android, iOS, or both?",
                ],
                "is_ready_for_agreement": False,
            }

        # Dynamic mock response for agreement generation.
        if "client_responsibilities" in result:

            title_match = re.search(
                r"PROJECT TITLE:\s*(.*)",
                user,
                re.IGNORECASE,
            )

            budget_match = re.search(
                r"BUDGET:\s*([0-9]+(?:\.[0-9]+)?)",
                user,
                re.IGNORECASE,
            )

            currency_match = re.search(
                r"CURRENCY:\s*([A-Za-z]+)",
                user,
                re.IGNORECASE,
            )

            answers_match = re.search(
                r"CLARIFICATION ANSWERS:\s*(.*?)\s*EXTRACTED INFORMATION:",
                user,
                re.DOTALL,
            )

            project_title = (
                title_match.group(1).strip()
                if title_match else "Mock Project"
            )

            budget = (
                float(budget_match.group(1))
                if budget_match else 50000.0
            )

            currency = (
                currency_match.group(1).strip().upper()
                if currency_match else "INR"
            )

            # Read clarification answers from the prompt.
            answers = {}

            if answers_match:
                try:
                    parsed = ast.literal_eval(
                        answers_match.group(1).strip()
                    )
                    if isinstance(parsed, dict):
                        answers = parsed
                except (ValueError, SyntaxError):
                    answers = {}

            deadline = answers.get("deadline")
            platform = answers.get("platform")
            payment_gateway = answers.get("payment_gateway")

            # Read the custom payment schedule.
            payment_schedule = answers.get("payment_schedule")

            if isinstance(payment_schedule, list):
                payment_schedule = [
                    item.strip()
                    for item in payment_schedule
                    if isinstance(item, str) and item.strip()
                ]
            else:
                payment_schedule = []

            first_amount = round(budget * 0.20, 2)
            second_amount = round(budget * 0.50, 2)
            third_amount = round(
                budget - first_amount - second_amount, 2
            )

            scope = [
                "Understand and implement project requirements",
                "Develop the required application features",
                "Test and deliver the completed project",
            ]

            deliverables = [
                "Completed application",
                "Source code",
                "Tested final delivery",
            ]

            incomplete_information = []

            if not payment_schedule:
                incomplete_information.append(
                    "Payment schedule needs confirmation."
                )

            if platform:
                scope.append(
                    f"Support the following platforms: {platform}"
                )
                deliverables.append(f"Application for {platform}")
            else:
                incomplete_information.append(
                    "Target platforms need confirmation."
                )

            if payment_gateway:
                scope.append(
                    f"Integrate the {payment_gateway} payment gateway."
                )
                deliverables.append(
                    f"{payment_gateway} payment integration"
                )
            else:
                incomplete_information.append(
                    "Payment gateway needs confirmation."
                )

            if not deadline:
                incomplete_information.append(
                    "Project deadline needs confirmation."
                )

            result = {
                "project_title": project_title,
                "scope": scope,
                "deliverables": deliverables,
                "milestones": [
                    {
                        "title": "Planning and Design",
                        "description": "Prepare project design and architecture.",
                        "amount": first_amount,
                        "deadline": None,
                    },
                    {
                        "title": "Development",
                        "description": "Develop the agreed project features.",
                        "amount": second_amount,
                        "deadline": None,
                    },
                    {
                        "title": "Testing and Delivery",
                        "description": "Test and deliver the completed project.",
                        "amount": third_amount,
                        "deadline": deadline,
                    },
                ],
                "total_budget": budget,
                "currency": currency,
                "payment_terms": (
                    payment_schedule
                    if payment_schedule
                    else [
                        "Payment schedule must be confirmed by both parties."
                    ]
                ),
                "deadline": deadline,
                "client_responsibilities": [
                    "Provide project requirements.",
                    "Review deliverables and provide feedback.",
                ],
                "freelancer_responsibilities": [
                    "Develop the agreed project features.",
                    "Test and deliver the project.",
                ],
                "incomplete_information": incomplete_information,
            }

        # Generate one mock result for every evaluation criterion.
        if "criteria_results" in result:
            match = re.search(
                r"ACCEPTANCE CRITERIA:\s*(.*?)\s*SUBMISSION:",
                user,
                re.DOTALL,
            )

            if match:
                criteria = json.loads(match.group(1))
                item_schema = schema["properties"][
                    "criteria_results"
                ]["items"]

                results = []

                for criterion in criteria:
                    item = generate_object(item_schema)
                    item["criterion_id"] = criterion["criterion_id"]
                    results.append(item)

                result["criteria_results"] = results

        return result