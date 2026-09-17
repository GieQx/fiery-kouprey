import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from sdmx_alignment.models.reference import ReferenceStandard
from sdmx_alignment.parser.sdmx_structure import parse_structure
from sdmx_alignment.reference_library import LibraryEntry
from sdmx_alignment.reference_sources import (
    GlobalRegistrySource,
    SourceRefreshResult,
    merge_refresh,
)
from sdmx_alignment.reference_sources.catalog import (
    load_methodology_catalog,
    load_source_catalog,
)


SOURCE_IDS = {
    "SDMX_GLOBAL_REGISTRY",
    "IMF",
    "OECD",
    "EUROSTAT",
    "CURATED_LOCAL",
}
OFFICIAL_SOURCE_URLS = {
    "SDMX_GLOBAL_REGISTRY": "https://registry.sdmx.org/sdmx/v2/",
    "IMF": "https://sdmxcentral.imf.org/ws/public/sdmxapi/rest/",
    "OECD": "https://sdmx.oecd.org/public/rest/",
    "EUROSTAT": "https://webgate.ec.europa.eu/fusionregistry/sdmx/v2/",
}
BPM7_URL = (
    "https://data.imf.org/-/media/iData/External-Storage/Documents/"
    "5B776E0E552E4881AF24042EAE7D049B/en/1-BPM7-White-Cover.pdf"
)
BPM6_URL = (
    "https://www.imf.org/en/publications/manuals-guides/issues/2016/12/31/"
    "balance-of-payments-manual-sixth-edition-22588"
)


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _source(**updates) -> dict:
    source = {
        "id": "SOURCE",
        "name": "Source",
        "source_type": "registry",
        "base_url": "https://example.com/sdmx/",
        "trust_level": "authoritative",
        "is_default": True,
    }
    source.update(updates)
    return source


def _methodology(**updates) -> dict:
    source_url = "https://example.com/methodology"
    methodology = {
        "id": "METHOD",
        "name": "Methodology",
        "issuer": "Test issuer",
        "version": "1",
        "description": "Contextual methodology",
        "source_url": source_url,
        "domains": ["test"],
        "principles": [
            {
                "id": "METHOD_PRINCIPLE",
                "text": "Contextual guidance for this test.",
                "source_url": source_url,
            }
        ],
    }
    methodology.update(updates)
    return methodology


def test_source_catalog_has_one_global_registry_default_and_expected_sources():
    sources = load_source_catalog(Path("reference_library/sources.json"))

    defaults = [source for source in sources if source.is_default]
    assert len(defaults) == 1
    assert defaults[0].id == "SDMX_GLOBAL_REGISTRY"
    assert sources[0].id == "SDMX_GLOBAL_REGISTRY"
    assert {source.id for source in sources} == SOURCE_IDS
    sources_by_id = {source.id: source for source in sources}
    assert {
        source_id: sources_by_id[source_id].base_url
        for source_id in OFFICIAL_SOURCE_URLS
    } == OFFICIAL_SOURCE_URLS
    assert sources_by_id["CURATED_LOCAL"].source_type == "curated_repository"
    assert sources_by_id["CURATED_LOCAL"].trust_level == "curated"


@pytest.mark.parametrize(("field", "value"), [("id", " "), ("name", "\t")])
def test_source_catalog_rejects_blank_identity_fields(tmp_path: Path, field: str, value: str):
    path = _write_json(
        tmp_path / "sources.json",
        {"sources": [_source(**{field: value})]},
    )

    with pytest.raises(ValueError):
        load_source_catalog(path)


@pytest.mark.parametrize("base_url", ["not-a-url", "ftp://example.com/sdmx/"])
def test_source_catalog_rejects_non_http_urls(tmp_path: Path, base_url: str):
    path = _write_json(
        tmp_path / "sources.json",
        {"sources": [_source(base_url=base_url)]},
    )

    with pytest.raises(ValueError):
        load_source_catalog(path)


def test_source_catalog_rejects_string_boolean(tmp_path: Path):
    path = _write_json(
        tmp_path / "sources.json",
        {"sources": [_source(is_default="true")]},
    )

    with pytest.raises(ValueError):
        load_source_catalog(path)


def test_source_catalog_rejects_unknown_fields(tmp_path: Path):
    path = _write_json(
        tmp_path / "sources.json",
        {"sources": [_source(unexpected="value")]},
    )

    with pytest.raises(ValueError):
        load_source_catalog(path)


def test_source_catalog_rejects_empty_catalog(tmp_path: Path):
    path = _write_json(tmp_path / "sources.json", {"sources": []})

    with pytest.raises(ValueError):
        load_source_catalog(path)


def test_source_catalog_rejects_zero_defaults(tmp_path: Path):
    path = _write_json(
        tmp_path / "sources.json",
        {"sources": [_source(is_default=False)]},
    )

    with pytest.raises(ValueError, match="exactly one default source"):
        load_source_catalog(path)


def test_source_catalog_rejects_duplicate_ids(tmp_path: Path):
    first = _source(id="Duplicate")
    second = _source(id=" duplicate ", is_default=False)
    path = _write_json(tmp_path / "sources.json", {"sources": [first, second]})

    with pytest.raises(ValueError, match="Duplicate source ID"):
        load_source_catalog(path)


def test_source_catalog_rejects_multiple_defaults(tmp_path: Path):
    path = _write_json(
        tmp_path / "sources.json",
        {
            "sources": [
                {
                    "id": "FIRST",
                    "name": "First source",
                    "source_type": "registry",
                    "base_url": "https://first.example/sdmx/v2/",
                    "trust_level": "authoritative",
                    "is_default": True,
                },
                {
                    "id": "SECOND",
                    "name": "Second source",
                    "source_type": "institutional_repository",
                    "base_url": "https://second.example/",
                    "trust_level": "authoritative",
                    "is_default": True,
                },
            ]
        },
    )

    with pytest.raises(ValueError, match="exactly one default source"):
        load_source_catalog(path)


def test_methodology_catalog_has_bounded_canonical_bpm_principles():
    methodologies = load_methodology_catalog(Path("reference_library/methodologies.json"))

    bpm7 = next(item for item in methodologies if item.id == "BPM7")
    bpm6 = next(item for item in methodologies if item.id == "BPM6")

    assert bpm7.issuer == "International Monetary Fund"
    assert bpm6.issuer == "International Monetary Fund"
    assert bpm7.name == (
        "Integrated Balance of Payments and International Investment Position Manual, "
        "Seventh Edition"
    )
    assert bpm7.source_url == BPM7_URL
    assert bpm6.source_url == BPM6_URL
    assert bpm6.published_at == date(2010, 1, 11)
    assert 1 <= len(bpm7.principles) <= 5
    assert 1 <= len(bpm6.principles) <= 5
    assert all(principle.source_url == bpm7.source_url for principle in bpm7.principles)
    assert all(principle.source_url == bpm6.source_url for principle in bpm6.principles)


@pytest.mark.parametrize(
    ("field", "value"),
    [("id", " "), ("name", "\t"), ("description", "\n"), ("domains", [" "])],
)
def test_methodology_catalog_rejects_blank_fields(
    tmp_path: Path,
    field: str,
    value: str | list[str],
):
    path = _write_json(
        tmp_path / "methodologies.json",
        {"methodologies": [_methodology(**{field: value})]},
    )

    with pytest.raises(ValueError):
        load_methodology_catalog(path)


@pytest.mark.parametrize("source_url", ["not-a-url", "file:///tmp/manual.pdf"])
def test_methodology_catalog_rejects_non_http_urls(tmp_path: Path, source_url: str):
    methodology = _methodology(source_url=source_url)
    methodology["principles"][0]["source_url"] = source_url
    path = _write_json(
        tmp_path / "methodologies.json",
        {"methodologies": [methodology]},
    )

    with pytest.raises(ValueError):
        load_methodology_catalog(path)


@pytest.mark.parametrize("target", ["methodology", "principle"])
def test_methodology_catalog_rejects_unknown_fields(tmp_path: Path, target: str):
    methodology = _methodology()
    if target == "methodology":
        methodology["unexpected"] = "value"
    else:
        methodology["principles"][0]["unexpected"] = "value"
    path = _write_json(
        tmp_path / "methodologies.json",
        {"methodologies": [methodology]},
    )

    with pytest.raises(ValueError):
        load_methodology_catalog(path)


def test_methodology_catalog_rejects_empty_catalog(tmp_path: Path):
    path = _write_json(tmp_path / "methodologies.json", {"methodologies": []})

    with pytest.raises(ValueError):
        load_methodology_catalog(path)


def test_methodology_catalog_rejects_empty_principles(tmp_path: Path):
    path = _write_json(
        tmp_path / "methodologies.json",
        {"methodologies": [_methodology(principles=[])]},
    )

    with pytest.raises(ValueError):
        load_methodology_catalog(path)


def test_methodology_catalog_rejects_principle_source_mismatch(tmp_path: Path):
    methodology = _methodology()
    methodology["principles"][0]["source_url"] = "https://example.com/other"
    path = _write_json(
        tmp_path / "methodologies.json",
        {"methodologies": [methodology]},
    )

    with pytest.raises(ValueError, match="canonical source URL"):
        load_methodology_catalog(path)


def test_methodology_catalog_rejects_duplicate_methodology_ids(tmp_path: Path):
    first = _methodology(id="Duplicate")
    second = _methodology(id=" duplicate ")
    second["principles"][0]["id"] = "SECOND_PRINCIPLE"
    path = _write_json(
        tmp_path / "methodologies.json",
        {"methodologies": [first, second]},
    )

    with pytest.raises(ValueError, match="Duplicate methodology ID"):
        load_methodology_catalog(path)


def test_methodology_catalog_rejects_duplicate_principle_ids(tmp_path: Path):
    source_url = "https://example.com/methodology"
    first = {
        "id": "Duplicate_Principle",
        "text": "Contextual guidance for this test.",
        "source_url": source_url,
    }
    second = {**first, "id": " duplicate_principle "}
    path = _write_json(
        tmp_path / "methodologies.json",
        {
            "methodologies": [
                {
                    "id": "METHOD",
                    "name": "Test methodology",
                    "issuer": "Test issuer",
                    "version": "1",
                    "description": "Test methodology",
                    "source_url": source_url,
                    "domains": ["test"],
                    "principles": [first, second],
                }
            ]
        },
    )

    with pytest.raises(ValueError, match="Duplicate principle ID"):
        load_methodology_catalog(path)


def _dsd_xml(
    *,
    agency_id: str = "SDMX",
    artefact_id: str = "DSD_TEST",
    version: str = "1.0",
    name: str = "Test structure",
    description: str = "A bounded registry test structure.",
) -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<mes:Structure xmlns:mes="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"
  xmlns:str="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure"
  xmlns:com="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common">
  <mes:Structures>
    <str:DataStructures>
      <str:DataStructure agencyID="{agency_id}" id="{artefact_id}" version="{version}">
        <com:Name xml:lang="en">{name}</com:Name>
        <com:Description xml:lang="en">{description}</com:Description>
        <str:DataStructureComponents>
          <str:DimensionList id="DimensionDescriptor" />
        </str:DataStructureComponents>
      </str:DataStructure>
    </str:DataStructures>
  </mes:Structures>
</mes:Structure>""".encode()


def _registry_source(
    handler,
    *,
    max_response_bytes: int = 5 * 1024 * 1024,
) -> GlobalRegistrySource:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return GlobalRegistrySource(client=client, max_response_bytes=max_response_bytes)


def _library_entry(
    agency_id: str,
    artefact_id: str,
    version: str,
    *,
    retrieval_mode: str = "cache",
    name: str = "Cached structure",
) -> LibraryEntry:
    xml_bytes = _dsd_xml(
        agency_id=agency_id,
        artefact_id=artefact_id,
        version=version,
        name=name,
    )
    structure = parse_structure(f"{artefact_id}.xml", xml_bytes)
    metadata = ReferenceStandard(
        agency_id=agency_id,
        artefact_id=artefact_id,
        version=version,
        name=name,
        description="Cached test structure.",
        domain="Test domain",
        issuer=agency_id,
        artefact_type="structural_reference",
        provenance="Test fixture.",
        source_url=(
            f"https://registry.sdmx.org/sdmx/v2/structure/datastructure/"
            f"{agency_id}/{artefact_id}/{version}?references=all"
        ),
        retrieved_at=date(2026, 9, 17),
        fixture_classification="authoritative_reference",
        local_file=f"{artefact_id}.xml",
        source_id="SDMX_GLOBAL_REGISTRY",
        retrieval_mode=retrieval_mode,
        trust_level="authoritative",
    )
    return LibraryEntry(metadata=metadata, structure=structure, xml_bytes=xml_bytes)


def test_global_registry_fetches_exact_structure_and_normalizes_metadata():
    requests: list[httpx.Request] = []
    xml_bytes = _dsd_xml()

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=xml_bytes, request=request)

    source = _registry_source(handler)

    result = source.fetch_datastructure("SDMX", "DSD_TEST", "1.0")

    assert result.status == "success"
    assert result.source_id == "SDMX_GLOBAL_REGISTRY"
    assert result.message == "Refreshed SDMX:DSD_TEST(1.0) from the SDMX Global Registry."
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == (
        "https://registry.sdmx.org/sdmx/v2/structure/datastructure/"
        "SDMX/DSD_TEST/1.0?references=all"
    )
    assert request.headers["accept"] == "application/vnd.sdmx.structure+xml;version=2.1"
    assert "all/all/all" not in str(request.url).lower()

    entry = result.entries[0]
    assert entry.metadata.identity == "SDMX:DSD_TEST(1.0)"
    assert entry.metadata.source_id == "SDMX_GLOBAL_REGISTRY"
    assert entry.metadata.retrieval_mode == "live"
    assert entry.metadata.trust_level == "authoritative"
    assert entry.metadata.fixture_classification == "authoritative_reference"
    assert entry.metadata.source_url == str(request.url)
    assert entry.metadata.issuer == "SDMX"
    assert entry.metadata.name == "Test structure"
    assert entry.metadata.description == "A bounded registry test structure."
    assert entry.metadata.domain
    assert entry.xml_bytes == xml_bytes


def test_global_registry_latest_accepts_returned_version():
    xml_bytes = _dsd_xml(version="4.2")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/SDMX/DSD_TEST/latest")
        return httpx.Response(200, content=xml_bytes, request=request)

    result = _registry_source(handler).fetch_datastructure(
        "SDMX", "DSD_TEST", "latest"
    )

    assert result.status == "success"
    assert result.entries[0].metadata.identity == "SDMX:DSD_TEST(4.2)"


@pytest.mark.parametrize(
    ("agency_id", "artefact_id"),
    [("", "DSD_TEST"), ("  ", "DSD_TEST"), ("SDMX", ""), ("SDMX", "\t")],
)
def test_global_registry_rejects_blank_identity_input(
    agency_id: str,
    artefact_id: str,
):
    source = _registry_source(
        lambda request: httpx.Response(500, request=request)
    )

    with pytest.raises(ValueError, match="nonblank"):
        source.fetch_datastructure(agency_id, artefact_id, "1.0")


@pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ReadTimeout])
def test_global_registry_network_failures_return_safe_fallback(error_type):
    def handler(request: httpx.Request) -> httpx.Response:
        raise error_type("internal transport detail", request=request)

    result = _registry_source(handler).fetch_datastructure(
        "SDMX", "DSD_TEST", "1.0"
    )

    assert result.status == "fallback"
    assert result.entries == []
    assert result.message == "The SDMX Global Registry could not be reached; using cached references."
    assert "internal transport detail" not in result.message


def test_global_registry_non_success_response_returns_safe_fallback():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="private upstream detail", request=request)

    result = _registry_source(handler).fetch_datastructure(
        "SDMX", "DSD_TEST", "1.0"
    )

    assert result.status == "fallback"
    assert result.entries == []
    assert result.message == "The SDMX Global Registry rejected the structure request; using cached references."
    assert "private upstream detail" not in result.message


def test_global_registry_oversized_response_returns_safe_fallback():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 65, request=request)

    result = _registry_source(handler, max_response_bytes=64).fetch_datastructure(
        "SDMX", "DSD_TEST", "1.0"
    )

    assert result.status == "fallback"
    assert result.entries == []
    assert result.message == "The registry response exceeded the safe size limit; using cached references."


@pytest.mark.parametrize(
    ("xml_bytes", "expected_message"),
    [
        (b"<not-closed>", "The registry returned invalid SDMX structure XML; using cached references."),
        (b"<root />", "The registry returned invalid SDMX structure XML; using cached references."),
    ],
)
def test_global_registry_invalid_xml_returns_safe_fallback(
    xml_bytes: bytes,
    expected_message: str,
):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=xml_bytes, request=request)

    result = _registry_source(handler).fetch_datastructure(
        "SDMX", "DSD_TEST", "1.0"
    )

    assert result.status == "fallback"
    assert result.entries == []
    assert result.message == expected_message


@pytest.mark.parametrize(
    "xml_bytes",
    [
        _dsd_xml(agency_id="OTHER"),
        _dsd_xml(artefact_id="DSD_OTHER"),
    ],
)
def test_global_registry_identity_mismatch_returns_safe_fallback(xml_bytes: bytes):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=xml_bytes, request=request)

    result = _registry_source(handler).fetch_datastructure(
        "SDMX", "DSD_TEST", "1.0"
    )

    assert result.status == "fallback"
    assert result.entries == []
    assert result.message == "The registry response did not match the requested structure; using cached references."


def test_global_registry_explicit_version_mismatch_returns_safe_fallback():
    xml_bytes = _dsd_xml(version="2.0")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=xml_bytes, request=request)

    result = _registry_source(handler).fetch_datastructure(
        "SDMX", "DSD_TEST", "1.0"
    )

    assert result.status == "fallback"
    assert result.entries == []
    assert result.message == "The registry response did not match the requested structure; using cached references."


def test_merge_refresh_replaces_exact_identity_and_preserves_unrelated_cache():
    replaced = _library_entry("SDMX", "DSD_TEST", "1.0")
    unrelated = _library_entry("OTHER", "DSD_OTHER", "2.0")
    live = _library_entry(
        "SDMX",
        "DSD_TEST",
        "1.0",
        retrieval_mode="live",
        name="Live structure",
    )
    added = _library_entry(
        "SDMX",
        "DSD_NEW",
        "1.0",
        retrieval_mode="live",
    )
    cache = [replaced, unrelated]
    refresh = SourceRefreshResult(
        source_id="SDMX_GLOBAL_REGISTRY",
        status="success",
        entries=[live, added],
        message="Refreshed.",
    )

    merged = merge_refresh(cache, refresh)

    assert [entry.metadata.identity for entry in merged] == [
        "SDMX:DSD_TEST(1.0)",
        "OTHER:DSD_OTHER(2.0)",
        "SDMX:DSD_NEW(1.0)",
    ]
    assert merged[0] is live
    assert merged[1] is unrelated
    assert cache == [replaced, unrelated]
    assert merged is not cache


def test_merge_refresh_fallback_preserves_cache_order_values_and_input_list():
    first = _library_entry("SDMX", "DSD_FIRST", "1.0")
    second = _library_entry("SDMX", "DSD_SECOND", "2.0")
    cache = [first, second]
    original = list(cache)
    refresh = SourceRefreshResult(
        source_id="SDMX_GLOBAL_REGISTRY",
        status="fallback",
        entries=[],
        message="Using cache.",
    )

    merged = merge_refresh(cache, refresh)

    assert merged == original
    assert merged is not cache
    assert cache == original
