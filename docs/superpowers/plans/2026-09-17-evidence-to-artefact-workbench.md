# Evidence-to-Artefact SDMX Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Deliver a five-minute Balance of Payments workflow that discovers cited references, records expert decisions, deterministically revises an SDMX DSD, validates the result, and proves before-and-after alignment.

**Architecture:** Extend the existing normalized models and curated library, then add independent transformation, validation, and audit services. Streamlit orchestrates three stages while the parser, comparator, LLM abstraction, and deterministic no-LLM path remain intact.

**Tech Stack:** Python 3.11+, Pydantic, lxml, httpx, Streamlit, pytest, Streamlit AppTest

---

### Task 1: Curated BOP Demo and Source Separation

**Files:**
- Modify: `sdmx_alignment/models/reference.py`
- Modify: `sdmx_alignment/reference_library.py`
- Modify: `sdmx_alignment/discovery.py`
- Modify: `reference_library/manifest.json`
- Create: `reference_library/reference-bop-workshop.xml`
- Create: `samples/local-bop-demo.xml`
- Test: `tests/test_reference_library.py`
- Test: `tests/test_discovery.py`

- [x] Write failing tests asserting the BOP record is a workshop structural reference, has separate IMF BPM7/BPM6 methodology citations, exposes issuer/version/source URLs, and ranks first for the local BOP demo.
- [x] Run `pytest tests/test_reference_library.py tests/test_discovery.py -q` and verify failure for missing citation/source fields and BOP assets.
- [x] Add typed `SourceCitation` metadata and structural-reference classification without allowing methodology records into the structural comparator.
- [x] Copy the workshop-supplied `SDMXWS:DSD_BOP(1.0)` structure into the curated library and add a compact synthetic PSA local BOP demo with documented mismatches.
- [x] Extend domain evidence for external-sector terms and run the focused tests to green.

### Task 2: Review Decisions and Approved Change Set

**Files:**
- Modify: `sdmx_alignment/models/alignment.py`
- Modify: `sdmx_alignment/review.py`
- Modify: `sdmx_alignment/alignment_plan.py`
- Modify: `sdmx_alignment/comparator/engine.py`
- Test: `tests/test_alignment_workflow.py`
- Test: `tests/test_comparator.py`

- [x] Write failing tests for accept, modify-and-approve, reject, unresolved, and no-action decisions; assert only approved executable actions enter the change set.
- [x] Write failing tests for representation difference, local extension, reference-only element, mapping required, and exact/no-action display classifications.
- [x] Run focused tests and verify the new statuses and fields are absent.
- [x] Add original recommendation, approved action, reviewer status/note, evidence, and decision timestamp to alignment decisions while preserving old accepted-plan behavior.
- [x] Add judge-readable finding classifications derived from deterministic evidence and run focused tests to green.

### Task 3: Deterministic XML Transformation

**Files:**
- Create: `sdmx_alignment/models/transformation.py`
- Create: `sdmx_alignment/transformation.py`
- Test: `tests/test_transformation.py`

- [x] Write failing tests proving original bytes are unchanged; rejected/unresolved/no-action decisions do not alter XML; approved MAP renames and updates a component from the reference; reviewed code mappings change only listed code IDs; and ADD_MISSING_ELEMENT clones the selected reference component.
- [x] Run `pytest tests/test_transformation.py -q` and verify import failures.
- [x] Implement lxml-based transformation on a defensive copy with entity/network protections, typed per-action results, and no free-form AI input.
- [x] Reparse every generated artefact with `parse_structure` before returning it.
- [x] Run transformation tests to green.

### Task 4: Validation, Reassessment, Before/After, and Audit

**Files:**
- Create: `sdmx_alignment/models/validation.py`
- Create: `sdmx_alignment/validation.py`
- Create: `sdmx_alignment/reporting.py`
- Modify: `sdmx_alignment/export.py`
- Test: `tests/test_validation.py`
- Test: `tests/test_reporting.py`

- [x] Write failing tests for well-formed/reparse checks, unique component IDs, dimension positions, codelist reference resolution, transformation failures, and explicit non-certification language.
- [x] Write failing tests asserting revised-reference comparison, before/after deltas, retained extensions, audit timestamps, source citations, reviewer decisions, AI provenance, JSON export, and CSV change log.
- [x] Implement scoped technical validation and separate reference-alignment status (`ALIGNED`, `PARTIALLY_ALIGNED`, `ISSUES_REMAIN`).
- [x] Implement deterministic before/after aggregation and complete audit exporters without credentials.
- [x] Run focused tests to green.

### Task 5: Three-Stage Streamlit Workbench

**Files:**
- Modify: `app.py`
- Modify: `tests/test_app.py`

- [x] Write failing AppTest coverage for the BOP demo, cited candidate details, explicit selection, review decisions, finalization, generation, validation results, before/after metrics, and revised XML/audit downloads.
- [x] Run `pytest tests/test_app.py -q` and verify the missing controls.
- [x] Preserve original/reference bytes in session state and organize the workbench into `Discover`, `Decide`, and `Generate and Prove` tabs with stage gating.
- [x] Render structural versus methodological sources distinctly, add reason-why/evidence panels, and display the AI expert-validation notice.
- [x] Add all review choices and approved-change summary; enable deterministic generation only for a final plan.
- [x] Render separate technical and alignment outcomes, before/after metrics, limitations, and XML/JSON/CSV downloads.
- [x] Run AppTest coverage to green.

### Task 6: Documentation and End-to-End Verification

**Files:**
- Modify: `README.md`
- Modify: `MVP_BLUEPRINT.md`
- Modify: `docs/superpowers/plans/2026-09-17-evidence-to-artefact-workbench.md`

- [x] Document the BOP demo script, source classifications, validation boundary, no-LLM behavior, and continuation path.
- [x] Run the complete suite with `.venv/Scripts/python.exe -m pytest -q` and require zero failures.
- [x] Run the local BOP workflow with and without Ollama and verify deterministic functions remain available.
- [x] Copy tested files into the live workshop folder without overwriting unrelated work.
- [x] Restart Streamlit to clear imported-module state.
- [x] Verify the five-minute flow in a real browser at desktop and mobile widths, confirm no overlaps, and check the live health endpoint.
