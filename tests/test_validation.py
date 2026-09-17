from pathlib import Path

from sdmx_alignment.alignment_plan import build_alignment_plan, finalize_alignment_plan
from sdmx_alignment.comparator.engine import compare_structures
from sdmx_alignment.parser.sdmx_structure import parse_structure
from sdmx_alignment.review import apply_review
from sdmx_alignment.transformation import transform_dsd
from sdmx_alignment.validation import assess_reference_alignment, validate_revised_dsd


FIXTURES = Path(__file__).parent / "fixtures"


def _generated():
    local_bytes = (FIXTURES / "local-demo.xml").read_bytes()
    reference_bytes = (FIXTURES / "reference-demo.xml").read_bytes()
    local = parse_structure("local.xml", local_bytes)
    reference = parse_structure("reference.xml", reference_bytes)
    comparison = compare_structures(local, reference)
    area = next(item for item in comparison.findings if item.local and item.local.id == "AREA")
    apply_review(comparison, area.id, "accepted", "MAP", "Reviewed mapping.")
    plan = finalize_alignment_plan(build_alignment_plan(comparison), "Reviewer")
    transformed = transform_dsd(local_bytes, reference_bytes, comparison, plan)
    return reference, transformed


def test_generated_dsd_passes_scoped_technical_checks_with_disclaimer():
    _, transformed = _generated()

    result = validate_revised_dsd(transformed.revised_xml, transformed)

    assert result.status == "PASS"
    assert all(check.status == "PASS" for check in result.checks)
    assert "not official SDMX certification" in result.disclaimer


def test_malformed_xml_fails_scoped_technical_checks():
    result = validate_revised_dsd(b"<broken>", None)

    assert result.status == "FAIL"
    assert result.validation_errors


def test_reference_alignment_is_separate_from_technical_validity():
    reference, transformed = _generated()
    revised = parse_structure("revised.xml", transformed.revised_xml)

    assessment = assess_reference_alignment(revised, reference)

    assert assessment.status in {"ALIGNED", "PARTIALLY_ALIGNED", "ISSUES_REMAIN"}
    assert assessment.outstanding_code_mappings >= 0
    assert assessment.unresolved_semantic_issues >= 0
    assert assessment.local_extensions_retained >= 0
    assert "does not guarantee" in assessment.disclaimer

