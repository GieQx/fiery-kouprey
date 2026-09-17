from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from sdmx_alignment.models.reference import ReferenceStandard, TrustedSource
from sdmx_alignment.models.structures import DSDStructure
from sdmx_alignment.parser.sdmx_structure import (
    StructureParseError,
    parse_dataflow_structure_ref,
    parse_structure,
)
from sdmx_alignment.reference_sources.catalog import load_source_catalog


DEFAULT_SOURCE_CATALOG = (
    Path(__file__).resolve().parent.parent / "reference_library" / "sources.json"
)
REQUIRED_SOURCE_METADATA_FIELDS = frozenset(
    {"source_id", "retrieval_mode", "trust_level"}
)
SOURCE_PROVENANCE_POLICY = {
    "curated_repository": ("curated", frozenset({"curated"})),
    "registry": ("authoritative", frozenset({"cache", "live"})),
    "institutional_repository": ("authoritative", frozenset({"cache", "live"})),
}


class _ReferenceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    standards: list[ReferenceStandard] = Field(min_length=1, max_length=5)


class LibraryEntry(BaseModel):
    metadata: ReferenceStandard
    structure: DSDStructure
    xml_bytes: bytes


class UploadedStructureResolution(BaseModel):
    structure: DSDStructure
    structure_xml: bytes
    message: str


def _require_explicit_source_metadata(payload: object) -> None:
    if not isinstance(payload, dict) or not isinstance(payload.get("standards"), list):
        return
    for index, standard in enumerate(payload["standards"]):
        if not isinstance(standard, dict):
            continue
        missing = REQUIRED_SOURCE_METADATA_FIELDS - standard.keys()
        if missing:
            fields = ", ".join(sorted(missing))
            raise ValueError(
                f"Reference manifest standard at index {index} must explicitly include: {fields}"
            )


def _validate_source_provenance(
    metadata: ReferenceStandard,
    source: TrustedSource,
) -> None:
    expected_trust, allowed_modes = SOURCE_PROVENANCE_POLICY[source.source_type]
    if (
        source.trust_level != expected_trust
        or metadata.trust_level != expected_trust
        or metadata.retrieval_mode not in allowed_modes
    ):
        raise ValueError(
            f"Reference source policy mismatch for {metadata.source_id}: "
            f"{source.source_type} requires {expected_trust} trust and "
            f"retrieval mode in {sorted(allowed_modes)}"
        )


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


def load_reference_library(
    manifest_path: Path,
    source_catalog_path: Path | None = None,
) -> list[LibraryEntry]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    _require_explicit_source_metadata(payload)
    standards = _ReferenceManifest.model_validate(payload).standards
    trusted_sources = load_source_catalog(source_catalog_path or DEFAULT_SOURCE_CATALOG)
    sources_by_id = {source.id.casefold(): source for source in trusted_sources}

    for metadata in standards:
        source = sources_by_id.get(metadata.source_id.casefold())
        if source is None:
            raise ValueError(
                f"Reference source ID {metadata.source_id} is absent from the trusted source catalog"
            )
        _validate_source_provenance(metadata, source)

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
