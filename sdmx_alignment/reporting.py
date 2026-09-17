from sdmx_alignment.models.findings import ComparisonResult
from sdmx_alignment.models.transformation import TransformationResult
from sdmx_alignment.models.validation import BeforeAfterReport


def build_before_after_report(
    before: ComparisonResult,
    after: ComparisonResult,
    transformation: TransformationResult,
) -> BeforeAfterReport:
    applied = sum(item.status == "applied" for item in transformation.actions)
    return BeforeAfterReport(
        before=before.summary,
        after=after.summary,
        exact_alignment_delta=after.summary.exact - before.summary.exact,
        unresolved_delta=after.summary.unresolved - before.summary.unresolved,
        applied_changes=applied,
        human_approved_changes=applied,
        deterministic_findings=sum(not item.is_ai_assisted for item in before.findings),
        ai_assisted_findings=sum(item.is_ai_assisted for item in before.findings),
    )

