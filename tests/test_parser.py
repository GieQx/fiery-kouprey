from pathlib import Path

import pytest

from sdmx_alignment.parser.sdmx_structure import (
    StructureParseError,
    parse_dataflow_structure_ref,
    parse_structure,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_structure_extracts_dsd_components_and_embedded_codelists():
    structure = parse_structure("local-demo.xml", (FIXTURES / "local-demo.xml").read_bytes())

    assert structure.id == "DSD_LOCAL_EMP"
    assert structure.agency_id == "PSA_DEMO"
    assert structure.version == "1.0"
    assert structure.label == "Local employment structure"
    assert [item.id for item in structure.dimensions] == [
        "AREA", "SEX", "EMP_STATUS", "LOCAL_DETAIL", "FREQ"
    ]
    assert structure.dimensions[0].concept_ref.id == "AREA"
    assert structure.dimensions[0].codelist_ref.id == "CL_AREA_LOCAL"
    assert structure.dimensions[2].representation.kind == "text"
    assert structure.dimensions[2].representation.facets["maxLength"] == "12"
    assert structure.attributes[0].id == "UNIT_MULT"
    assert [code.label for code in structure.codelists["PSA_DEMO:CL_SEX_LOCAL(1.0)"].codes] == [
        "Male", "Female", "Total"
    ]
    assert "Dimension[@id='AREA']" in structure.dimensions[0].source_path


def test_parse_structure_rejects_dtd_before_parsing():
    xml = b'<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>'

    with pytest.raises(StructureParseError, match="DTD and entity declarations are not allowed"):
        parse_structure("unsafe.xml", xml)


def test_parse_structure_rejects_xml_without_dsd():
    with pytest.raises(StructureParseError, match="does not contain an SDMX DataStructure"):
        parse_structure("empty.xml", b"<root />")


def test_parse_dataflow_structure_ref_extracts_sdmx_30_urn():
    xml_bytes = (FIXTURES / "DSD_BOP@DF_BOP.xml").read_bytes()

    reference = parse_dataflow_structure_ref("DSD_BOP@DF_BOP.xml", xml_bytes)

    assert reference.agency_id == "SDMXWS"
    assert reference.id == "DSD_BOP"
    assert reference.version == "1.0"
