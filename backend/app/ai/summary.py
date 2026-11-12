def generate_project_summary(project):
    milestones = project.milestones

    completed = sum(
        milestone.status in ("approved", "completed")
        for milestone in milestones
    )

    pending = len(milestones) - completed

    milestone_details = []
    risks = []

    for milestone in milestones:
        deliverables = []

        for deliverable in milestone.deliverables:
            latest_evaluation = (
                deliverable.evaluations[-1]
                if deliverable.evaluations
                else None
            )

            deliverables.append({
                "description": deliverable.description,
                "status": deliverable.status,
                "recommendation": (
                    latest_evaluation.recommendation
                    if latest_evaluation else None
                ),
            })

            if deliverable.status in (
                "revision_requested",
                "rejected",
            ):
                risks.append(
                    f"Deliverable needs attention: {deliverable.description}"
                )

        milestone_details.append({
            "title": milestone.title,
            "status": milestone.status,
            "amount": str(milestone.amount),
            "deliverables": deliverables,
        })

    return {
        "project_id": project.id,
        "project_title": project.title,
        "description": project.description,
        "budget": str(project.budget),
        "currency": project.currency,
        "status": project.status,
        "milestone_summary": {
            "total": len(milestones),
            "completed": completed,
            "pending": pending,
        },
        "milestones": milestone_details,
        "risks": risks,
        "summary": (
            f"{project.title} has {len(milestones)} milestones. "
            f"{completed} are completed and {pending} are pending."
        ),
    }