"""Trusted reference source adapters and catalog access."""

from typing import TYPE_CHECKING, Any

from sdmx_alignment.reference_sources.base import ReferenceSource, SourceRefreshResult
from sdmx_alignment.reference_sources.catalog import (
    load_methodology_catalog,
    load_source_catalog,
)
from sdmx_alignment.reference_sources.service import merge_refresh

if TYPE_CHECKING:
    from sdmx_alignment.reference_sources.global_registry import GlobalRegistrySource


def __getattr__(name: str) -> Any:
    if name == "GlobalRegistrySource":
        from sdmx_alignment.reference_sources.global_registry import GlobalRegistrySource

        return GlobalRegistrySource
    raise AttributeError(name)

__all__ = [
    "GlobalRegistrySource",
    "ReferenceSource",
    "SourceRefreshResult",
    "load_methodology_catalog",
    "load_source_catalog",
    "merge_refresh",
]
