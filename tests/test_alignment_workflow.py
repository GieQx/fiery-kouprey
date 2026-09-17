from pathlib import Path

import pytest

from sdmx_alignment.alignment_plan import build_alignment_plan, finalize_alignment_plan
from sdmx_alignment.comparator.engine import compare_structures
from sdmx_alignment.evaluation import FIXED_QUESTION, create_evaluation
from sdmx_alignment.export import export_evidence_package
from sdmx_alignment.parser.sdmx_structure import parse_structure
from sdmx_alignment.review import apply_review


FIXTURES = Path(__file__).parent / "fixtures"


def _comparison():
    local = parse_structure("local.xml", (FIXTURES / "local-demo.xml").read_bytes())
    reference = parse_structure("reference.xml", (FIXTURES / "reference-demo.xml").read_bytes())
    return compare_structures(local, reference)


def test_reviewed_findings_create_reuse_first_alignment_plan():
    result = _comparison()
    area = next(item for item in result.findings if item.local and item.local.id == "AREA")
    sex = next(item for item in result.findings if item.local and item.local.id == "SEX")
    local_detail = next(item for item in result.findings if item.local and item.local.id == "LOCAL_DETAIL")

    apply_review(result, area.id, "accepted", "REUSE", "Definitions checked.")
    apply_review(result, sex.id, "accepted", "MAP", "Code labels verified.")
    apply_review(result, local_detail.id, "accepted", "KEEP_LOCAL_EXTENSION", "Required locally.")
    plan = build_alignment_plan(result)

    assert plan.status == "draft"
    assert {item.recommended_action for item in plan.decisions} >= {"REUSE", "MAP", "KEEP_LOCAL_EXTENSION"}
    assert area.id not in plan.unresolved_finding_ids
    assert all(item.evidence for item in plan.decisions)

    final = finalize_alignment_plan(plan, "PSA reviewer")
    assert final.status == "final"
    assert final.reviewer == "PSA reviewer"
    assert final.finalized_at is not None


def test_pending_ai_suggestion_cannot_enter_approved_plan():
    result = _comparison()
    area = next(item for item in result.findings if item.local and item.local.id == "AREA")
    area.is_ai_assisted = True
    area.alignment_status = "possible_equivalent"
    area.match_method = "ai_semantic"

    plan = build_alignment_plan(result)

    assert area.id in plan.unresolved_finding_ids
    assert area.id not in {item.finding_id for item in plan.decisions}


def test_evaluation_calculates_measured_delta_only_for_complete_scores():
    baseline = {name: 0 for name in ("reuse", "code_mapping", "gaps", "limitations", "evidence")}
    improved = {name: 2 for name in baseline}

    evaluation = create_evaluation(
        provider="openai",
        model="test-model",
        capture_method="in_app",
        context_hash="same-context",
        baseline_answer="Baseline answer",
        improved_answer="Improved answer",
        baseline_scores=baseline,
        improved_scores=improved,
        critical_errors=[],
        evaluator_note="Reviewed against deterministic findings.",
    )

    assert evaluation.fixed_question == FIXED_QUESTION
    assert evaluation.baseline_total == 0
    assert evaluation.improved_total == 10
    assert evaluation.measured_delta == 10


def test_export_contains_plan_and_evaluation_but_no_credentials():
    result = _comparison()
    plan = build_alignment_plan(result)
    payload = export_evidence_package(result, plan, None)

    assert b'"comparison"' in payload
    assert b'"alignment_plan"' in payload
    assert b"OPENAI_API_KEY" not in payload
    assert b'"api_key"' not in payload


def test_review_rejects_invalid_action_for_status():
    result = _comparison()
    finding = result.findings[0]

    with pytest.raises(ValueError, match="Accepted findings require"):
        apply_review(result, finding.id, "accepted", None, "")


def test_modified_decision_requires_note_and_enters_approved_plan():
    result = _comparison()
    finding = next(item for item in result.findings if item.review_status == "pending")

    with pytest.raises(ValueError, match="reviewer note"):
        apply_review(result, finding.id, "modified", "MAP", "")

    apply_review(result, finding.id, "modified", "MAP", "Map to the reviewed target and retain local label.")
    plan = build_alignment_plan(result)
    decision = next(item for item in plan.decisions if item.finding_id == finding.id)

    assert decision.reviewer_status == "modified"
    assert decision.recommended_action == "MAP"
    assert decision.decided_at is not None


def test_rejected_unresolved_and_no_action_decisions_are_not_executable():
    for status in ("rejected", "unresolved", "no_action"):
        result = _comparison()
        finding = next(item for item in result.findings if item.review_status == "pending")
        apply_review(result, finding.id, status, None, f"Reviewed as {status}.")

        plan = build_alignment_plan(result)

        assert finding.id not in {item.finding_id for item in plan.decisions}
        if status == "no_action":
            assert finding.id not in plan.unresolved_finding_ids
        else:
            assert finding.id in plan.unresolved_finding_ids
