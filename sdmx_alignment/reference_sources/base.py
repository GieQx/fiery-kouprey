from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

if TYPE_CHECKING:
    from sdmx_alignment.reference_library import LibraryEntry


@dataclass(frozen=True, slots=True)
class SourceRefreshResult:
    source_id: str
    status: Literal["success", "fallback"]
    entries: list[LibraryEntry]
    message: str


class ReferenceSource(Protocol):
    source_id: str

    def fetch_datastructure(
        self,
        agency_id: str,
        artefact_id: str,
        version: str,
    ) -> SourceRefreshResult: ...
