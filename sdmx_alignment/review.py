from datetime import datetime, timezone

from sdmx_alignment.models.findings import ComparisonResult, Finding


VALID_STATUSES = {"accepted", "modified", "rejected", "unresolved", "no_action"}
VALID_ACTIONS = {"REUSE", "MAP", "KEEP_LOCAL_EXTENSION", "ADD_MISSING_ELEMENT"}


def default_action(finding: Finding) -> str:
    if finding.alignment_status == "mapping_required":
        return "MAP"
    if finding.alignment_status == "missing_reference":
        return "KEEP_LOCAL_EXTENSION"
    if finding.alignment_status == "missing_local":
        return "ADD_MISSING_ELEMENT"
    return "REUSE"


def apply_review(
    result: ComparisonResult,
    finding_id: str,
    review_status: str,
    recommended_action: str | None,
    review_note: str,
) -> ComparisonResult:
    if review_status not in VALID_STATUSES:
        raise ValueError("Review status must be accepted, modified, rejected, unresolved, or no_action")
    finding = next((item for item in result.findings if item.id == finding_id), None)
    if finding is None:
        raise ValueError(f"Unknown finding: {finding_id}")
    if review_status in {"accepted", "modified"} and recommended_action not in VALID_ACTIONS:
        raise ValueError("Accepted findings require a valid recommended action")
    if review_status == "modified" and not review_note.strip():
        raise ValueError("Modified findings require a reviewer note")
    finding.review_status = review_status
    finding.recommended_action = recommended_action if review_status in {"accepted", "modified"} else None
    finding.review_note = review_note.strip()
    finding.reviewed_at = datetime.now(timezone.utc)
    return result
