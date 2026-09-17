# MVP3 Authoritative Sources and Recommendation Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make uploaded SDMX structures the only production entry path, prioritize cache-first SDMX Global Registry references, support trusted structural and methodological sources, and add a grounded AI recommendation agent under the existing human-review and transformation controls.

**Architecture:** Preserve `Finding` as the unit reviewed and transformed, enriching it with recommendation and provenance fields. Add provider-neutral source catalogs and a bounded Global Registry adapter in front of the existing curated library. Deterministic recommendations run first; optional LLM recommendations use structured requests, strict allow-lists, and an abstention fallback.

**Tech Stack:** Python 3.13, Streamlit, Pydantic 2, lxml, httpx, OpenAI SDK, Ollama HTTP API, pytest, Streamlit AppTest, Playwright CLI.

**Repository Note:** This workspace has no Git metadata. Each task therefore ends with focused and full-suite verification rather than a commit; sync to the live workshop directory occurs only after all tests pass.

---

## File Map

**Create:**

- `sdmx_alignment/reference_sources/__init__.py` - public source-layer exports.
- `sdmx_alignment/reference_sources/base.py` - source protocol and refresh result.
- `sdmx_alignment/reference_sources/catalog.py` - trusted source and methodology catalog loader.
- `sdmx_alignment/reference_sources/global_registry.py` - bounded SDMX Global Registry client.
- `sdmx_alignment/reference_sources/service.py` - cache-first aggregation and fallback.
- `sdmx_alignment/models/recommendations.py` - structured AI request and response models.
- `sdmx_alignment/recommendations.py` - deterministic recommendation templates, grounding validation, and agent orchestration.
- `reference_library/sources.json` - Global Registry, IMF, OECD, Eurostat, and curated-source definitions.
- `reference_library/methodologies.json` - BPM7/BPM6 methodology metadata and bounded principles.
- `tests/test_reference_sources.py` - source catalog, registry client, and fallback tests.
- `tests/test_recommendations.py` - deterministic, AI grounding, abstention, and provenance tests.

**Modify:**

- `app.py`
- `reference_library/manifest.json`
- `sdmx_alignment/models/reference.py`
- `sdmx_alignment/models/findings.py`
- `sdmx_alignment/models/semantic.py`
- `sdmx_alignment/reference_library.py`
- `sdmx_alignment/discovery.py`
- `sdmx_alignment/semantic_matcher/base.py`
- `sdmx_alignment/semantic_matcher/no_llm_provider.py`
- `sdmx_alignment/semantic_matcher/openai_provider.py`
- `sdmx_alignment/semantic_matcher/ollama_provider.py`
- `sdmx_alignment/semantic_matcher/service.py`
- `sdmx_alignment/export.py`
- `tests/test_app.py`
- `tests/test_discovery.py`
- `tests/test_reference_library.py`
- `tests/test_semantic_matcher.py`
- `README.md`
- `MVP_BLUEPRINT.md`

---

### Task 1: Remove Production Demo Controls

**Files:**

- Modify: `tests/test_app.py`
- Modify: `app.py:273-322`
- Modify: `app.py:370-420`

- [x] **Step 1: Replace button-dependent AppTests with upload tests**

Change the initial assertions to:

```python
assert all(button.label != "Load local demo" for button in app.button)
assert all(button.label != "Load BOP demo" for button in app.button)
assert all(button.label != "Apply transparent BOP demo decisions" for button in app.button)
```

Upload `tests/fixtures/local-demo.xml`, run `Discover standards`, and select `DSD_REFERENCE_EMP`. Upload `tests/fixtures/local-bop-demo.xml` for the BOP source test.

- [x] **Step 2: Run the focused AppTests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_app.py -q
```

Expected: failures because the demo buttons and BOP automatic-decision control still exist.

- [x] **Step 3: Remove only the production UI dependencies**

In `render_source_selection`, replace the three-column demo/upload toolbar with one upload action:

```python
if st.button(
    "Discover standards",
    type="primary",
    width="stretch",
    disabled=local_file is None,
):
    load_local_structure(local_file.name, local_file.getvalue(), library)
```

Delete `apply_bop_demo_decisions` and its button branch. Keep `samples/` and all parser/comparator fixtures.

- [x] **Step 4: Verify GREEN**

Run the focused AppTests and then:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass after obsolete expectations are updated.

---

### Task 2: Add Trusted Source and Methodology Models

**Files:**

- Modify: `sdmx_alignment/models/reference.py`
- Create: `reference_library/sources.json`
- Create: `reference_library/methodologies.json`
- Create: `sdmx_alignment/reference_sources/catalog.py`
- Create: `tests/test_reference_sources.py`

- [x] **Step 1: Write failing catalog tests**

Add tests asserting:

```python
sources = load_source_catalog(Path("reference_library/sources.json"))
assert sources[0].id == "SDMX_GLOBAL_REGISTRY"
assert sources[0].is_default is True
assert {item.id for item in sources} >= {
    "SDMX_GLOBAL_REGISTRY", "IMF", "OECD", "EUROSTAT", "CURATED_LOCAL"
}

methods = load_methodology_catalog(Path("reference_library/methodologies.json"))
bpm7 = next(item for item in methods if item.id == "BPM7")
assert bpm7.issuer == "International Monetary Fund"
assert bpm7.principles
assert all(item.source_url == bpm7.source_url for item in bpm7.principles)
```

- [x] **Step 2: Run tests and verify RED**

Run `pytest tests/test_reference_sources.py -q` and expect import/model failures.

- [x] **Step 3: Implement Pydantic source contracts**

Add models equivalent to:

```python
class TrustedSource(BaseModel):
    id: str
    name: str
    source_type: Literal["registry", "institutional_repository", "curated_repository"]
    base_url: str
    trust_level: Literal["authoritative", "curated"]
    is_default: bool = False

class MethodologyPrinciple(BaseModel):
    id: str
    text: str
    source_url: str

class MethodologyStandard(BaseModel):
    id: str
    name: str
    issuer: str
    version: str
    description: str
    source_url: str
    domains: list[str]
    published_at: date | None = None
    principles: list[MethodologyPrinciple] = Field(default_factory=list)
```

Extend `ReferenceStandard` with `source_id`, `retrieval_mode`, `trust_level`, and `retrieved_at`, using backward-compatible defaults while the manifest is migrated.

- [x] **Step 4: Add explicit JSON catalogs**

Set `SDMX_GLOBAL_REGISTRY` as the sole default source. Include official canonical URLs for IMF, OECD, and Eurostat and keep `CURATED_LOCAL` visibly non-authoritative. Add BPM7 and BPM6 with only bounded, cited principles used by the recommendation agent.

- [x] **Step 5: Implement strict catalog loaders and verify GREEN**

Use `model_validate` for every row, reject duplicate IDs, and reject more than one default source. Run `tests/test_reference_sources.py` and the full suite.

---

### Task 3: Make the Curated Library an Explicit Cache

**Files:**

- Modify: `reference_library/manifest.json`
- Modify: `sdmx_alignment/reference_library.py`
- Modify: `sdmx_alignment/discovery.py`
- Modify: `tests/test_reference_library.py`
- Modify: `tests/test_discovery.py`

- [x] **Step 1: Add failing source-priority tests**

Assert every library entry has a source and retrieval mode. Add an equal-evidence fixture pair and verify authoritative registry cache wins the tie:

```python
result = discover_candidates(local, [curated_entry, registry_entry])
assert result.candidates[0].reference.source_id == "SDMX_GLOBAL_REGISTRY"
```

- [x] **Step 2: Verify RED**

Run `pytest tests/test_reference_library.py tests/test_discovery.py -q`.

- [x] **Step 3: Migrate the manifest**

Add these fields to each standard:

```json
{
  "source_id": "CURATED_LOCAL",
  "retrieval_mode": "curated",
  "trust_level": "curated"
}
```

Registry-derived cached artefacts use `SDMX_GLOBAL_REGISTRY`, `cache`, and `authoritative`. Do not mislabel the workshop BOP file as registry-maintained.

- [x] **Step 4: Add trust as a tie-breaker, not a relevance substitute**

Keep current evidence scoring first. Add a trust rank only after evidence tier and meaningful evidence count so an irrelevant authoritative DSD cannot outrank a relevant curated DSD.

- [x] **Step 5: Verify GREEN**

Run focused tests, then the full suite.

---

### Task 4: Implement Bounded Global Registry Refresh

**Files:**

- Create: `sdmx_alignment/reference_sources/base.py`
- Create: `sdmx_alignment/reference_sources/global_registry.py`
- Create: `sdmx_alignment/reference_sources/service.py`
- Create: `sdmx_alignment/reference_sources/__init__.py`
- Modify: `tests/test_reference_sources.py`

- [x] **Step 1: Write failing HTTP-adapter tests with `httpx.MockTransport`**

Cover:

```python
result = client.fetch_datastructure(agency_id="SDMX", artefact_id="DSD_TEST", version="1.0")
assert result.entries[0].metadata.identity == "SDMX:DSD_TEST(1.0)"
assert result.entries[0].metadata.retrieval_mode == "live"
assert result.source_id == "SDMX_GLOBAL_REGISTRY"
```

Also test timeout, non-2xx response, oversized body, malformed XML, and identity mismatch. Every failure must return a typed refresh result and preserve the supplied cache.

- [x] **Step 2: Verify RED**

Run `pytest tests/test_reference_sources.py -q`.

- [x] **Step 3: Implement the source protocol**

```python
class ReferenceSource(Protocol):
    source_id: str
    def fetch_datastructure(self, agency_id: str, artefact_id: str, version: str) -> SourceRefreshResult: ...

class SourceRefreshResult(BaseModel):
    source_id: str
    status: Literal["success", "fallback"]
    entries: list[LibraryEntry]
    message: str
```

- [x] **Step 4: Implement the Global Registry client**

Build requests beneath configured base URL `https://registry.sdmx.org/sdmx/v2/`, require agency and artefact ID, support `latest` or an explicit version, set SDMX-ML accept headers, use a short timeout, cap response bytes, parse with the existing safe parser, and mark normalized entries `live` and `authoritative`.

Do not issue an unbounded `all/all/all` download.

- [x] **Step 5: Implement cache-preserving aggregation**

```python
def merge_refresh(cache: list[LibraryEntry], refresh: SourceRefreshResult) -> list[LibraryEntry]:
    if refresh.status != "success":
        return cache
    by_identity = {entry.metadata.identity: entry for entry in cache}
    by_identity.update({entry.metadata.identity: entry for entry in refresh.entries})
    return list(by_identity.values())
```

- [x] **Step 6: Verify GREEN**

Run source tests and full suite with network disabled; tests must rely only on `MockTransport`.

---

### Task 5: Add Methodology Selection to the Workflow

**Files:**

- Modify: `app.py`
- Modify: `tests/test_app.py`

- [ ] **Step 1: Write failing Streamlit tests**

Upload the BOP fixture, select the BOP structural reference, then assert a separate selectbox exists:

```python
methodology = next(item for item in app.selectbox if item.label == "Methodological standard")
assert "No methodological standard selected" in methodology.options
assert any("BPM7" in option for option in methodology.options)
```

Assert the structural reference and methodology IDs occupy separate session-state keys.

- [ ] **Step 2: Verify RED**

Run the new AppTest.

- [ ] **Step 3: Add source status and registry refresh UI**

Display `SDMX Global Registry - primary source` with current cache/live status. Put refresh controls in an expander with required agency ID, DSD ID, and version fields. On failure, show `st.warning` and leave `reference_library` session state unchanged.

- [ ] **Step 4: Add methodology filtering**

Filter catalog entries by selected reference domain and related-source IDs. Default to no methodology rather than implying compliance. Store the selected `MethodologyStandard` in session state and reset recommendations when it changes.

- [ ] **Step 5: Verify GREEN**

Run AppTests and full suite.

---

### Task 6: Generate Deterministic Standards Recommendations

**Files:**

- Modify: `sdmx_alignment/models/findings.py`
- Create: `sdmx_alignment/models/recommendations.py`
- Create: `sdmx_alignment/recommendations.py`
- Create: `tests/test_recommendations.py`

- [ ] **Step 1: Write failing deterministic recommendation tests**

For representative findings assert:

```python
recommendations = build_deterministic_recommendations(comparison, reference, methodology)
missing = next(item for item in recommendations if item.alignment_status == "missing_local")
assert missing.recommendation_text
assert missing.reason
assert missing.recommendation_origin == "deterministic"
assert missing.evidence
assert missing.grounding_status == "grounded"
```

Test missing definitions and ambiguous same-label/different-description cases. When no methodology is selected, methodology fields must remain empty rather than inventing a principle.

- [ ] **Step 2: Verify RED**

Run `pytest tests/test_recommendations.py -q`.

- [ ] **Step 3: Extend findings without breaking review**

Add backward-compatible fields:

```python
recommendation_text: str = ""
reason: str = ""
recommendation_origin: Literal["deterministic", "ai"] = "deterministic"
recommendation_category: str = ""
evidence: list[str] = Field(default_factory=list)
citation_ids: list[str] = Field(default_factory=list)
methodology_principle_id: str | None = None
grounding_status: Literal["grounded", "insufficient", "rejected"] = "grounded"
```

Retain `deterministic_evidence`, review state, and transformation action fields for compatibility.

- [ ] **Step 4: Implement fixed templates**

Derive recommendation text from finding classification and only parsed evidence. Never create codes, concepts, definitions, or citations. Use the exact abstention sentence when a useful claim cannot be supported.

- [ ] **Step 5: Verify GREEN**

Run recommendation, comparator, review, transformation, and full tests.

---

### Task 7: Add the Grounded AI Recommendation Contract

**Files:**

- Modify: `sdmx_alignment/models/semantic.py`
- Modify: `sdmx_alignment/semantic_matcher/base.py`
- Modify: `sdmx_alignment/semantic_matcher/no_llm_provider.py`
- Modify: `sdmx_alignment/semantic_matcher/openai_provider.py`
- Modify: `sdmx_alignment/semantic_matcher/ollama_provider.py`
- Modify: `sdmx_alignment/semantic_matcher/service.py`
- Modify: `sdmx_alignment/recommendations.py`
- Modify: `tests/test_semantic_matcher.py`
- Modify: `tests/test_recommendations.py`

- [x] **Step 1: Write failing structured-agent tests**

Define tests for a valid result, invented local ID, invented reference ID, invented citation, invented code, absent methodology principle, malformed JSON, provider failure, and no LLM.

Every invalid case must produce:

```python
assert result.recommendation_text == "Insufficient information for a reliable recommendation."
assert result.grounding_status in {"insufficient", "rejected"}
```

- [x] **Step 2: Verify RED**

Run semantic and recommendation tests.

- [x] **Step 3: Add provider-neutral request and response models**

```python
class StandardsRecommendationRequest(BaseModel):
    finding_id: str
    local: SemanticElement | None
    reference: SemanticElement | None
    allowed_local_ids: list[str]
    allowed_reference_ids: list[str]
    allowed_codes: list[str]
    principles: list[MethodologyPrinciple]
    citations: list[SourceCitation]

class StandardsRecommendationResult(BaseModel):
    local_element_id: str | None
    reference_element_id: str | None
    recommendation: str
    reason: str
    evidence: list[str]
    citation_ids: list[str]
    principle_id: str | None = None
    confidence: float = Field(ge=0, le=1)
    provider: str
    model: str
```

- [x] **Step 4: Extend the provider protocol**

Add `recommend(request)` to `SemanticMatcher`. OpenAI uses JSON response mode; Ollama uses a Pydantic-derived JSON schema with ID/citation enums. `NoLLMProvider.recommend` raises its existing safe `ProviderError`.

- [x] **Step 5: Implement strict post-response grounding validation**

Validate all IDs, codes, principle IDs, and citation IDs against request allow-lists after provider parsing. Reject rather than repair invalid output. Convert every failure to the exact abstention result and do not overwrite deterministic evidence.

- [x] **Step 6: Verify GREEN**

Run semantic/recommendation tests and full suite.

---

### Task 8: Integrate Recommendations with Review, Audit, and UI

**Files:**

- Modify: `app.py`
- Modify: `sdmx_alignment/export.py`
- Modify: `tests/test_app.py`
- Modify: `tests/test_reporting.py`
- Modify: `tests/test_alignment_workflow.py`

- [x] **Step 1: Write failing integration tests**

Assert the UI shows local element, reference/principle, recommendation, reason, evidence, origin, and citation. Assert `Run AI recommendations` is disabled when no provider is ready and enabled with a fake ready matcher.

Assert audit JSON contains:

```python
assert payload["selected_methodology"]["id"] == "BPM7"
assert payload["recommendation_summary"]["deterministic"] >= 1
assert "grounding_status" in payload["original_comparison"]["findings"][0]
```

- [x] **Step 2: Verify RED**

Run AppTest, reporting, and workflow tests.

- [x] **Step 3: Stop automatic AI execution during comparison**

Change `run_comparison` to run `compare_structures` and deterministic recommendation construction only. Add an explicit `Run AI recommendations` command after reference and methodology selection.

- [x] **Step 4: Render recommendation evidence safely**

Use Streamlit text and links rather than injecting model output as raw HTML. Show an AI badge only for AI-origin results and always state human review is required. Render citations only from the trusted catalog.

- [x] **Step 5: Reuse existing review controls**

Keep all five statuses and `apply_review`. Do not add AI-only approval paths. An accepted advisory recommendation uses the existing `REUSE` action so it enters the reviewed audit plan without mutating XML; rejected, unresolved, and no-action recommendations retain their existing semantics.

- [x] **Step 6: Extend audit exports**

Add selected source status, structural reference provenance, selected methodology, recommendation counts, grounding status, provider/model, citations, reviewer decisions, and transformation outcomes. Never export credentials or full provider prompts.

- [x] **Step 7: Verify GREEN**

Run focused integration tests and the full suite.

---

### Task 9: Update Documentation and Blueprint

**Files:**

- Modify: `README.md`
- Modify: `MVP_BLUEPRINT.md`

- [ ] **Step 1: Update the five-minute demo flow**

Document upload-only entry, cache-first Global Registry status, optional exact registry refresh, separate methodology selection, deterministic recommendations, optional grounded AI, human review, and proof exports.

- [ ] **Step 2: Document trust boundaries**

State explicitly that registry source does not prove statistical suitability, methodology selection does not prove compliance, AI cannot create authoritative content, and the app is not full SDMX certification.

- [ ] **Step 3: Document offline behavior**

Explain that failed refresh preserves the curated cache and deterministic comparison remains available with no LLM.

- [ ] **Step 4: Verify documentation consistency**

Run:

```powershell
rg -n "Load local demo|Load BOP demo|automatic.*decision" README.md MVP_BLUEPRINT.md
```

Expected: no production instructions using removed controls.

---

### Task 10: Full Verification and Live Deployment

**Files:**

- Verify all modified files.
- Sync verified files to `D:\Project\SDMX\﻿MODS-OECD-ADB Global Workshop 2026\hackathon-mvp`.

- [ ] **Step 1: Run the complete automated suite**

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: zero failures.

- [ ] **Step 2: Run a direct offline smoke test**

Upload `DSD_BOP@DF_BOP.xml`, resolve `SDMXWS:DSD_BOP(1.0)`, confirm cached fallback works with registry network disabled, select BPM7, generate deterministic recommendations, review at least one recommendation, and verify no XML generation occurs before plan finalization.

- [ ] **Step 3: Sync staging to the live workshop project**

Copy only changed source, catalogs, tests, and documentation. Compare SHA-256 hashes between staging and live copies.

- [ ] **Step 4: Restart Streamlit cleanly**

Run the live project on `http://127.0.0.1:8501` using the staging virtual environment and confirm `/_stcore/health` returns `HTTP 200 ok`.

- [ ] **Step 5: Verify the real browser workflow with Playwright**

At desktop and 390px mobile widths verify:

- no demo buttons;
- uploaded Dataflow resolution;
- Global Registry primary/cache status;
- candidate source metadata;
- separate methodology selection;
- deterministic recommendations without LLM;
- AI command behavior for configured and unavailable providers;
- all five human-review options;
- approval gate and audit exports;
- no overlapping or clipped controls.

- [ ] **Step 6: Capture final evidence**

Record the test count, health response, relevant before/after metrics, and screenshots. Leave the Streamlit server running for the user.
