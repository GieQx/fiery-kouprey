from __future__ import annotations

from datetime import date
from urllib.parse import quote

import httpx

from sdmx_alignment.models.reference import ReferenceStandard
from sdmx_alignment.parser.sdmx_structure import StructureParseError, parse_structure
from sdmx_alignment.reference_library import LibraryEntry
from sdmx_alignment.reference_sources.base import SourceRefreshResult


DEFAULT_BASE_URL = "https://registry.sdmx.org/sdmx/v2/"
DEFAULT_MAX_RESPONSE_BYTES = 5 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 5.0
SDMX_ML_ACCEPT = "application/vnd.sdmx.structure+xml;version=2.1"


class GlobalRegistrySource:
    source_id = "SDMX_GLOBAL_REGISTRY"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        if max_response_bytes < 1:
            raise ValueError("max_response_bytes must be positive")
        self._client = client or httpx.Client()
        self._base_url = base_url.rstrip("/") + "/"
        self._timeout = timeout
        self._max_response_bytes = max_response_bytes

    def fetch_datastructure(
        self,
        agency_id: str,
        artefact_id: str,
        version: str,
    ) -> SourceRefreshResult:
        agency_id = agency_id.strip()
        artefact_id = artefact_id.strip()
        version = version.strip()
        if not agency_id or not artefact_id:
            raise ValueError("agency_id and artefact_id must be nonblank")
        if not version:
            raise ValueError("version must be an explicit version or 'latest'")

        path = "/".join(
            quote(value, safe="") for value in (agency_id, artefact_id, version)
        )
        endpoint = f"{self._base_url}structure/datastructure/{path}"
        request_url = httpx.URL(endpoint, params={"references": "all"})

        try:
            with self._client.stream(
                "GET",
                request_url,
                headers={"Accept": SDMX_ML_ACCEPT},
                timeout=self._timeout,
                follow_redirects=True,
            ) as response:
                if not response.is_success:
                    return self._fallback(
                        "The SDMX Global Registry rejected the structure request; "
                        "using cached references."
                    )
                xml_bytes = self._read_bounded(response)
        except _ResponseTooLarge:
            return self._fallback(
                "The registry response exceeded the safe size limit; using cached references."
            )
        except httpx.RequestError:
            return self._fallback(
                "The SDMX Global Registry could not be reached; using cached references."
            )

        file_name = f"{artefact_id}.xml"
        try:
            structure = parse_structure(file_name, xml_bytes)
        except (StructureParseError, ValueError):
            return self._fallback(
                "The registry returned invalid SDMX structure XML; using cached references."
            )

        identity_matches = (
            structure.agency_id == agency_id and structure.id == artefact_id
        )
        version_matches = version.casefold() == "latest" or structure.version == version
        if not identity_matches or not version_matches or not structure.version:
            return self._fallback(
                "The registry response did not match the requested structure; "
                "using cached references."
            )

        description = (
            structure.descriptions.get("en")
            or next(iter(structure.descriptions.values()), "")
            or f"SDMX DataStructure {structure.id}."
        )
        try:
            metadata = ReferenceStandard(
                agency_id=structure.agency_id,
                artefact_id=structure.id,
                version=structure.version,
                name=structure.label,
                description=description,
                domain="SDMX structural metadata",
                issuer=structure.agency_id,
                artefact_type="structural_reference",
                provenance="Retrieved live from the SDMX Global Registry.",
                source_url=str(request_url),
                retrieved_at=date.today(),
                fixture_classification="authoritative_reference",
                local_file=file_name,
                source_id=self.source_id,
                retrieval_mode="live",
                trust_level="authoritative",
            )
        except ValueError:
            return self._fallback(
                "The registry returned invalid SDMX structure XML; using cached references."
            )

        entry = LibraryEntry(
            metadata=metadata,
            structure=structure,
            xml_bytes=xml_bytes,
        )
        return SourceRefreshResult(
            source_id=self.source_id,
            status="success",
            entries=[entry],
            message=f"Refreshed {metadata.identity} from the SDMX Global Registry.",
        )

    def _read_bounded(self, response: httpx.Response) -> bytes:
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > self._max_response_bytes:
                    raise _ResponseTooLarge
            except ValueError:
                pass

        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > self._max_response_bytes:
                raise _ResponseTooLarge
            chunks.append(chunk)
        return b"".join(chunks)

    def _fallback(self, message: str) -> SourceRefreshResult:
        return SourceRefreshResult(
            source_id=self.source_id,
            status="fallback",
            entries=[],
            message=message,
        )


class _ResponseTooLarge(Exception):
    pass
