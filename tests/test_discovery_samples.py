from pathlib import Path

import pytest

from sdmx_alignment.discovery import discover_candidates
from sdmx_alignment.parser.sdmx_structure import parse_structure
from sdmx_alignment.reference_library import load_reference_library


SAMPLE_DIR = Path("samples/discovery-tests")
LIBRARY = Path("reference_library/manifest.json")


@pytest.mark.parametrize(
    ("file_name", "expected_reference", "expected_tier"),
    [
        ("local-employment.xml", "DSD_REFERENCE_EMP", "strong"),
        ("local-tourism.xml", "DSD_REFERENCE_TOURISM", "strong"),
        ("local-prices.xml", "DSD_REFERENCE_CPI", "strong"),
    ],
)
def test_domain_samples_rank_the_expected_reference_first(file_name, expected_reference, expected_tier):
    path = SAMPLE_DIR / file_name
    local = parse_structure(path.name, path.read_bytes())

    result = discover_candidates(local, load_reference_library(LIBRARY))

    assert result.candidates[0].reference.artefact_id == expected_reference
    assert result.candidates[0].discovery_tier == expected_tier


def test_mixed_domain_sample_returns_multiple_plausible_candidates():
    path = SAMPLE_DIR / "local-mixed-domain.xml"
    local = parse_structure(path.name, path.read_bytes())

    result = discover_candidates(local, load_reference_library(LIBRARY))

    assert 3 <= len(result.candidates) <= 5
    assert {candidate.discovery_tier for candidate in result.candidates} == {"plausible"}


def test_no_match_sample_does_not_force_a_candidate():
    path = SAMPLE_DIR / "local-no-match.xml"
    local = parse_structure(path.name, path.read_bytes())

    result = discover_candidates(local, load_reference_library(LIBRARY))

    assert result.candidates == []
    assert result.message == "No suitable reference standard identified."
