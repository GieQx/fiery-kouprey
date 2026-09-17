# Standards Discovery Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revise the existing Streamlit MVP so a producer uploads one local DSD, discovers explainable candidate standards from a curated library, selects one reference, and completes a traceable human-reviewed alignment assessment.

**Architecture:** Preserve the existing parser, comparator, provider abstraction, review service, and export service. Add a manifest-backed reference library and deterministic discovery engine in front of comparison, then extend finding/review models without introducing a database or separate API.

**Tech Stack:** Python 3.11+, Streamlit, Pydantic, lxml, pandas, pytest, Streamlit AppTest, OpenAI client, HTTPX/Ollama.

**Execution note:** The project directory is not currently a Git repository. Initialize source control or create a dated backup before implementation; do not overwrite the working MVP without a recovery point.

---

## File Map

### Create

- `sdmx_alignment/models/reference.py`: reference-standard and discovery-candidate contracts.
- `sdmx_alignment/reference_library.py`: load and validate the curated manifest and DSD files.
- `sdmx_alignment/discovery.py`: deterministic candidate evidence and tier ordering.
- `reference_library/manifest.json`: versioned metadata and provenance for 3-5 DSDs.
- `reference_library/*.xml`: local offline copies of curated reference DSDs.
- `benchmarks/manifest.json`: expert-validated expected cases.
- `tests/test_reference_library.py`: manifest and provenance tests.
- `tests/test_discovery.py`: candidate evidence and no-match tests.
- `tests/test_benchmarks.py`: fixture classification tests.

### Modify

- `sdmx_alignment/models/structures.py`: preserve additional DSD annotations and metadata.
- `sdmx_alignment/models/findings.py`: categories, provenance, origin, limitations, and richer review state.
- `sdmx_alignment/parser/sdmx_structure.py`: extract additional available DSD-level metadata.
- `sdmx_alignment/comparator/engine.py`: produce the revised finding classifications.
- `sdmx_alignment/review.py`: Modify and No Action Required decisions.
- `sdmx_alignment/export.py`: discovery evidence, provenance, reviewed modifications, and CSV export.
- `app.py`: one-upload discovery-first workflow and renamed interface.
- `tests/test_app.py`: upload, discovery, selection, and comparison journey.
- `README.md`: revised scope, library setup, run, and demo instructions.

---

## Milestone 1: One-Upload Discovery Vertical Slice

### Task 1: Reference Library Models

**Files:**
- Create: `sdmx_alignment/models/reference.py`
- Modify: `sdmx_alignment/models/__init__.py`
- Test: `tests/test_reference_library.py`

- [ ] **Step 1: Write the failing model test**

```python
from datetime import date

from sdmx_alignment.models.reference import ReferenceStandard


def test_reference_standard_requires_version_and_provenance():
    item = ReferenceStandard(
        agency_id="SDMX",
        artefact_id="DSD_LABOUR",
        version="1.0",
        name="Labour reference",
        description="Curated labour statistics reference",
        domain="labour",
        provenance="SDMX Global Registry",
        source_url="https://registry.sdmx.org/",
        retrieved_at=date(2026, 9, 17),
        fixture_classification="authoritative_reference",
        local_file="labour.xml",
    )
    assert item.identity == "SDMX:DSD_LABOUR(1.0)"
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `uv run pytest tests/test_reference_library.py::test_reference_standard_requires_version_and_provenance -v`

Expected: failure because `sdmx_alignment.models.reference` does not exist.

- [ ] **Step 3: Add the minimum model contracts**

```python
from datetime import date
from typing import Literal

from pydantic import BaseModel, computed_field


class ReferenceStandard(BaseModel):
    agency_id: str
    artefact_id: str
    version: str
    name: str
    description: str
    domain: str
    provenance: str
    source_url: str | None = None
    retrieved_at: date
    fixture_classification: Literal["authoritative_reference", "synthetic_benchmark"]
    local_file: str

    @computed_field
    @property
    def identity(self) -> str:
        return f"{self.agency_id}:{self.artefact_id}({self.version})"


class DiscoveryEvidence(BaseModel):
    signal: str
    count: int
    examples: list[str]


class DiscoveryCandidate(BaseModel):
    reference: ReferenceStandard
    evidence: list[DiscoveryEvidence]
    discovery_tier: Literal["strong", "plausible", "weak"]
    explanation: str
```

- [ ] **Step 4: Run the model tests**

Run: `uv run pytest tests/test_reference_library.py -v`

Expected: all tests pass.

### Task 2: Curated Manifest Loader

**Files:**
- Create: `sdmx_alignment/reference_library.py`
- Create: `reference_library/manifest.json`
- Create: `reference_library/reference-demo.xml`
- Test: `tests/test_reference_library.py`

- [ ] **Step 1: Add a failing loader test**

```python
from pathlib import Path

from sdmx_alignment.reference_library import load_reference_library


def test_library_loads_manifest_and_exact_dsd_version(tmp_path: Path):
    library = load_reference_library(Path("reference_library/manifest.json"))
    assert 1 <= len(library) <= 5
    assert all(item.metadata.version for item in library)
    assert all(item.structure.version == item.metadata.version for item in library)
```

- [ ] **Step 2: Run the test and confirm the missing loader failure**

Run: `uv run pytest tests/test_reference_library.py -v`

- [ ] **Step 3: Add a three-entry manifest**

Use one clearly labeled synthetic demo reference initially, then replace or supplement it with at least two authoritative, versioned DSDs whose redistribution is allowed. Every manifest entry must include all fields defined by `ReferenceStandard`.

```json
{
  "standards": [
    {
      "agency_id": "SDMX",
      "artefact_id": "DSD_REFERENCE_EMP",
      "version": "2.0",
      "name": "Employment reference benchmark",
      "description": "Synthetic offline benchmark for the hackathon",
      "domain": "labour",
      "provenance": "Hackathon benchmark fixture",
      "source_url": null,
      "retrieved_at": "2026-09-17",
      "fixture_classification": "synthetic_benchmark",
      "local_file": "reference-demo.xml"
    }
  ]
}
```

- [ ] **Step 4: Implement strict manifest loading**

```python
from pathlib import Path
import json

from pydantic import BaseModel

from sdmx_alignment.models.reference import ReferenceStandard
from sdmx_alignment.models.structures import DSDStructure
from sdmx_alignment.parser.sdmx_structure import parse_structure


class LibraryEntry(BaseModel):
    metadata: ReferenceStandard
    structure: DSDStructure


def load_reference_library(manifest_path: Path) -> list[LibraryEntry]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    standards = [ReferenceStandard.model_validate(row) for row in payload["standards"]]
    if not 1 <= len(standards) <= 5:
        raise ValueError("Reference library must contain between 1 and 5 standards")

    entries = []
    for metadata in standards:
        xml_path = manifest_path.parent / metadata.local_file
        structure = parse_structure(xml_path.name, xml_path.read_bytes())
        if structure.agency_id != metadata.agency_id or structure.id != metadata.artefact_id:
            raise ValueError(f"Manifest identity does not match {xml_path.name}")
        if structure.version != metadata.version:
            raise ValueError(f"Manifest version does not match {xml_path.name}")
        entries.append(LibraryEntry(metadata=metadata, structure=structure))
    return entries
```

- [ ] **Step 5: Run reference-library tests**

Run: `uv run pytest tests/test_reference_library.py -v`

Expected: manifest loads; missing files, identity mismatches, and version mismatches fail safely.

### Task 3: Explainable Deterministic Discovery

**Files:**
- Create: `sdmx_alignment/discovery.py`
- Test: `tests/test_discovery.py`

- [ ] **Step 1: Write failing candidate and no-match tests**

```python
from pathlib import Path

from sdmx_alignment.discovery import discover_candidates
from sdmx_alignment.parser.sdmx_structure import parse_structure
from sdmx_alignment.reference_library import load_reference_library


def test_discovery_explains_candidate_signals():
    local = parse_structure("local-demo.xml", Path("samples/local-demo.xml").read_bytes())
    library = load_reference_library(Path("reference_library/manifest.json"))
    result = discover_candidates(local, library)
    assert result.candidates
    assert any(e.signal == "exact_concept_id" for e in result.candidates[0].evidence)
    assert result.candidates[0].explanation


def test_discovery_can_return_no_suitable_reference(unrelated_structure, library):
    result = discover_candidates(unrelated_structure, library)
    assert result.candidates == []
    assert result.message == "No suitable reference standard identified."
```

- [ ] **Step 2: Run the discovery tests and confirm they fail**

Run: `uv run pytest tests/test_discovery.py -v`

- [ ] **Step 3: Implement evidence-first discovery**

```python
from pydantic import BaseModel

from sdmx_alignment.models.reference import DiscoveryCandidate, DiscoveryEvidence
from sdmx_alignment.models.structures import DSDStructure
from sdmx_alignment.reference_library import LibraryEntry


class DiscoveryResult(BaseModel):
    candidates: list[DiscoveryCandidate]
    message: str


def discover_candidates(local: DSDStructure, library: list[LibraryEntry]) -> DiscoveryResult:
    candidates: list[DiscoveryCandidate] = []
    local_ids = {item.id for item in local.dimensions + local.attributes}

    for entry in library:
        reference_ids = {item.id for item in entry.structure.dimensions + entry.structure.attributes}
        shared_ids = sorted(local_ids & reference_ids)
        shared_codelists = sorted(
            {item.ref.id for item in local.codelists.values()}
            & {item.ref.id for item in entry.structure.codelists.values()}
        )
        if not shared_ids and not shared_codelists:
            continue
        evidence = [
            DiscoveryEvidence(signal="exact_concept_id", count=len(shared_ids), examples=shared_ids[:5]),
            DiscoveryEvidence(signal="shared_codelist", count=len(shared_codelists), examples=shared_codelists[:5]),
        ]
        tier = "strong" if len(shared_ids) >= 3 or shared_codelists else "plausible"
        candidates.append(
            DiscoveryCandidate(
                reference=entry.metadata,
                evidence=evidence,
                discovery_tier=tier,
                explanation=f"{len(shared_ids)} exact component IDs and {len(shared_codelists)} shared codelists.",
            )
        )

    candidates.sort(
        key=lambda item: (
            item.discovery_tier == "strong",
            sum(e.count for e in item.evidence),
            item.reference.identity,
        ),
        reverse=True,
    )
    return DiscoveryResult(
        candidates=candidates[:5],
        message="Candidate standards found." if candidates else "No suitable reference standard identified.",
    )
```

- [ ] **Step 4: Add label, concept-scheme, code-label, structure, representation, and domain signals one at a time**

For each signal, first add a focused failing test, then add the smallest deterministic implementation. Do not introduce a single opaque numeric alignment score. Keep evidence counts and examples individually visible.

- [ ] **Step 5: Run parser, library, and discovery tests**

Run: `uv run pytest tests/test_parser.py tests/test_reference_library.py tests/test_discovery.py -v`

Expected: all tests pass with and without candidate matches.

### Task 4: Replace Two-Upload UI with Discovery-First Flow

**Files:**
- Modify: `app.py`
- Modify: `tests/test_app.py`

- [ ] **Step 1: Change the AppTest expectation before changing the UI**

```python
from streamlit.testing.v1 import AppTest


def test_app_uses_one_upload_and_discovery_flow():
    app = AppTest.from_file("app.py").run()
    assert len(app.file_uploader) == 1
    assert app.file_uploader[0].label == "Local DSD"
    assert app.title[0].value == "SDMX Standards Discovery and Alignment Assistant"
    assert any(button.label == "Load local demo" for button in app.button)
```

- [ ] **Step 2: Run the AppTest and confirm the old two-upload flow fails**

Run: `uv run pytest tests/test_app.py -v`

- [ ] **Step 3: Add explicit workflow state**

Initialize these session keys in `initialize_state()`:

```python
defaults = {
    "local_structure": None,
    "discovery_result": None,
    "selected_reference_identity": None,
    "comparison": None,
    "alignment_plan": None,
    "evaluation": None,
}
```

- [ ] **Step 4: Split the page into three rendering functions**

```python
def render_local_upload() -> None: ...
def render_discovery_candidates(library) -> None: ...
def render_alignment_workspace(settings, matcher, library) -> None: ...
```

`render_local_upload()` parses one upload. `render_discovery_candidates()` shows evidence and requires a Select action. `render_alignment_workspace()` calls the existing `compare_structures()` only after selection.

- [ ] **Step 5: Add the no-match and browse-library paths**

The no-match state must display the exact message and must not enable detailed comparison until the user manually selects an entry from the library.

- [ ] **Step 6: Run AppTest and the existing suite**

Run: `uv run pytest -p no:cacheprovider`

Expected: all existing tests pass after updating obsolete two-upload assumptions.

---

## Milestone 2: Revised Findings, Review, and Export

### Task 5: Expand Finding and Review Contracts

**Files:**
- Modify: `sdmx_alignment/models/findings.py`
- Modify: `sdmx_alignment/review.py`
- Test: `tests/test_alignment_workflow.py`

- [ ] **Step 1: Add tests for the revised classifications and decisions**

```python
def test_reviewer_can_modify_or_mark_no_action(finding):
    modified = apply_review(
        finding,
        decision="modified",
        action="MAP",
        note="Use the approved national-to-reference bridge.",
        modified_relation="partial",
    )
    assert modified.review_status == "modified"
    assert modified.original_relation == finding.relation
    assert modified.relation == "partial"

    no_action = apply_review(finding, decision="no_action_required", note="Intentional extension")
    assert no_action.review_status == "no_action_required"
```

- [ ] **Step 2: Replace free-form statuses with literal enums**

Add status values matching the blueprint: exact alignment, equivalent, partial alignment, mapping required, representation difference, local extension, reference-only element, metadata gap, potential semantic correspondence, potential semantic conflict, insufficient metadata, and unresolved.

- [ ] **Step 3: Preserve proposal and review separately**

Add `original_relation`, `reviewer_modification`, `reviewer`, `reviewed_at`, `limitations`, `origin`, and reference provenance fields. Migrate existing findings without losing current evidence.

- [ ] **Step 4: Run workflow tests**

Run: `uv run pytest tests/test_alignment_workflow.py -v`

### Task 6: Upgrade Detailed Comparison Classification

**Files:**
- Modify: `sdmx_alignment/comparator/engine.py`
- Modify: `tests/test_comparator.py`

- [ ] **Step 1: Add one failing test per new deterministic classification**

Cover exact alignment, code mapping, representation difference, local extension, reference-only element, metadata gap, and insufficient metadata.

- [ ] **Step 2: Keep comparison precedence explicit**

```text
exact identity and compatible evidence
-> mapping required
-> representation difference
-> potential semantic correspondence/conflict
-> insufficient metadata
-> local extension/reference-only
-> unresolved
```

- [ ] **Step 3: Require supporting metadata for semantic equivalence**

Do not classify equal labels such as `AGE` as equivalent when definitions, representations, or codelists conflict. Use potential semantic conflict or insufficient metadata.

- [ ] **Step 4: Run comparator and semantic tests**

Run: `uv run pytest tests/test_comparator.py tests/test_semantic_matcher.py -v`

### Task 7: Traceable JSON and CSV Export

**Files:**
- Modify: `sdmx_alignment/export.py`
- Modify: `tests/test_alignment_workflow.py`

- [ ] **Step 1: Add export assertions**

```python
def test_export_contains_discovery_provenance_and_review(comparison, discovery):
    package = export_evidence_package(comparison, discovery=discovery)
    assert package["selected_reference"]["version"]
    assert package["selected_reference"]["provenance"]
    assert package["discovery_results"]
    assert "reviewer_decision" in package["findings"][0]
```

- [ ] **Step 2: Extend JSON without exposing provider payloads**

Include schema version, discovery evidence, selected reference, category counts, original proposals, reviewed decisions, limitations, and product claims.

- [ ] **Step 3: Add a flattened CSV exporter**

```python
def findings_to_csv(result: ComparisonResult) -> str:
    rows = [flatten_finding(item, result) for item in result.findings]
    return pandas.DataFrame(rows).to_csv(index=False)
```

- [ ] **Step 4: Run export tests and secret scan**

Run: `uv run pytest tests/test_alignment_workflow.py -v`

Run: `rg -n -i "api[_-]?key|authorization|bearer|raw_response" tests/output`

Expected: tests pass and the scan returns no secret-bearing export fields.

---

## Milestone 3: Benchmark, Demo, and Release Gate

### Task 8: Expert-Validated Benchmark Fixtures

**Files:**
- Create: `benchmarks/manifest.json`
- Create: `tests/test_benchmarks.py`
- Add: `benchmarks/*.xml`

- [ ] **Step 1: Define eight expected cases**

The manifest must include exact match, equivalent different ID, same concept different codes, partial match, local extension, reference-only element, false `AGE` similarity, and insufficient metadata. Each case includes expected status, evidence rationale, and reviewer name/initials.

- [ ] **Step 2: Parameterize the benchmark test**

```python
@pytest.mark.parametrize("case", load_benchmark_cases())
def test_benchmark_classification(case):
    result = run_case(case)
    finding = next(item for item in result.findings if item.id == case.finding_id)
    assert finding.alignment_status == case.expected_status
```

- [ ] **Step 3: Run the benchmark suite in no-LLM mode**

Run: `uv run pytest tests/test_benchmarks.py -v`

Expected: deterministic cases pass; ambiguous cases remain conflict, insufficient metadata, or unresolved.

### Task 9: UI and Demo Hardening

**Files:**
- Modify: `app.py`
- Modify: `README.md`
- Modify: `tests/test_app.py`

- [ ] **Step 1: Add UI assertions for boundaries and provenance**

Verify the app shows producer-assistance wording, reference version/provenance, AI expert-validation warning, no overall score, and JSON/CSV download controls.

- [ ] **Step 2: Run the complete automated suite**

Run: `uv run pytest -p no:cacheprovider`

Expected: all tests pass.

- [ ] **Step 3: Launch the app with telemetry disabled**

Run: `uv run streamlit run app.py --browser.gatherUsageStats false`

- [ ] **Step 4: Perform browser QA at desktop and mobile widths**

Verify upload, discovery, candidate selection, comparison, review, and both downloads. Confirm no horizontal overflow, clipped labels, browser-console errors, or server warnings.

- [ ] **Step 5: Rehearse the five-minute demo**

Use the exact scenario in `MVP_BLUEPRINT.md`. The successful close is a traceable reviewed decision and export, not a score or certification claim.

---

## Recommended Starting Checkpoint

Implement Tasks 1-4 first. Stop and demonstrate this vertical slice before changing finding classifications:

1. Upload one local DSD.
2. Load a three-entry reference manifest.
3. Show explainable deterministic candidates or the no-match message.
4. Select one reference.
5. Run the existing detailed comparator.

This checkpoint proves the revised product idea while preserving the already-working comparison, LLM fallback, review, and export functionality.

