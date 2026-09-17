from datetime import date
import json
from pathlib import Path

import pytest

from sdmx_alignment.models.reference import ReferenceStandard, SourceCitation
from sdmx_alignment.reference_library import load_reference_library, resolve_uploaded_structure
from sdmx_alignment.reference_sources.catalog import load_source_catalog


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
    manifest_path = Path("reference_library/manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    library = load_reference_library(manifest_path)
    sources = {
        source.id: source
        for source in load_source_catalog(Path("reference_library/sources.json"))
    }

    assert len(library) == 4
    assert all(
        {"source_id", "retrieval_mode", "trust_level"} <= standard.keys()
        for standard in manifest["standards"]
    )
    assert all(item.metadata.version for item in library)
    assert all(item.structure.version == item.metadata.version for item in library)
    assert all(item.structure.id == item.metadata.artefact_id for item in library)
    assert all(item.metadata.source_id in sources for item in library)
    assert all(
        item.metadata.trust_level == sources[item.metadata.source_id].trust_level
        for item in library
    )
    assert all(
        item.metadata.retrieval_mode
        == ("curated" if sources[item.metadata.source_id].source_type == "curated_repository" else "cache")
        for item in library
    )


@pytest.mark.parametrize(
    ("fixture_classification", "field", "value"),
    [
        ("synthetic_benchmark", "retrieval_mode", "live"),
        ("workshop_reference", "retrieval_mode", "live"),
        ("synthetic_benchmark", "trust_level", "authoritative"),
        ("workshop_reference", "trust_level", "authoritative"),
    ],
)
def test_non_authoritative_fixtures_cannot_launder_provenance(
    fixture_classification: str,
    field: str,
    value: str,
):
    payload = _reference_payload(
        fixture_classification=fixture_classification,
        **{field: value},
    )

    with pytest.raises(ValueError, match="cannot claim"):
        ReferenceStandard.model_validate(payload)


def test_curated_local_cannot_claim_authoritative_trust():
    payload = _reference_payload(
        fixture_classification="authoritative_reference",
        trust_level="authoritative",
    )

    with pytest.raises(ValueError, match="CURATED_LOCAL"):
        ReferenceStandard.model_validate(payload)


def test_reference_models_reject_unknown_fields_and_invalid_urls():
    with pytest.raises(ValueError):
        ReferenceStandard.model_validate(_reference_payload(unexpected="value"))

    citation = {
        "id": "CITATION",
        "name": "Citation",
        "issuer": "Issuer",
        "version": "1",
        "artefact_type": "methodological_standard",
        "description": "Description",
        "source_url": "file:///tmp/source.pdf",
        "unexpected": "value",
    }
    with pytest.raises(ValueError):
        SourceCitation.model_validate(citation)


def test_reference_models_reject_blank_text_fields():
    with pytest.raises(ValueError):
        ReferenceStandard.model_validate(_reference_payload(description=" "))

    citation = {
        "id": " ",
        "name": "Citation",
        "issuer": "Issuer",
        "version": "1",
        "artefact_type": "methodological_standard",
        "description": "Description",
        "source_url": "https://example.com/source",
    }
    with pytest.raises(ValueError):
        SourceCitation.model_validate(citation)


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
    bpm7 = next(source for source in bop.related_sources if source.id == "BPM7")
    assert bpm7.name == (
        "Integrated Balance of Payments and International Investment Position Manual, "
        "Seventh Edition"
    )
    assert bpm7.source_url == (
        "https://data.imf.org/-/media/iData/External-Storage/Documents/"
        "5B776E0E552E4881AF24042EAE7D049B/en/1-BPM7-White-Cover.pdf"
    )


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
                "source_id": "CURATED_LOCAL",
                "retrieval_mode": "curated",
                "trust_level": "curated",
                "local_file": "reference.xml",
            }
        ]
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="Manifest identity"):
        load_reference_library(path)


def test_library_rejects_source_id_absent_from_trusted_catalog(tmp_path: Path):
    manifest_path = _write_reference_manifest(tmp_path, source_id="UNKNOWN_SOURCE")
    catalog_path = _write_source_catalog(tmp_path, source_id="CURATED_LOCAL")

    with pytest.raises(ValueError, match="UNKNOWN_SOURCE"):
        load_reference_library(manifest_path, source_catalog_path=catalog_path)


@pytest.mark.parametrize("missing_field", ["source_id", "retrieval_mode", "trust_level"])
def test_library_requires_explicit_manifest_provenance(
    tmp_path: Path,
    missing_field: str,
):
    payload = _reference_payload()
    payload.pop(missing_field)
    manifest_path = _write_reference_manifest(tmp_path, payload=payload)
    catalog_path = _write_source_catalog(tmp_path, source_id="CURATED_LOCAL")

    with pytest.raises(ValueError, match=missing_field):
        load_reference_library(manifest_path, source_catalog_path=catalog_path)


@pytest.mark.parametrize(
    ("source_id", "source_type", "source_trust", "retrieval_mode", "entry_trust"),
    [
        ("CURATED_LOCAL", "curated_repository", "curated", "cache", "curated"),
        ("SDMX_GLOBAL_REGISTRY", "registry", "authoritative", "curated", "authoritative"),
    ],
)
def test_library_rejects_retrieval_mode_inconsistent_with_source_policy(
    tmp_path: Path,
    source_id: str,
    source_type: str,
    source_trust: str,
    retrieval_mode: str,
    entry_trust: str,
):
    manifest_path = _write_reference_manifest(
        tmp_path,
        payload=_reference_payload(
            source_id=source_id,
            retrieval_mode=retrieval_mode,
            trust_level=entry_trust,
            fixture_classification="authoritative_reference"
            if entry_trust == "authoritative"
            else "synthetic_benchmark",
        ),
    )
    catalog_path = _write_source_catalog(
        tmp_path,
        source_id=source_id,
        source_type=source_type,
        trust_level=source_trust,
    )

    with pytest.raises(ValueError, match="source policy"):
        load_reference_library(manifest_path, source_catalog_path=catalog_path)


@pytest.mark.parametrize("retrieval_mode", ["cache", "live"])
def test_library_accepts_authoritative_source_retrieval_modes(
    tmp_path: Path,
    retrieval_mode: str,
):
    manifest_path = _write_reference_manifest(
        tmp_path,
        payload=_reference_payload(
            source_id="SDMX_GLOBAL_REGISTRY",
            retrieval_mode=retrieval_mode,
            trust_level="authoritative",
            fixture_classification="authoritative_reference",
        ),
    )
    catalog_path = _write_source_catalog(
        tmp_path,
        source_id="SDMX_GLOBAL_REGISTRY",
        source_type="registry",
        trust_level="authoritative",
    )

    library = load_reference_library(manifest_path, source_catalog_path=catalog_path)

    assert library[0].metadata.retrieval_mode == retrieval_mode


def test_library_accepts_source_id_registered_by_future_adapter(tmp_path: Path):
    manifest_path = _write_reference_manifest(tmp_path, source_id="FUTURE_ADAPTER")
    catalog_path = _write_source_catalog(tmp_path, source_id="FUTURE_ADAPTER")

    library = load_reference_library(manifest_path, source_catalog_path=catalog_path)

    assert library[0].metadata.source_id == "FUTURE_ADAPTER"


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


def _reference_payload(**updates) -> dict:
    payload = {
        "agency_id": "SDMX",
        "artefact_id": "DSD_REFERENCE_EMP",
        "version": "2.0",
        "name": "Employment reference",
        "description": "Curated employment reference",
        "domain": "labour",
        "issuer": "Test issuer",
        "artefact_type": "structural_reference",
        "provenance": "Test fixture",
        "source_url": None,
        "retrieved_at": "2026-09-17",
        "fixture_classification": "synthetic_benchmark",
        "local_file": "reference.xml",
        "source_id": "CURATED_LOCAL",
        "retrieval_mode": "curated",
        "trust_level": "curated",
    }
    payload.update(updates)
    return payload


def _write_reference_manifest(
    tmp_path: Path,
    source_id: str | None = None,
    payload: dict | None = None,
) -> Path:
    source_xml = Path("samples/reference-demo.xml")
    (tmp_path / "reference.xml").write_bytes(source_xml.read_bytes())
    path = tmp_path / "manifest.json"
    standard = payload or _reference_payload(source_id=source_id or "CURATED_LOCAL")
    path.write_text(
        json.dumps({"standards": [standard]}),
        encoding="utf-8",
    )
    return path


def _write_source_catalog(
    tmp_path: Path,
    source_id: str,
    source_type: str = "curated_repository",
    trust_level: str = "curated",
) -> Path:
    path = tmp_path / "sources.json"
    path.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": source_id,
                        "name": "Test source",
                        "source_type": source_type,
                        "base_url": "https://example.com/reference-library/",
                        "trust_level": trust_level,
                        "is_default": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return path
