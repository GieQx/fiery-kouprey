from pathlib import Path

from sdmx_alignment.discovery import discover_candidates
from sdmx_alignment.models.reference import ReferenceStandard
from sdmx_alignment.models.structures import Component, DSDStructure
from sdmx_alignment.parser.sdmx_structure import parse_structure
from sdmx_alignment.reference_library import LibraryEntry, load_reference_library


def _library():
    return load_reference_library(Path("reference_library/manifest.json"))


def test_discovery_explains_and_orders_candidate_signals():
    local = parse_structure("local-demo.xml", Path("samples/local-demo.xml").read_bytes())

    result = discover_candidates(local, _library())

    assert 3 <= len(result.candidates) <= 5
    best = result.candidates[0]
    assert best.reference.artefact_id == "DSD_REFERENCE_EMP"
    assert best.discovery_tier == "strong"
    assert any(item.signal == "exact_component_id" and item.count >= 3 for item in best.evidence)
    assert any(item.signal == "code_label_overlap" and item.count >= 3 for item in best.evidence)
    assert "exact component" in best.explanation


def test_discovery_can_return_no_suitable_reference():
    unrelated = DSDStructure(
        agency_id="LOCAL",
        id="DSD_UNRELATED",
        version="1.0",
        names={"en": "Marine chemistry measurements"},
        dimensions=[
            Component(
                component_type="dimension",
                id="SALINITY_METHOD",
                names={"en": "Salinity measurement method"},
                source_path="/SALINITY_METHOD",
            )
        ],
        file_name="unrelated.xml",
    )

    result = discover_candidates(unrelated, _library())

    assert result.candidates == []
    assert result.message == "No suitable reference standard identified."


def test_bop_demo_ranks_global_registry_bop_reference_first_with_citations():
    local = parse_structure("local-bop-demo.xml", Path("samples/local-bop-demo.xml").read_bytes())

    result = discover_candidates(local, _library())

    best = result.candidates[0]
    assert best.reference.identity == "IMF:BOP(2.6.0)"
    assert best.reference.source_id == "SDMX_GLOBAL_REGISTRY"
    assert best.reference.fixture_classification == "authoritative_reference"
    assert best.discovery_tier == "strong"
    assert any(item.signal == "domain_metadata_overlap" and item.count for item in best.evidence)
    assert {source.id for source in best.reference.related_sources} >= {"BPM7", "BPM6"}
    assert all(
        candidate.reference.fixture_classification != "workshop_reference"
        for candidate in result.candidates
    )


def test_discovery_uses_source_trust_only_after_relevance_and_evidence():
    local = _structure("LOCAL", "LOCAL_DSD", ["FREQ", "REF_AREA", "MEASURE"])
    equivalent = _structure("TEST", "EQUIVALENT", ["FREQ", "REF_AREA"])
    curated = _entry(
        equivalent,
        agency_id="ZZZ_CURATED",
        artefact_id="CURATED_EQUIVALENT",
        source_id="CURATED_LOCAL",
        retrieval_mode="curated",
        trust_level="curated",
        fixture_classification="synthetic_benchmark",
    )
    authoritative = _entry(
        equivalent,
        agency_id="AAA_REGISTRY",
        artefact_id="REGISTRY_EQUIVALENT",
        source_id="SDMX_GLOBAL_REGISTRY",
        retrieval_mode="cache",
        trust_level="authoritative",
        fixture_classification="authoritative_reference",
    )

    tied = discover_candidates(local, [curated, authoritative])

    assert [candidate.reference.source_id for candidate in tied.candidates] == [
        "SDMX_GLOBAL_REGISTRY",
        "CURATED_LOCAL",
    ]

    more_relevant_curated = _entry(
        _structure("TEST", "MORE_RELEVANT", ["FREQ", "REF_AREA", "MEASURE"]),
        agency_id="ZZZ_CURATED",
        artefact_id="CURATED_MORE_RELEVANT",
        source_id="CURATED_LOCAL",
        retrieval_mode="curated",
        trust_level="curated",
        fixture_classification="synthetic_benchmark",
    )
    relevance_wins = discover_candidates(local, [authoritative, more_relevant_curated])

    assert relevance_wins.candidates[0].reference.source_id == "CURATED_LOCAL"


def test_global_registry_wins_exact_authoritative_source_tie_before_identity():
    local = _structure("LOCAL", "LOCAL_DSD", ["FREQ", "REF_AREA"])
    equivalent = _structure("TEST", "EQUIVALENT", ["FREQ", "REF_AREA"])
    registry = _entry(
        equivalent,
        agency_id="AAA_REGISTRY",
        artefact_id="REGISTRY_EQUIVALENT",
        source_id="SDMX_GLOBAL_REGISTRY",
        retrieval_mode="cache",
        trust_level="authoritative",
        fixture_classification="authoritative_reference",
    )
    imf = _entry(
        equivalent,
        agency_id="ZZZ_IMF",
        artefact_id="IMF_EQUIVALENT",
        source_id="IMF",
        retrieval_mode="cache",
        trust_level="authoritative",
        fixture_classification="authoritative_reference",
    )

    result = discover_candidates(local, [imf, registry])

    assert [candidate.reference.source_id for candidate in result.candidates] == [
        "SDMX_GLOBAL_REGISTRY",
        "IMF",
    ]


def _structure(agency_id: str, artefact_id: str, component_ids: list[str]) -> DSDStructure:
    return DSDStructure(
        agency_id=agency_id,
        id=artefact_id,
        version="1.0",
        names={"en": "Neutral dataset"},
        dimensions=[
            Component(
                component_type="dimension",
                id=component_id,
                names={"en": component_id},
                source_path=f"/{component_id}",
            )
            for component_id in component_ids
        ],
        file_name=f"{artefact_id}.xml",
    )


def _entry(
    structure: DSDStructure,
    *,
    agency_id: str,
    artefact_id: str,
    source_id: str,
    retrieval_mode: str,
    trust_level: str,
    fixture_classification: str,
) -> LibraryEntry:
    entry_structure = structure.model_copy(
        update={
            "agency_id": agency_id,
            "id": artefact_id,
            "file_name": f"{artefact_id}.xml",
        }
    )
    metadata = ReferenceStandard.model_validate(
        {
            "agency_id": agency_id,
            "artefact_id": artefact_id,
            "version": "1.0",
            "name": "Equivalent reference",
            "description": "Controlled discovery ranking fixture",
            "domain": "neutral",
            "issuer": "Test issuer",
            "artefact_type": "structural_reference",
            "provenance": "Test fixture",
            "source_url": None,
            "retrieved_at": "2026-09-17",
            "fixture_classification": fixture_classification,
            "local_file": entry_structure.file_name,
            "source_id": source_id,
            "retrieval_mode": retrieval_mode,
            "trust_level": trust_level,
        }
    )
    return LibraryEntry(metadata=metadata, structure=entry_structure, xml_bytes=b"<test />")
