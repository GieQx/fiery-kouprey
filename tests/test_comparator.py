from pathlib import Path

from sdmx_alignment.comparator.engine import compare_structures
from sdmx_alignment.parser.sdmx_structure import parse_structure


FIXTURES = Path(__file__).parent / "fixtures"


def _comparison():
    local = parse_structure("local-demo.xml", (FIXTURES / "local-demo.xml").read_bytes())
    reference = parse_structure("reference-demo.xml", (FIXTURES / "reference-demo.xml").read_bytes())
    return compare_structures(local, reference)


def test_comparator_identifies_exact_and_code_mapping_findings():
    result = _comparison()

    sex = next(item for item in result.findings if item.local and item.local.id == "SEX")
    assert sex.reference.id == "SEX"
    assert sex.match_method == "exact_id"
    assert sex.alignment_status == "mapping_required"
    assert [(item.local_code, item.reference_code) for item in sex.code_mappings] == [
        ("1", "M"), ("2", "F"), ("9", "T")
    ]
    assert sex.is_ai_assisted is False

    freq = next(item for item in result.findings if item.local and item.local.id == "FREQ")
    assert freq.alignment_status == "exact"
    assert freq.review_status == "not_required"


def test_comparator_creates_semantic_candidates_and_missing_findings():
    result = _comparison()

    area = next(item for item in result.findings if item.local and item.local.id == "AREA")
    employment = next(item for item in result.findings if item.local and item.local.id == "EMP_STATUS")
    local_only = next(item for item in result.findings if item.local and item.local.id == "LOCAL_DETAIL")
    reference_only = next(item for item in result.findings if item.reference and item.reference.id == "AGE_GROUP")

    assert (area.reference.id, area.alignment_status, area.match_method) == (
        "REF_AREA", "unresolved", "none"
    )
    assert employment.reference.id == "STATUS_IN_EMPLOYMENT"
    assert employment.alignment_status == "unresolved"
    assert local_only.reference is None
    assert local_only.alignment_status == "missing_reference"
    assert reference_only.local is None
    assert reference_only.alignment_status == "missing_local"


def test_comparator_summary_has_no_overall_score():
    result = _comparison()

    assert result.summary.mapping_required == 1
    assert result.summary.unresolved == 2
    assert result.summary.missing == 2
    assert "score" not in result.summary.model_dump()


def test_findings_use_judge_readable_classifications():
    result = _comparison()

    classifications = {item.finding_classification for item in result.findings}

    assert "exact_alignment" in classifications
    assert "mapping_required" in classifications
    assert "local_extension" in classifications
    assert "reference_only_element" in classifications
