from datetime import date
import json
from pathlib import Path

import pytest

from sdmx_alignment.models.reference import ReferenceStandard
from sdmx_alignment.reference_library import load_reference_library, resolve_uploaded_structure


def test_reference_standard_requires_version_and_provenance():
    item = ReferenceStandard(
        agency_id="SDMX",
        artefact_id="DSD_LABOUR",
        version="1.0",
        name="Labour reference",
        description="Curated labour statistics reference",
        domain="labour",
        issuer="SDMX",
        artefact_type="structural_reference",
        provenance="SDMX Global Registry",
        source_url="https://registry.sdmx.org/",
        retrieved_at=date(2026, 9, 17),
        fixture_classification="authoritative_reference",
        local_file="labour.xml",
    )

    assert item.identity == "SDMX:DSD_LABOUR(1.0)"


def test_library_loads_manifest_and_exact_dsd_version():
    library = load_reference_library(Path("reference_library/manifest.json"))

    assert len(library) == 4
    assert all(item.metadata.version for item in library)
    assert all(item.structure.version == item.metadata.version for item in library)
    assert all(item.structure.id == item.metadata.artefact_id for item in library)


def test_bop_reference_separates_structure_from_methodology_sources():
    library = load_reference_library(Path("reference_library/manifest.json"))

    bop = next(item.metadata for item in library if item.metadata.artefact_id == "DSD_BOP")

    assert bop.identity == "SDMXWS:DSD_BOP(1.0)"
    assert bop.artefact_type == "structural_reference"
    assert bop.fixture_classification == "workshop_reference"
    assert bop.issuer == "MODS-OECD-ADB Global Workshop 2026"
    assert {source.id for source in bop.related_sources} >= {"BPM7", "BPM6", "SDMX_GLOBAL_REGISTRY"}
    assert all(source.source_url.startswith("https://") for source in bop.related_sources)
    assert {source.artefact_type for source in bop.related_sources} >= {
        "methodological_standard",
        "shared_sdmx_artefact_source",
    }


def test_library_rejects_manifest_identity_mismatch(tmp_path: Path):
    source_xml = Path("samples/reference-demo.xml")
    (tmp_path / "reference.xml").write_bytes(source_xml.read_bytes())
    manifest = {
        "standards": [
            {
                "agency_id": "WRONG",
                "artefact_id": "DSD_REFERENCE_EMP",
                "version": "2.0",
                "name": "Wrong identity",
                "description": "Test mismatch",
                "domain": "labour",
                "issuer": "Test",
                "artefact_type": "structural_reference",
                "provenance": "Test fixture",
                "source_url": None,
                "retrieved_at": "2026-09-17",
                "fixture_classification": "synthetic_benchmark",
                "local_file": "reference.xml",
            }
        ]
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="Manifest identity"):
        load_reference_library(path)


def test_dataflow_upload_resolves_its_referenced_dsd_from_library():
    library = load_reference_library(Path("reference_library/manifest.json"))
    upload = Path("tests/fixtures/DSD_BOP@DF_BOP.xml")

    resolution = resolve_uploaded_structure(upload.name, upload.read_bytes(), library)

    assert resolution.structure.id == "DSD_BOP"
    assert resolution.structure.agency_id == "SDMXWS"
    assert resolution.structure.version == "1.0"
    assert resolution.structure.file_name == upload.name
    assert b"DataStructure" in resolution.structure_xml
    assert "resolved" in resolution.message.lower()
