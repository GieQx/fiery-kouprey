from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from sdmx_alignment.models.reference import ReferenceStandard
from sdmx_alignment.models.structures import DSDStructure
from sdmx_alignment.parser.sdmx_structure import (
    StructureParseError,
    parse_dataflow_structure_ref,
    parse_structure,
)


class LibraryEntry(BaseModel):
    metadata: ReferenceStandard
    structure: DSDStructure
    xml_bytes: bytes


class UploadedStructureResolution(BaseModel):
    structure: DSDStructure
    structure_xml: bytes
    message: str


def resolve_uploaded_structure(
    file_name: str,
    xml_bytes: bytes,
    library: list[LibraryEntry],
) -> UploadedStructureResolution:
    """Parse an embedded DSD or resolve a Dataflow's exact DSD reference locally."""
    try:
        structure = parse_structure(file_name, xml_bytes)
        return UploadedStructureResolution(
            structure=structure,
            structure_xml=bytes(xml_bytes),
            message="Uploaded DataStructure parsed directly.",
        )
    except StructureParseError as direct_error:
        try:
            reference = parse_dataflow_structure_ref(file_name, xml_bytes)
        except StructureParseError:
            raise direct_error

    match = next(
        (
            entry
            for entry in library
            if entry.structure.agency_id == reference.agency_id
            and entry.structure.id == reference.id
            and entry.structure.version == reference.version
        ),
        None,
    )
    if match is None:
        raise StructureParseError(
            f"{file_name} is a Dataflow that references {reference.key}, "
            "but that DataStructure is not available in the curated reference library"
        )

    structure = match.structure.model_copy(update={"file_name": file_name}, deep=True)
    return UploadedStructureResolution(
        structure=structure,
        structure_xml=bytes(match.xml_bytes),
        message=f"Dataflow reference {reference.key} resolved from the curated reference library.",
    )


def load_reference_library(manifest_path: Path) -> list[LibraryEntry]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    standards = [ReferenceStandard.model_validate(row) for row in payload["standards"]]
    if not 1 <= len(standards) <= 5:
        raise ValueError("Reference library must contain between 1 and 5 standards")

    entries: list[LibraryEntry] = []
    for metadata in standards:
        xml_path = manifest_path.parent / metadata.local_file
        structure = parse_structure(xml_path.name, xml_path.read_bytes())
        if structure.agency_id != metadata.agency_id or structure.id != metadata.artefact_id:
            raise ValueError(f"Manifest identity does not match {xml_path.name}")
        if structure.version != metadata.version:
            raise ValueError(f"Manifest version does not match {xml_path.name}")
        entries.append(LibraryEntry(metadata=metadata, structure=structure, xml_bytes=xml_path.read_bytes()))
    return entries
