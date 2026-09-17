from pathlib import Path

import pytest

from sdmx_alignment.alignment_plan import build_alignment_plan, finalize_alignment_plan
from sdmx_alignment.comparator.engine import compare_structures
from sdmx_alignment.parser.sdmx_structure import parse_structure
from sdmx_alignment.review import apply_review
from sdmx_alignment.transformation import transform_dsd


FIXTURES = Path(__file__).parent / "fixtures"


def _inputs():
    local_bytes = (FIXTURES / "local-demo.xml").read_bytes()
    reference_bytes = (FIXTURES / "reference-demo.xml").read_bytes()
    local = parse_structure("local.xml", local_bytes)
    reference = parse_structure("reference.xml", reference_bytes)
    return local_bytes, reference_bytes, local, reference, compare_structures(local, reference)


def _final_plan(result):
    return finalize_alignment_plan(build_alignment_plan(result), "PSA reviewer")


def test_transformer_requires_final_plan_and_preserves_original_bytes():
    local_bytes, reference_bytes, _, _, result = _inputs()
    original_snapshot = bytes(local_bytes)

    with pytest.raises(ValueError, match="finalized"):
        transform_dsd(local_bytes, reference_bytes, result, build_alignment_plan(result))

    output = transform_dsd(local_bytes, reference_bytes, result, _final_plan(result))

    assert local_bytes == original_snapshot
    assert output.original_sha256 != ""
    assert output.revised_xml


def test_approved_map_updates_component_identity_and_reviewed_codes():
    local_bytes, reference_bytes, _, _, result = _inputs()
    area = next(item for item in result.findings if item.local and item.local.id == "AREA")
    sex = next(item for item in result.findings if item.local and item.local.id == "SEX")
    apply_review(result, area.id, "accepted", "MAP", "Use the reviewed reference-area concept.")
    apply_review(result, sex.id, "accepted", "MAP", "Code labels checked.")

    output = transform_dsd(local_bytes, reference_bytes, result, _final_plan(result))
    revised = parse_structure("revised.xml", output.revised_xml)

    assert any(item.id == "REF_AREA" for item in revised.dimensions)
    assert not any(item.id == "AREA" for item in revised.dimensions)
    revised_sex = next(item for item in revised.dimensions if item.id == "SEX")
    revised_codes = revised.find_codelist(revised_sex.codelist_ref)
    assert {code.id for code in revised_codes.codes} == {"M", "F", "T"}
    assert {item.status for item in output.actions if item.finding_id in {area.id, sex.id}} == {"applied"}


def test_approved_missing_component_is_cloned_but_rejected_change_is_not_applied():
    local_bytes, reference_bytes, _, _, result = _inputs()
    missing = next(item for item in result.findings if item.local is None and item.reference)
    local_extension = next(item for item in result.findings if item.reference is None and item.local)
    apply_review(result, missing.id, "accepted", "ADD_MISSING_ELEMENT", "Required for selected reference.")
    apply_review(result, local_extension.id, "rejected", None, "Do not transform this finding.")

    output = transform_dsd(local_bytes, reference_bytes, result, _final_plan(result))
    revised = parse_structure("revised.xml", output.revised_xml)

    assert any(item.id == missing.reference.id for item in revised.dimensions + revised.attributes)
    assert any(item.id == local_extension.local.id for item in revised.dimensions + revised.attributes)
    assert local_extension.id not in {item.finding_id for item in output.actions}
