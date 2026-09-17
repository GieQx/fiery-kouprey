from __future__ import annotations

from lxml import etree

from sdmx_alignment.comparator.engine import compare_structures
from sdmx_alignment.models.structures import DSDStructure
from sdmx_alignment.models.transformation import TransformationResult
from sdmx_alignment.models.validation import (
    ReferenceAlignmentAssessment,
    TechnicalCheck,
    TechnicalValidationResult,
)
from sdmx_alignment.parser.sdmx_structure import parse_structure


TECHNICAL_DISCLAIMER = (
    "MVP SDMX technical checks only; this result is not official SDMX certification or full XSD validation."
)
ALIGNMENT_DISCLAIMER = (
    "Structural and reference alignment does not guarantee complete real-world interoperability."
)


def _check(check_id: str, name: str, passed: bool, success: str, failure: str) -> TechnicalCheck:
    return TechnicalCheck(
        id=check_id,
        name=name,
        status="PASS" if passed else "FAIL",
        message=success if passed else failure,
    )


def validate_revised_dsd(
    revised_xml: bytes,
    transformation: TransformationResult | None,
) -> TechnicalValidationResult:
    checks: list[TechnicalCheck] = []
    errors: list[str] = []
    try:
        parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, recover=False)
        etree.fromstring(revised_xml, parser=parser)
        checks.append(_check("well_formed", "Well-formed XML", True, "XML parsed safely.", ""))
    except Exception:
        message = "Generated artefact is not well-formed XML."
        checks.append(_check("well_formed", "Well-formed XML", False, "", message))
        return TechnicalValidationResult(
            status="FAIL",
            checks=checks,
            validation_errors=[message],
            disclaimer=TECHNICAL_DISCLAIMER,
        )

    try:
        structure = parse_structure("revised-dsd.xml", revised_xml)
        checks.append(_check("reparse", "Application reparse", True, "DataStructure reparsed successfully.", ""))
    except Exception as exc:
        message = f"DataStructure could not be reparsed: {exc}"
        checks.append(_check("reparse", "Application reparse", False, "", message))
        return TechnicalValidationResult(
            status="FAIL", checks=checks, validation_errors=[message], disclaimer=TECHNICAL_DISCLAIMER
        )

    components = structure.dimensions + structure.attributes
    component_ids = [item.id for item in components]
    unique_ids = len(component_ids) == len(set(component_ids))
    checks.append(_check(
        "unique_components",
        "Unique component IDs",
        unique_ids,
        "Component IDs are unique.",
        "Duplicate component IDs were found.",
    ))

    positions = [item.position for item in structure.dimensions]
    valid_positions = all(value is not None and value > 0 for value in positions) and len(positions) == len(set(positions))
    checks.append(_check(
        "dimension_positions",
        "Dimension positions",
        valid_positions,
        "Dimension positions are present and non-duplicated.",
        "Dimension positions are missing or duplicated.",
    ))

    unresolved_refs = sorted({
        item.codelist_ref.id
        for item in components
        if item.codelist_ref and structure.find_codelist(item.codelist_ref) is None
    })
    checks.append(_check(
        "codelist_references",
        "Codelist reference resolution",
        not unresolved_refs,
        "Codelist references resolve inside the generated message.",
        "Unresolved codelist references: " + ", ".join(unresolved_refs),
    ))

    failed_actions = [item for item in transformation.actions if item.status == "failed"] if transformation else []
    checks.append(_check(
        "approved_actions",
        "Approved transformation actions",
        not failed_actions,
        "All approved transformation actions completed or required no XML change.",
        f"{len(failed_actions)} approved transformation action(s) failed.",
    ))

    errors = [item.message for item in checks if item.status == "FAIL"]
    return TechnicalValidationResult(
        status="FAIL" if errors else "PASS",
        checks=checks,
        validation_errors=errors,
        disclaimer=TECHNICAL_DISCLAIMER,
    )


def assess_reference_alignment(
    revised: DSDStructure,
    reference: DSDStructure,
) -> ReferenceAlignmentAssessment:
    comparison = compare_structures(revised, reference)
    blocking = comparison.summary.mapping_required + comparison.summary.missing + comparison.summary.unresolved
    if blocking == 0:
        status = "ALIGNED"
    elif comparison.summary.exact:
        status = "PARTIALLY_ALIGNED"
    else:
        status = "ISSUES_REMAIN"
    return ReferenceAlignmentAssessment(
        status=status,
        summary=comparison.summary,
        outstanding_code_mappings=comparison.summary.mapping_required,
        unresolved_semantic_issues=comparison.summary.unresolved,
        local_extensions_retained=sum(
            item.finding_classification == "local_extension" for item in comparison.findings
        ),
        disclaimer=ALIGNMENT_DISCLAIMER,
    )

