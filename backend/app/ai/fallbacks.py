"""Fallback implementations for offline/template agreements and inconclusive evaluations."""

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.ai.schemas import AgreementModelOutput
from app.services.agreements import create_draft_version


def template_agreement(
    project,
    db: Session | None = None,
    custom_terms: list[str] | None = None,
) -> Any:
    """Generate a structured template agreement for a project.

    Does not require an LLM call or external network access.
    If db is provided, saves a new draft agreement version via create_draft_version.
    Otherwise returns the validated content dictionary.
    """
    if project.status != "draft":
        raise ValueError("Agreements can only be generated for draft projects.")

    if not project.title or not project.title.strip():
        raise ValueError("Project title cannot be empty.")

    try:
        total_budget = Decimal(str(project.budget))
    except Exception as exc:
        raise ValueError(f"Invalid project budget: {project.budget}") from exc

    if total_budget <= 0:
        raise ValueError("Project budget must be greater than zero.")

    # Calculate milestone amounts summing exactly to total_budget
    m1 = (total_budget * Decimal("0.30")).quantize(Decimal("0.01"))
    m2 = (total_budget * Decimal("0.40")).quantize(Decimal("0.01"))
    m3 = total_budget - m1 - m2

    if m3 <= 0:
        milestones = [
            {
                "title": f"Milestone 1: {project.title.strip()} Deliverables",
                "description": f"Complete all agreed deliverables for {project.title.strip()}.",
                "amount": float(total_budget),
                "deadline": None,
            }
        ]
        payment_terms = ["100% upon completion and approval of all deliverables."]
    else:
        milestones = [
            {
                "title": "Phase 1: Project Setup and Initial Deliverables",
                "description": (
                    "Initial setup, requirements finalization, "
                    "and foundational deliverables."
                ),
                "amount": float(m1),
                "deadline": None,
            },
            {
                "title": "Phase 2: Core Implementation and Review",
                "description": (
                    "Development of core features, primary deliverables, "
                    "and milestone review."
                ),
                "amount": float(m2),
                "deadline": None,
            },
            {
                "title": "Phase 3: Final Delivery and Handoff",
                "description": (
                    "Final testing, polish, documentation handoff, "
                    "and client acceptance."
                ),
                "amount": float(m3),
                "deadline": None,
            },
        ]
        payment_terms = [
            "30% upon completion and approval of Phase 1",
            "40% upon completion and approval of Phase 2",
            "30% upon final delivery and acceptance",
        ]

    if custom_terms:
        payment_terms.extend(custom_terms)

    content_data = {
        "project_title": project.title.strip(),
        "scope": [
            f"Complete all deliverables and milestones outlined for {project.title.strip()}.",
            "Provide documentation and verification as agreed by both parties.",
            "Perform revisions within the agreed scope.",
        ],
        "deliverables": [
            f"Core project implementation for {project.title.strip()}",
            "Verification and test evidence report",
            "Final project deliverables and handoff documentation",
        ],
        "milestones": milestones,
        "total_budget": float(total_budget),
        "currency": project.currency or "USD",
        "payment_terms": payment_terms,
        "deadline": None,
        "client_responsibilities": [
            "Provide timely feedback and required project specifications.",
            "Review submitted milestone deliverables within agreed timeframe.",
            "Approve accepted milestones to release payment.",
        ],
        "freelancer_responsibilities": [
            "Complete agreed deliverables in accordance with project specifications.",
            "Submit progress updates and test evidence for milestone reviews.",
            "Address revision requests within the agreed project scope.",
        ],
        "incomplete_information": [],
    }

    # Validate against AgreementModelOutput schema
    validated = AgreementModelOutput.model_validate(content_data)
    content = validated.model_dump(mode="json")

    if db is not None:
        return create_draft_version(
            db=db,
            project_id=project.id,
            content=content,
        )

    return content
