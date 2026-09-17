from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

from lxml import etree

from sdmx_alignment.models.alignment import AlignmentPlan
from sdmx_alignment.models.findings import ComparisonResult, Finding
from sdmx_alignment.models.transformation import TransformationActionResult, TransformationResult
from sdmx_alignment.parser.sdmx_structure import parse_structure


COMPONENT_NAMES = {"Dimension", "TimeDimension", "MeasureDimension", "Attribute"}


def _local_name(element: etree._Element) -> str:
    return etree.QName(element).localname


def _parse(xml_bytes: bytes) -> etree._Element:
    if b"<!doctype" in xml_bytes.lower() or b"<!entity" in xml_bytes.lower():
        raise ValueError("DTD and entity declarations are not allowed")
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, recover=False)
    return etree.fromstring(xml_bytes, parser=parser)


def _find(root: etree._Element, names: set[str], element_id: str) -> etree._Element | None:
    return next(
        (item for item in root.iter() if _local_name(item) in names and item.get("id") == element_id),
        None,
    )


def _children(element: etree._Element, names: set[str]) -> list[etree._Element]:
    return [child for child in element if _local_name(child) in names]


def _replace_component_metadata(local: etree._Element, reference: etree._Element) -> None:
    for child in _children(local, {"ConceptIdentity", "LocalRepresentation"}):
        local.remove(child)
    insert_at = 0
    for child in _children(reference, {"ConceptIdentity", "LocalRepresentation"}):
        local.insert(insert_at, deepcopy(child))
        insert_at += 1


def _copy_reference_codelist_if_missing(
    local_root: etree._Element,
    reference_root: etree._Element,
    codelist_id: str,
) -> None:
    if _find(local_root, {"Codelist"}, codelist_id) is not None:
        return
    reference = _find(reference_root, {"Codelist"}, codelist_id)
    if reference is None:
        raise ValueError(f"Reference codelist '{codelist_id}' is unavailable")
    section = next((item for item in local_root.iter() if _local_name(item) == "Codelists"), None)
    if section is None:
        structures = next((item for item in local_root.iter() if _local_name(item) == "Structures"), None)
        if structures is None:
            raise ValueError("Local structure message has no Structures container")
        section = etree.Element(reference.getparent().tag)
        structures.insert(0, section)
    section.append(deepcopy(reference))


def _apply_code_mapping(
    local_root: etree._Element,
    reference_root: etree._Element,
    finding: Finding,
    local_codelist_id: str,
    reference_codelist_id: str,
) -> None:
    local_list = _find(local_root, {"Codelist"}, local_codelist_id)
    reference_list = _find(reference_root, {"Codelist"}, reference_codelist_id)
    if local_list is None or reference_list is None:
        raise ValueError("Reviewed code mapping requires both local and reference codelists")
    existing = _find(local_root, {"Codelist"}, reference_codelist_id)
    if existing is not None and existing is not local_list:
        local_list.getparent().remove(local_list)
        return
    for attribute in ("id", "agencyID", "version"):
        value = reference_list.get(attribute)
        if value:
            local_list.set(attribute, value)
    mapping = {item.local_code: item.reference_code for item in finding.code_mappings}
    for code in local_list:
        if _local_name(code) == "Code" and code.get("id") in mapping:
            code.set("id", mapping[code.get("id")])


def _component_maps(structure):
    return {item.id: item for item in structure.dimensions + structure.attributes}


def _map_component(
    local_root: etree._Element,
    reference_root: etree._Element,
    finding: Finding,
    local_components: dict,
    reference_components: dict,
) -> None:
    if finding.local is None or finding.reference is None:
        raise ValueError("MAP requires local and reference evidence")
    local_element = _find(local_root, COMPONENT_NAMES, finding.local.id)
    reference_element = _find(reference_root, COMPONENT_NAMES, finding.reference.id)
    if local_element is None or reference_element is None:
        raise ValueError("MAP component could not be located in source XML")
    duplicate = _find(local_root, COMPONENT_NAMES, finding.reference.id)
    if duplicate is not None and duplicate is not local_element:
        raise ValueError(f"Target component ID '{finding.reference.id}' already exists")

    local_component = local_components[finding.local.id]
    reference_component = reference_components[finding.reference.id]
    if local_component.codelist_ref and reference_component.codelist_ref:
        _apply_code_mapping(
            local_root,
            reference_root,
            finding,
            local_component.codelist_ref.id,
            reference_component.codelist_ref.id,
        )
    elif reference_component.codelist_ref:
        _copy_reference_codelist_if_missing(local_root, reference_root, reference_component.codelist_ref.id)

    local_element.set("id", finding.reference.id)
    _replace_component_metadata(local_element, reference_element)


def _add_component(
    local_root: etree._Element,
    reference_root: etree._Element,
    finding: Finding,
    reference_components: dict,
) -> None:
    if finding.reference is None:
        raise ValueError("ADD_MISSING_ELEMENT requires reference evidence")
    if _find(local_root, COMPONENT_NAMES, finding.reference.id) is not None:
        raise ValueError(f"Component '{finding.reference.id}' already exists")
    reference_element = _find(reference_root, COMPONENT_NAMES, finding.reference.id)
    if reference_element is None:
        raise ValueError("Reference component could not be located in source XML")
    list_name = "AttributeList" if _local_name(reference_element) == "Attribute" else "DimensionList"
    target = next((item for item in local_root.iter() if _local_name(item) == list_name), None)
    if target is None:
        raise ValueError(f"Local structure has no {list_name}")
    target.append(deepcopy(reference_element))
    component = reference_components[finding.reference.id]
    if component.codelist_ref:
        _copy_reference_codelist_if_missing(local_root, reference_root, component.codelist_ref.id)


def _normalize_dimension_positions(root: etree._Element) -> None:
    dimension_list = next((item for item in root.iter() if _local_name(item) == "DimensionList"), None)
    if dimension_list is None:
        return
    position = 1
    for component in dimension_list:
        if _local_name(component) in {"Dimension", "TimeDimension", "MeasureDimension"}:
            component.set("position", str(position))
            position += 1


def transform_dsd(
    original_xml: bytes,
    reference_xml: bytes,
    comparison: ComparisonResult,
    plan: AlignmentPlan,
) -> TransformationResult:
    if plan.status != "final":
        raise ValueError("Alignment plan must be finalized before transformation")
    local_root = _parse(bytes(original_xml))
    reference_root = _parse(reference_xml)
    local_structure = parse_structure(comparison.local_dsd.file_name, original_xml)
    reference_structure = parse_structure(comparison.reference_dsd.file_name, reference_xml)
    local_components = _component_maps(local_structure)
    reference_components = _component_maps(reference_structure)
    findings = {item.id: item for item in comparison.findings}
    actions: list[TransformationActionResult] = []

    for decision in plan.decisions:
        finding = findings[decision.finding_id]
        try:
            if decision.recommended_action == "MAP":
                _map_component(local_root, reference_root, finding, local_components, reference_components)
                status, message = "applied", "Mapped local component using approved reference evidence."
            elif decision.recommended_action == "ADD_MISSING_ELEMENT":
                _add_component(local_root, reference_root, finding, reference_components)
                status, message = "applied", "Cloned approved missing component from the selected reference."
            else:
                status, message = "no_change", "Approved decision does not require an XML modification."
        except Exception as exc:
            status, message = "failed", str(exc)
        actions.append(
            TransformationActionResult(
                finding_id=decision.finding_id,
                action=decision.recommended_action,
                status=status,
                local_element_id=decision.local_element_id,
                reference_element_id=decision.reference_element_id,
                message=message,
            )
        )

    _normalize_dimension_positions(local_root)
    revised_xml = etree.tostring(local_root, xml_declaration=True, encoding="UTF-8", pretty_print=True)
    parse_structure("revised-dsd.xml", revised_xml)
    return TransformationResult(
        original_sha256=sha256(original_xml).hexdigest(),
        revised_sha256=sha256(revised_xml).hexdigest(),
        revised_xml=revised_xml,
        actions=actions,
    )

