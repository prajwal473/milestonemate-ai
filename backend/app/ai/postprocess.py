import re

from app.ai.schemas import (
    CriterionStatus,
    EvaluationReportModelOutput,
    EvaluationReport,
    Recommendation,
)


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return re.sub(r"[^\w\s]", "", text).strip()


def verify_evidence(
    report: EvaluationReportModelOutput,
    source_texts: dict[str, str],
    submission_note: str = "",
) -> EvaluationReportModelOutput:

    sources = dict(source_texts)
    sources["submission_note"] = submission_note

    for result in report.criteria_results:
        verified_evidence = []

        for evidence in result.evidence:
            source = sources.get(evidence.file, "")

            verified = (
                bool(evidence.quote.strip())
                and bool(source)
                and normalize_text(evidence.quote)
                in normalize_text(source)
            )

            if verified:
                evidence.verified = True
                verified_evidence.append(evidence)

        result.evidence = verified_evidence

        if (
            result.status == CriterionStatus.MET
            and not result.evidence
        ):
            result.status = CriterionStatus.CANNOT_DETERMINE
            result.gap = "No verifiable evidence found."

    return report


def get_recommendation(
    report: EvaluationReportModelOutput,
    required_ids: set[str],
    has_extracted_text: bool = True,
) -> Recommendation:

    if not has_extracted_text:
        return Recommendation.INCONCLUSIVE

    results = {
        item.criterion_id: item.status
        for item in report.criteria_results
    }

    if required_ids:
        statuses = [
            results.get(item_id, CriterionStatus.CANNOT_DETERMINE)
            for item_id in required_ids
        ]
    else:
        statuses = [
            item.status for item in report.criteria_results
        ]

    if not statuses:
        return Recommendation.INCONCLUSIVE

    if all(s == CriterionStatus.MET for s in statuses):
        return Recommendation.MEETS

    if all(s == CriterionStatus.NOT_MET for s in statuses):
        return Recommendation.DOES_NOT_MEET

    if all(
        s == CriterionStatus.CANNOT_DETERMINE
        for s in statuses
    ):
        return Recommendation.INCONCLUSIVE

    return Recommendation.PARTIALLY_MEETS


def build_evaluation_report(
    report: EvaluationReportModelOutput,
    required_ids: set[str],
    has_extracted_text: bool = True,
) -> EvaluationReport:

    recommendation = get_recommendation(
        report,
        required_ids,
        has_extracted_text,
    )

    met_count = sum(
        item.status == CriterionStatus.MET
        for item in report.criteria_results
    )

    return EvaluationReport(
        **report.model_dump(),
        recommendation=recommendation,
        total_criteria=len(report.criteria_results),
        met_criteria=met_count,
    )