import json
import csv
from io import StringIO
from datetime import datetime, timezone

from sdmx_alignment.models.alignment import AlignmentPlan, AnswerEvaluation
from sdmx_alignment.models.findings import ComparisonResult
from sdmx_alignment.models.recommendations import StandardsRecommendationResult
from sdmx_alignment.models.reference import MethodologyStandard, ReferenceStandard
from sdmx_alignment.models.transformation import TransformationResult
from sdmx_alignment.models.validation import (
    BeforeAfterReport,
    ReferenceAlignmentAssessment,
    TechnicalValidationResult,
)


def export_evidence_package(
    comparison: ComparisonResult,
    alignment_plan: AlignmentPlan,
    evaluation: AnswerEvaluation | None,
) -> bytes:
    package = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "comparison": comparison.model_dump(mode="json"),
        "alignment_plan": alignment_plan.model_dump(mode="json"),
        "answer_evaluation": evaluation.model_dump(mode="json") if evaluation else None,
    }
    return json.dumps(package, indent=2, ensure_ascii=True).encode("utf-8")


def export_audit_package(
    before: ComparisonResult,
    after: ComparisonResult,
    alignment_plan: AlignmentPlan,
    transformation: TransformationResult,
    technical_validation: TechnicalValidationResult,
    reference_alignment: ReferenceAlignmentAssessment,
    before_after: BeforeAfterReport,
    selected_reference: ReferenceStandard,
    selected_methodology: MethodologyStandard | None = None,
    recommendations: dict[str, StandardsRecommendationResult] | None = None,
) -> bytes:
    recommendations = recommendations or {}
    original_comparison = before.model_dump(mode="json")
    for finding, exported_finding in zip(before.findings, original_comparison["findings"]):
        recommendation = recommendations.get(finding.id)
        exported_finding.update(
            recommendation_text=(
                recommendation.recommendation if recommendation else finding.explanation
            ),
            reason=(recommendation.reason if recommendation else finding.explanation),
            recommendation_origin="ai" if recommendation else "deterministic",
            evidence=(
                recommendation.evidence
                if recommendation
                else finding.deterministic_evidence
            ),
            citation_ids=(recommendation.citation_ids if recommendation else []),
            methodology_principle_id=(
                recommendation.principle_id if recommendation else None
            ),
            grounding_status=(
                recommendation.grounding_status if recommendation else "grounded"
            ),
            provider=(recommendation.provider if recommendation else None),
            model=(recommendation.model if recommendation else None),
            reviewer_decision={
                "status": finding.review_status,
                "action": finding.recommended_action,
                "note": finding.review_note,
                "reviewed_at": (
                    finding.reviewed_at.isoformat() if finding.reviewed_at else None
                ),
            },
        )

    grounding_counts = {"grounded": 0, "insufficient": 0, "rejected": 0}
    for recommendation in recommendations.values():
        grounding_counts[recommendation.grounding_status] += 1
    package = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "selected_source_status": {
            "source_id": selected_reference.source_id,
            "retrieval_mode": selected_reference.retrieval_mode,
            "trust_level": selected_reference.trust_level,
        },
        "structural_reference_provenance": {
            "identity": selected_reference.identity,
            "issuer": selected_reference.issuer,
            "provenance": selected_reference.provenance,
            "source_url": selected_reference.source_url,
            "fixture_classification": selected_reference.fixture_classification,
        },
        "selected_reference": selected_reference.model_dump(mode="json"),
        "selected_methodology": (
            selected_methodology.model_dump(mode="json")
            if selected_methodology
            else None
        ),
        "recommendation_summary": {
            "deterministic": len(before.findings) - len(recommendations),
            "ai": len(recommendations),
            **grounding_counts,
        },
        "original_comparison": original_comparison,
        "revised_comparison": after.model_dump(mode="json"),
        "alignment_plan": alignment_plan.model_dump(mode="json"),
        "transformation": transformation.model_dump(mode="json", exclude={"revised_xml"}),
        "technical_validation": technical_validation.model_dump(mode="json"),
        "reference_alignment": reference_alignment.model_dump(mode="json"),
        "before_after": before_after.model_dump(mode="json"),
    }
    return json.dumps(package, indent=2, ensure_ascii=True).encode("utf-8")


def export_change_log_csv(
    alignment_plan: AlignmentPlan,
    transformation: TransformationResult,
) -> bytes:
    action_by_finding = {item.finding_id: item for item in transformation.actions}
    output = StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "finding_id",
            "reviewer_status",
            "approved_action",
            "local_element_id",
            "reference_element_id",
            "reviewer_note",
            "decided_at",
            "transformation_status",
            "transformation_message",
        ],
    )
    writer.writeheader()
    for decision in alignment_plan.decisions:
        action = action_by_finding.get(decision.finding_id)
        writer.writerow({
            "finding_id": decision.finding_id,
            "reviewer_status": decision.reviewer_status,
            "approved_action": decision.recommended_action,
            "local_element_id": decision.local_element_id or "",
            "reference_element_id": decision.reference_element_id or "",
            "reviewer_note": decision.reviewer_note,
            "decided_at": decision.decided_at.isoformat(),
            "transformation_status": action.status if action else "not_executed",
            "transformation_message": action.message if action else "",
        })
    return output.getvalue().encode("utf-8")
