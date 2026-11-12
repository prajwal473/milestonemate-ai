import re
from datetime import date
from decimal import Decimal

from app.ai.llm.factory import get_llm_client
from app.ai.prompts.agreement_v1 import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from app.ai.schemas import AgreementModelOutput
from app.services.agreements import create_draft_version


AGREEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "project_title": {"type": "string"},
        "scope": {
            "type": "array",
            "items": {"type": "string"},
        },
        "deliverables": {
            "type": "array",
            "items": {"type": "string"},
        },
        "milestones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "amount": {"type": "number"},
                    "deadline": {"type": ["string", "null"]},
                },
                "required": [
                    "title",
                    "description",
                    "amount",
                    "deadline",
                ],
                "additionalProperties": False,
            },
        },
        "total_budget": {"type": "number"},
        "currency": {"type": "string"},
        "payment_terms": {
            "type": "array",
            "items": {"type": "string"},
        },
        "deadline": {"type": ["string", "null"]},
        "client_responsibilities": {
            "type": "array",
            "items": {"type": "string"},
        },
        "freelancer_responsibilities": {
            "type": "array",
            "items": {"type": "string"},
        },
        "incomplete_information": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "project_title",
        "scope",
        "deliverables",
        "milestones",
        "total_budget",
        "currency",
        "payment_terms",
        "deadline",
        "client_responsibilities",
        "freelancer_responsibilities",
        "incomplete_information",
    ],
    "additionalProperties": False,
}


def validate_payment_schedule(payment_terms):
    """Validate percentage-based payment schedules."""

    percentages = []

    for term in payment_terms:
        matches = re.findall(
            r"(\d+(?:\.\d+)?)\s*%",
            term,
        )

        for value in matches:
            percentages.append(Decimal(value))

    # Skip validation when no percentages are provided.
    if not percentages:
        return

    total_percentage = sum(percentages, Decimal("0"))

    if total_percentage != Decimal("100"):
        raise ValueError(
            f"Payment percentages must total 100%. "
            f"Current total: {total_percentage}%."
        )


def generate_agreement(
    db,
    project,
    answers: dict | None = None,
    extraction: dict | None = None,
):
    if project.status != "draft":
        raise ValueError("Only draft projects can generate agreements.")

    client = get_llm_client()

    prompt = USER_PROMPT_TEMPLATE.format(
        project_title=project.title,
        brief=project.description or "",
        budget=project.budget,
        currency=project.currency,
        answers=answers or {},
        extraction=extraction or {},
        current_date=date.today().isoformat(),
    )

    response = client.generate_json(
        system=SYSTEM_PROMPT,
        user=prompt,
        schema=AGREEMENT_SCHEMA,
        temperature=0.2,
    )

    result = AgreementModelOutput.model_validate(response)

    # Validate project title.
    if not result.project_title.strip():
        raise ValueError("Agreement project title cannot be empty.")

    if result.project_title.strip() != project.title.strip():
        raise ValueError("Agreement project title does not match the project.")

    # Validate required sections.
    required_sections = {
        "scope": result.scope,
        "deliverables": result.deliverables,
        "milestones": result.milestones,
        "payment_terms": result.payment_terms,
        "client_responsibilities": result.client_responsibilities,
        "freelancer_responsibilities": result.freelancer_responsibilities,
    }

    for section_name, section_value in required_sections.items():
        if not section_value:
            raise ValueError(
                f"Agreement section '{section_name}' cannot be empty."
            )

        if any(
            isinstance(item, str) and not item.strip()
            for item in section_value
        ):
            raise ValueError(
                f"Agreement section '{section_name}' contains empty text."
            )

    # Validate payment percentages.
    validate_payment_schedule(result.payment_terms)

    # Validate project budget and currency.
    project_budget = Decimal(str(project.budget))
    agreement_budget = Decimal(str(result.total_budget))

    if agreement_budget != project_budget:
        raise ValueError(
            "Generated agreement budget does not match project budget."
        )

    if result.currency != project.currency:
        raise ValueError(
            "Generated agreement currency does not match project currency."
        )

    # Validate milestones.
    milestone_total = Decimal("0")

    for milestone in result.milestones:
        title = milestone.get("title")
        description = milestone.get("description")
        amount = milestone.get("amount")

        if not isinstance(title, str) or not title.strip():
            raise ValueError("Milestone title cannot be empty.")

        if not isinstance(description, str) or not description.strip():
            raise ValueError("Milestone description cannot be empty.")

        if isinstance(amount, bool) or not isinstance(
            amount, (int, float, Decimal)
        ):
            raise ValueError("Milestone amount must be a number.")

        milestone_amount = Decimal(str(amount))

        if not milestone_amount.is_finite():
            raise ValueError("Milestone amount must be finite.")

        if milestone_amount <= 0:
            raise ValueError("Milestone amount must be greater than zero.")

        milestone_total += milestone_amount

    if milestone_total != project_budget:
        raise ValueError(
            "Milestone amounts do not add up to the project budget."
        )

    # Save only after successful validation.
    content = result.model_dump(mode="json")

    return create_draft_version(
        db=db,
        project_id=project.id,
        content=content,
    )