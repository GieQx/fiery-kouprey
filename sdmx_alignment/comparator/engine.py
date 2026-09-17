from __future__ import annotations

from uuid import uuid4

from sdmx_alignment.comparator.lexical import lexical_similarity
from sdmx_alignment.comparator.normalize import normalize_text
from sdmx_alignment.models.findings import (
    CodeMapping,
    ComparisonResult,
    DSDIdentity,
    ElementEvidence,
    Finding,
    SummaryCounts,
)
from sdmx_alignment.models.structures import Component, DSDStructure


PARTIAL_THRESHOLD = 0.82
SEMANTIC_CANDIDATE_THRESHOLD = 0.30


def _ref_text(ref) -> str | None:
    return ref.key if ref else None


def _representation_text(component: Component) -> str | None:
    representation = component.representation
    if representation is None:
        return None
    if representation.kind == "enumeration" and representation.enumeration:
        return f"enumeration:{representation.enumeration.key}"
    if representation.kind == "text":
        facets = ",".join(f"{key}={value}" for key, value in sorted(representation.facets.items()))
        return f"text:{facets}"
    return representation.kind


def _evidence(component: Component) -> ElementEvidence:
    return ElementEvidence(
        id=component.id,
        label=component.label,
        description=component.description,
        concept_ref=_ref_text(component.concept_ref),
        codelist_ref=_ref_text(component.codelist_ref),
        representation=_representation_text(component),
        source_path=component.source_path,
    )


def _code_mappings(local: Component, reference: Component, local_dsd: DSDStructure, ref_dsd: DSDStructure):
    local_list = local_dsd.find_codelist(local.codelist_ref)
    reference_list = ref_dsd.find_codelist(reference.codelist_ref)
    if not local_list or not reference_list:
        return [], False
    reference_by_label = {normalize_text(code.label): code for code in reference_list.codes}
    mappings = []
    for local_code in local_list.codes:
        reference_code = reference_by_label.get(normalize_text(local_code.label))
        if reference_code:
            mappings.append(
                CodeMapping(
                    local_code=local_code.id,
                    local_label=local_code.label,
                    reference_code=reference_code.id,
                    reference_label=reference_code.label,
                )
            )
    local_ids = {code.id for code in local_list.codes}
    reference_ids = {code.id for code in reference_list.codes}
    requires_mapping = local_ids != reference_ids or len(mappings) != len(local_list.codes)
    return mappings, requires_mapping


def _pair_finding(
    index: int,
    local: Component,
    reference: Component,
    method: str,
    local_dsd: DSDStructure,
    reference_dsd: DSDStructure,
    similarity: float | None = None,
) -> Finding:
    mappings, requires_mapping = _code_mappings(local, reference, local_dsd, reference_dsd)
    local_rep = _representation_text(local)
    reference_rep = _representation_text(reference)
    representation_differs = bool(local_rep and reference_rep and local_rep != reference_rep)

    if method == "none":
        status = "unresolved"
        classification = "potential_semantic_correspondence"
        review = "pending"
        explanation = "Deterministic comparison found a plausible lexical candidate but cannot establish semantic equivalence."
    elif requires_mapping:
        status = "mapping_required"
        classification = "mapping_required"
        review = "pending"
        explanation = "The components align, but their codelist codes require an explicit reviewed mapping."
    elif method == "lexical" or representation_differs:
        status = "partial"
        classification = "representation_difference" if representation_differs else "partial_alignment"
        review = "pending"
        explanation = "The components appear aligned, but a lexical or representation difference requires review."
    else:
        status = "exact"
        classification = "exact_alignment"
        review = "not_required"
        explanation = "The components match using deterministic structure evidence."

    evidence = [local.source_path, reference.source_path]
    if representation_differs:
        evidence.append(f"representation:{local_rep} != {reference_rep}")
    return Finding(
        id=f"finding-{index:03d}",
        element_type=local.component_type,
        local=_evidence(local),
        reference=_evidence(reference),
        match_method=method,
        alignment_status=status,
        finding_classification=classification,
        confidence=similarity if method == "lexical" else None,
        explanation=explanation,
        deterministic_evidence=evidence,
        code_mappings=mappings,
        review_status=review,
    )


def _missing_finding(index: int, component: Component, side: str) -> Finding:
    if side == "reference":
        return Finding(
            id=f"finding-{index:03d}",
            element_type=component.component_type,
            local=_evidence(component),
            match_method="none",
            alignment_status="missing_reference",
            finding_classification="local_extension",
            explanation="No corresponding reference element was identified; review whether this is a legitimate local extension.",
            deterministic_evidence=[component.source_path],
        )
    return Finding(
        id=f"finding-{index:03d}",
        element_type=component.component_type,
        reference=_evidence(component),
        match_method="none",
        alignment_status="missing_local",
        finding_classification="reference_only_element",
        explanation="The reference element has no identified local counterpart; review whether it should be added.",
        deterministic_evidence=[component.source_path],
    )


def _compare_group(
    local_items: list[Component],
    reference_items: list[Component],
    local_dsd: DSDStructure,
    reference_dsd: DSDStructure,
    start_index: int,
) -> list[Finding]:
    findings: list[Finding] = []
    available = list(reference_items)
    pending: list[Component] = []

    for local in local_items:
        reference = next((item for item in available if item.id == local.id), None)
        method = "exact_id"
        if reference is None:
            reference = next((item for item in available if normalize_text(item.label) == normalize_text(local.label)), None)
            method = "exact_label"
        if reference is None and local.concept_ref:
            reference = next(
                (item for item in available if item.concept_ref and item.concept_ref.id == local.concept_ref.id),
                None,
            )
            method = "concept_reference"
        if reference is None:
            pending.append(local)
            continue
        available.remove(reference)
        findings.append(_pair_finding(start_index + len(findings), local, reference, method, local_dsd, reference_dsd))

    for local in pending:
        candidates = [(lexical_similarity(local.label, item.label), item) for item in available]
        score, reference = max(candidates, default=(0.0, None), key=lambda item: item[0])
        if reference is not None and score >= SEMANTIC_CANDIDATE_THRESHOLD:
            available.remove(reference)
            method = "lexical" if score >= PARTIAL_THRESHOLD else "none"
            findings.append(
                _pair_finding(
                    start_index + len(findings), local, reference, method, local_dsd, reference_dsd, score
                )
            )
        else:
            findings.append(_missing_finding(start_index + len(findings), local, "reference"))

    for reference in available:
        findings.append(_missing_finding(start_index + len(findings), reference, "local"))
    return findings


def _summary(findings: list[Finding]) -> SummaryCounts:
    return SummaryCounts(
        exact=sum(item.alignment_status == "exact" for item in findings),
        semantic_suggestions=sum(item.is_ai_assisted for item in findings),
        mapping_required=sum(item.alignment_status == "mapping_required" for item in findings),
        missing=sum(item.alignment_status in {"missing_local", "missing_reference"} for item in findings),
        unresolved=sum(item.alignment_status == "unresolved" for item in findings),
    )


def _identity(structure: DSDStructure) -> DSDIdentity:
    return DSDIdentity(
        agency_id=structure.agency_id,
        id=structure.id,
        version=structure.version,
        label=structure.label,
        file_name=structure.file_name,
    )


def compare_structures(local: DSDStructure, reference: DSDStructure) -> ComparisonResult:
    dimension_findings = _compare_group(local.dimensions, reference.dimensions, local, reference, 1)
    attribute_findings = _compare_group(
        local.attributes, reference.attributes, local, reference, len(dimension_findings) + 1
    )
    findings = dimension_findings + attribute_findings
    return ComparisonResult(
        id=str(uuid4()),
        local_dsd=_identity(local),
        reference_dsd=_identity(reference),
        findings=findings,
        summary=_summary(findings),
    )


def refresh_summary(result: ComparisonResult) -> ComparisonResult:
    result.summary = _summary(result.findings)
    return result
