from __future__ import annotations

import re

from lxml import etree

from sdmx_alignment.models.structures import (
    ArtefactRef,
    Code,
    Codelist,
    Component,
    DSDStructure,
    Representation,
)


MAX_XML_BYTES = 10 * 1024 * 1024
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
DATASTRUCTURE_URN = re.compile(
    r"^urn:sdmx:org\.sdmx\.infomodel\.datastructure\.DataStructure="
    r"(?P<agency>[^:]+):(?P<id>[^()]+)\((?P<version>[^()]+)\)$"
)


class StructureParseError(ValueError):
    """Raised when an uploaded file cannot be treated as a safe SDMX DSD."""


def _local_name(element: etree._Element) -> str:
    return etree.QName(element).localname


def _children(element: etree._Element, name: str) -> list[etree._Element]:
    return [child for child in element if _local_name(child) == name]


def _descendants(element: etree._Element, name: str) -> list[etree._Element]:
    return [child for child in element.iter() if _local_name(child) == name]


def _localized(element: etree._Element, name: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for child in _children(element, name):
        text = (child.text or "").strip()
        if text:
            values[child.get(XML_LANG, "und")] = text
    return values


def _ref(element: etree._Element | None) -> ArtefactRef | None:
    if element is None:
        return None
    refs = _descendants(element, "Ref")
    if not refs or not refs[0].get("id"):
        return None
    node = refs[0]
    return ArtefactRef(
        agency_id=node.get("agencyID"),
        id=node.get("id"),
        version=node.get("version") or node.get("maintainableParentVersion"),
        maintainable_parent_id=node.get("maintainableParentID"),
    )


def parse_dataflow_structure_ref(file_name: str, xml_bytes: bytes) -> ArtefactRef:
    """Extract the DSD identity referenced by an SDMX Dataflow message."""
    if len(xml_bytes) > MAX_XML_BYTES:
        raise StructureParseError(f"{file_name} exceeds the 10 MB upload limit")
    lowered = xml_bytes.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise StructureParseError("DTD and entity declarations are not allowed")
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, recover=False)
    try:
        root = etree.fromstring(xml_bytes, parser=parser)
    except (etree.XMLSyntaxError, ValueError) as exc:
        raise StructureParseError(f"{file_name} is not well-formed XML") from exc

    for dataflow in _descendants(root, "Dataflow"):
        for structure in _children(dataflow, "Structure"):
            nested_ref = _ref(structure)
            if nested_ref is not None:
                return nested_ref
            match = DATASTRUCTURE_URN.match((structure.text or "").strip())
            if match:
                return ArtefactRef(
                    agency_id=match.group("agency"),
                    id=match.group("id"),
                    version=match.group("version"),
                )

    raise StructureParseError(f"{file_name} does not contain a resolvable Dataflow structure reference")


def _concept_catalog(root: etree._Element) -> dict[str, tuple[dict[str, str], dict[str, str]]]:
    catalog = {}
    for concept in _descendants(root, "Concept"):
        concept_id = concept.get("id")
        if concept_id:
            catalog[concept_id] = (_localized(concept, "Name"), _localized(concept, "Description"))
    return catalog


def _parse_codelists(root: etree._Element) -> dict[str, Codelist]:
    result: dict[str, Codelist] = {}
    for element in _descendants(root, "Codelist"):
        if not element.get("id"):
            continue
        ref = ArtefactRef(
            agency_id=element.get("agencyID"),
            id=element.get("id"),
            version=element.get("version"),
        )
        codes = []
        for code_element in _children(element, "Code"):
            code_id = code_element.get("id")
            if not code_id:
                continue
            codes.append(
                Code(
                    id=code_id,
                    names=_localized(code_element, "Name"),
                    descriptions=_localized(code_element, "Description"),
                    source_path=f"Codelist[@id='{ref.id}']/Code[@id='{code_id}']",
                )
            )
        result[ref.key] = Codelist(
            ref=ref,
            names=_localized(element, "Name"),
            descriptions=_localized(element, "Description"),
            codes=codes,
            source_path=f"Codelist[@id='{ref.id}']",
        )
    return result


def _representation(component: etree._Element) -> tuple[Representation | None, ArtefactRef | None]:
    local_reps = _children(component, "LocalRepresentation")
    if not local_reps:
        return None, None
    local_rep = local_reps[0]
    enumerations = _children(local_rep, "Enumeration")
    if enumerations:
        codelist_ref = _ref(enumerations[0])
        return Representation(kind="enumeration", enumeration=codelist_ref), codelist_ref
    formats = _children(local_rep, "TextFormat")
    if formats:
        facets = {str(key): str(value) for key, value in formats[0].attrib.items()}
        return Representation(kind="text", facets=facets), None
    return Representation(kind="unspecified"), None


def _component(
    element: etree._Element,
    dsd_id: str,
    component_type: str,
    concepts: dict[str, tuple[dict[str, str], dict[str, str]]],
) -> Component:
    component_id = element.get("id") or ""
    identities = _children(element, "ConceptIdentity")
    concept_ref = _ref(identities[0]) if identities else None
    names, descriptions = concepts.get(concept_ref.id if concept_ref else component_id, ({}, {}))
    representation, codelist_ref = _representation(element)
    annotation_texts = [
        (item.text or "").strip()
        for item in _descendants(element, "AnnotationText")
        if (item.text or "").strip()
    ]
    position = int(element.get("position")) if element.get("position", "").isdigit() else None
    return Component(
        component_type=component_type,
        id=component_id,
        position=position,
        names=names,
        descriptions=descriptions,
        concept_ref=concept_ref,
        codelist_ref=codelist_ref,
        representation=representation,
        annotations=annotation_texts,
        source_path=f"DataStructure[@id='{dsd_id}']/{_local_name(element)}[@id='{component_id}']",
    )


def parse_structure(file_name: str, xml_bytes: bytes) -> DSDStructure:
    if len(xml_bytes) > MAX_XML_BYTES:
        raise StructureParseError(f"{file_name} exceeds the 10 MB upload limit")
    lowered = xml_bytes.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise StructureParseError("DTD and entity declarations are not allowed")
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, recover=False)
    try:
        root = etree.fromstring(xml_bytes, parser=parser)
    except (etree.XMLSyntaxError, ValueError) as exc:
        raise StructureParseError(f"{file_name} is not well-formed XML") from exc

    structures = [item for item in _descendants(root, "DataStructure") if item.get("id")]
    if not structures:
        raise StructureParseError(f"{file_name} does not contain an SDMX DataStructure")
    dsd = structures[0]
    dsd_id = dsd.get("id")
    concepts = _concept_catalog(root)

    dimensions: list[Component] = []
    dimension_lists = _descendants(dsd, "DimensionList")
    if dimension_lists:
        for element in dimension_lists[0]:
            name = _local_name(element)
            if name in {"Dimension", "TimeDimension", "MeasureDimension"}:
                dimensions.append(_component(element, dsd_id, name.lower(), concepts))

    attributes: list[Component] = []
    attribute_lists = _descendants(dsd, "AttributeList")
    if attribute_lists:
        for element in _children(attribute_lists[0], "Attribute"):
            attributes.append(_component(element, dsd_id, "attribute", concepts))

    return DSDStructure(
        agency_id=dsd.get("agencyID"),
        id=dsd_id,
        version=dsd.get("version"),
        names=_localized(dsd, "Name"),
        descriptions=_localized(dsd, "Description"),
        dimensions=dimensions,
        attributes=attributes,
        codelists=_parse_codelists(root),
        file_name=file_name,
    )
