from __future__ import annotations

from typing import TYPE_CHECKING

from sdmx_alignment.reference_sources.base import SourceRefreshResult

if TYPE_CHECKING:
    from sdmx_alignment.reference_library import LibraryEntry


def merge_refresh(
    cache: list[LibraryEntry],
    refresh: SourceRefreshResult,
) -> list[LibraryEntry]:
    if refresh.status != "success":
        return list(cache)

    by_identity = {entry.metadata.identity: entry for entry in cache}
    by_identity.update(
        {entry.metadata.identity: entry for entry in refresh.entries}
    )
    return list(by_identity.values())
