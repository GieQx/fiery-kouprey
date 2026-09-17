from __future__ import annotations

from pydantic import BaseModel, Field

from sdmx_alignment.comparator.normalize import normalize_text
from sdmx_alignment.models.reference import DiscoveryCandidate, DiscoveryEvidence
from sdmx_alignment.models.structures import Component, DSDStructure
from sdmx_alignment.reference_library import LibraryEntry


DOMAIN_TERMS = {
    "labour": {"labour", "employment", "work"},
    "tourism": {"tourism", "visitor", "travel"},
    "prices": {"price", "prices", "cpi", "inflation"},
    "external_sector": {
        "balance of payments",
        "bop",
        "external sector",
        "international investment",
    },
}


class DiscoveryResult(BaseModel):
    candidates: list[DiscoveryCandidate] = Field(default_factory=list)
    message: str


def _components(structure: DSDStructure) -> list[Component]:
    return structure.dimensions + structure.attributes


def _code_labels(structure: DSDStructure) -> set[str]:
    return {
        normalize_text(code.label)
        for codelist in structure.codelists.values()
        for code in codelist.codes
        if normalize_text(code.label)
    }


def _representation_kinds(structure: DSDStructure) -> set[str]:
    return {
        component.representation.kind
        for component in _components(structure)
        if component.representation is not None
    }


def _domain_matches(local: DSDStructure, domain: str) -> list[str]:
    local_text = normalize_text(" ".join([local.label, *local.names.values(), *local.descriptions.values()]))
    return sorted(term for term in DOMAIN_TERMS.get(domain.casefold(), {domain.casefold()}) if term in local_text)


def _candidate(local: DSDStructure, entry: LibraryEntry) -> DiscoveryCandidate | None:
    local_components = _components(local)
    reference_components = _components(entry.structure)
    local_ids = {item.id for item in local_components}
    reference_ids = {item.id for item in reference_components}
    exact_ids = sorted(local_ids & reference_ids)

    local_labels = {normalize_text(item.label) for item in local_components}
    reference_labels = {normalize_text(item.label) for item in reference_components}
    label_matches = sorted((local_labels & reference_labels) - {""})

    local_schemes = {
        item.concept_ref.maintainable_parent_id
        for item in local_components
        if item.concept_ref and item.concept_ref.maintainable_parent_id
    }
    reference_schemes = {
        item.concept_ref.maintainable_parent_id
        for item in reference_components
        if item.concept_ref and item.concept_ref.maintainable_parent_id
    }
    scheme_matches = sorted(local_schemes & reference_schemes)

    local_codelists = {item.ref.id for item in local.codelists.values()}
    reference_codelists = {item.ref.id for item in entry.structure.codelists.values()}
    codelist_matches = sorted(local_codelists & reference_codelists)
    code_label_matches = sorted(_code_labels(local) & _code_labels(entry.structure))
    representation_matches = sorted(_representation_kinds(local) & _representation_kinds(entry.structure))
    domain_matches = _domain_matches(local, entry.metadata.domain)

    meaningful_count = sum(
        len(items)
        for items in (
            exact_ids,
            label_matches,
            scheme_matches,
            codelist_matches,
            code_label_matches,
            domain_matches,
        )
    )
    if meaningful_count == 0:
        return None

    evidence = [
        DiscoveryEvidence(signal="exact_component_id", count=len(exact_ids), examples=exact_ids[:5]),
        DiscoveryEvidence(signal="normalized_label_overlap", count=len(label_matches), examples=label_matches[:5]),
        DiscoveryEvidence(signal="concept_scheme_overlap", count=len(scheme_matches), examples=scheme_matches[:5]),
        DiscoveryEvidence(signal="shared_codelist", count=len(codelist_matches), examples=codelist_matches[:5]),
        DiscoveryEvidence(signal="code_label_overlap", count=len(code_label_matches), examples=code_label_matches[:5]),
        DiscoveryEvidence(
            signal="structural_similarity",
            count=min(len(local_components), len(reference_components)),
            examples=[f"{len(local.dimensions)} vs {len(entry.structure.dimensions)} dimensions"],
        ),
        DiscoveryEvidence(
            signal="representation_similarity",
            count=len(representation_matches),
            examples=representation_matches[:5],
        ),
        DiscoveryEvidence(signal="domain_metadata_overlap", count=len(domain_matches), examples=domain_matches[:5]),
    ]
    if len(exact_ids) >= 3 or len(code_label_matches) >= 3:
        tier = "strong"
    elif exact_ids or label_matches or codelist_matches or domain_matches:
        tier = "plausible"
    else:
        tier = "weak"

    explanation = (
        f"{len(exact_ids)} exact component matches, {len(label_matches)} matching labels, "
        f"{len(codelist_matches)} shared codelists, and {len(code_label_matches)} matching code labels."
    )
    return DiscoveryCandidate(
        reference=entry.metadata,
        evidence=evidence,
        discovery_tier=tier,
        explanation=explanation,
    )


def discover_candidates(local: DSDStructure, library: list[LibraryEntry]) -> DiscoveryResult:
    candidates = [candidate for entry in library if (candidate := _candidate(local, entry)) is not None]
    tier_order = {"strong": 2, "plausible": 1, "weak": 0}
    candidates.sort(
        key=lambda item: (
            tier_order[item.discovery_tier],
            sum(evidence.count for evidence in item.evidence if evidence.signal != "structural_similarity"),
            item.reference.identity,
        ),
        reverse=True,
    )
    return DiscoveryResult(
        candidates=candidates[:5],
        message="Candidate standards found." if candidates else "No suitable reference standard identified.",
    )
