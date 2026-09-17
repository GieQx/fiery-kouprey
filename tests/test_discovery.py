from pathlib import Path

from sdmx_alignment.discovery import discover_candidates
from sdmx_alignment.models.structures import Component, DSDStructure
from sdmx_alignment.parser.sdmx_structure import parse_structure
from sdmx_alignment.reference_library import load_reference_library


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


def test_bop_demo_ranks_workshop_bop_reference_first_with_citations():
    local = parse_structure("local-bop-demo.xml", Path("samples/local-bop-demo.xml").read_bytes())

    result = discover_candidates(local, _library())

    best = result.candidates[0]
    assert best.reference.artefact_id == "DSD_BOP"
    assert best.reference.fixture_classification == "workshop_reference"
    assert best.discovery_tier == "strong"
    assert any(item.signal == "domain_metadata_overlap" and item.count for item in best.evidence)
    assert {source.id for source in best.reference.related_sources} >= {"BPM7", "BPM6"}
