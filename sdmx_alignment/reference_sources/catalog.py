from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from sdmx_alignment.models.reference import MethodologyStandard, TrustedSource


class _SourceCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sources: list[TrustedSource] = Field(min_length=1)


class _MethodologyCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    methodologies: list[MethodologyStandard] = Field(min_length=1)


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalized_id(value: str) -> str:
    return value.strip().casefold()


def load_source_catalog(path: Path) -> list[TrustedSource]:
    catalog = _SourceCatalog.model_validate(_load_json(path))
    source_ids = [_normalized_id(source.id) for source in catalog.sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Duplicate source ID in source catalog")

    defaults = [source for source in catalog.sources if source.is_default]
    if len(defaults) != 1:
        raise ValueError("Source catalog must contain exactly one default source")
    return catalog.sources


def load_methodology_catalog(path: Path) -> list[MethodologyStandard]:
    catalog = _MethodologyCatalog.model_validate(_load_json(path))
    methodology_ids = [_normalized_id(methodology.id) for methodology in catalog.methodologies]
    if len(methodology_ids) != len(set(methodology_ids)):
        raise ValueError("Duplicate methodology ID in methodology catalog")

    principle_ids = [
        _normalized_id(principle.id)
        for methodology in catalog.methodologies
        for principle in methodology.principles
    ]
    if len(principle_ids) != len(set(principle_ids)):
        raise ValueError("Duplicate principle ID in methodology catalog")

    for methodology in catalog.methodologies:
        if any(
            principle.source_url != methodology.source_url
            for principle in methodology.principles
        ):
            raise ValueError(
                f"Methodology {methodology.id} principles must use its canonical source URL"
            )
    return catalog.methodologies
