from datetime import datetime, timezone

from sdmx_alignment.models.alignment import AlignmentDecision, AlignmentPlan
from sdmx_alignment.models.findings import ComparisonResult
from sdmx_alignment.review import default_action


def build_alignment_plan(result: ComparisonResult) -> AlignmentPlan:
    decisions = []
    unresolved = []
    for finding in result.findings:
        deterministic_exact = finding.review_status == "not_required" and finding.alignment_status == "exact"
        accepted = finding.review_status in {"accepted", "modified"} and finding.recommended_action is not None
        if deterministic_exact or accepted:
            decisions.append(
                AlignmentDecision(
                    finding_id=finding.id,
                    local_element_id=finding.local.id if finding.local else None,
                    reference_element_id=finding.reference.id if finding.reference else None,
                    recommended_action=finding.recommended_action or default_action(finding),
                    relation=finding.relation,
                    confidence=finding.confidence,
                    evidence=finding.deterministic_evidence,
                    reviewer_status=finding.review_status,
                    reviewer_note=finding.review_note,
                    decided_at=finding.reviewed_at or datetime.now(timezone.utc),
                )
            )
        elif finding.review_status == "no_action":
            continue
        else:
            unresolved.append(finding.id)
    return AlignmentPlan(
        local_dsd=result.local_dsd,
        reference_dsd=result.reference_dsd,
        decisions=decisions,
        unresolved_finding_ids=unresolved,
    )


def finalize_alignment_plan(plan: AlignmentPlan, reviewer: str) -> AlignmentPlan:
    reviewer = reviewer.strip()
    if not reviewer:
        raise ValueError("Reviewer name or initials are required")
    plan.status = "final"
    plan.reviewer = reviewer
    plan.finalized_at = datetime.now(timezone.utc)
    return plan
