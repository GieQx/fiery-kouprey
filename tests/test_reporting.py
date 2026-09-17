import json
from pathlib import Path

from sdmx_alignment.alignment_plan import build_alignment_plan, finalize_alignment_plan
from sdmx_alignment.comparator.engine import compare_structures
from sdmx_alignment.export import export_audit_package, export_change_log_csv
from sdmx_alignment.parser.sdmx_structure import parse_structure
from sdmx_alignment.reference_library import load_reference_library
from sdmx_alignment.reporting import build_before_after_report
from sdmx_alignment.review import apply_review
from sdmx_alignment.transformation import transform_dsd
from sdmx_alignment.validation import assess_reference_alignment, validate_revised_dsd


FIXTURES = Path(__file__).parent / "fixtures"


def _workflow():
    local_bytes = (FIXTURES / "local-demo.xml").read_bytes()
    reference_bytes = (FIXTURES / "reference-demo.xml").read_bytes()
    local = parse_structure("local.xml", local_bytes)
    reference = parse_structure("reference.xml", reference_bytes)
    before = compare_structures(local, reference)
    area = next(item for item in before.findings if item.local and item.local.id == "AREA")
    apply_review(before, area.id, "accepted", "MAP", "Approved reference-area mapping.")
    plan = finalize_alignment_plan(build_alignment_plan(before), "PSA reviewer")
    transformation = transform_dsd(local_bytes, reference_bytes, before, plan)
    revised = parse_structure("revised.xml", transformation.revised_xml)
    after = compare_structures(revised, reference)
    technical = validate_revised_dsd(transformation.revised_xml, transformation)
    alignment = assess_reference_alignment(revised, reference)
    report = build_before_after_report(before, after, transformation)
    return before, after, plan, transformation, technical, alignment, report


def test_before_after_report_attributes_human_approved_changes():
    _, _, _, transformation, _, _, report = _workflow()

    assert report.applied_changes == sum(item.status == "applied" for item in transformation.actions)
    assert report.before.unresolved >= report.after.unresolved
    assert report.human_approved_changes == report.applied_changes


def test_audit_json_and_csv_include_sources_decisions_and_results():
    before, after, plan, transformation, technical, alignment, report = _workflow()
    reference = load_reference_library(Path("reference_library/manifest.json"))[0].metadata

    payload = json.loads(export_audit_package(
        before, after, plan, transformation, technical, alignment, report, reference
    ))
    csv_payload = export_change_log_csv(plan, transformation).decode("utf-8")

    assert payload["exported_at"]
    assert payload["selected_reference"]["identity"] == reference.identity
    assert "transformation" in payload
    assert payload["technical_validation"]["status"] == "PASS"
    assert "reviewer_status" in csv_payload
    assert "OPENAI_API_KEY" not in json.dumps(payload)
