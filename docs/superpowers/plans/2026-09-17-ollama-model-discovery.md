# Ollama Model Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Automatically discover installed Ollama models and let the user select one without typing its name.

**Architecture:** Add model discovery to the Ollama adapter through `/api/tags`, then expose a cached Streamlit helper that renders discovered models or a manual fallback. Existing configuration, matcher creation, and deterministic comparison remain unchanged.

**Tech Stack:** Python, httpx, Streamlit, pytest, Streamlit AppTest

---

### Task 1: Ollama Model Discovery

**Files:**
- Modify: `sdmx_alignment/semantic_matcher/ollama_provider.py`
- Test: `tests/test_semantic_matcher.py`

- [x] **Step 1: Write failing discovery tests**

Add tests that mock `/api/tags`, assert model names are returned in response order, and assert malformed or unavailable responses raise `ProviderError`.

- [x] **Step 2: Verify the tests fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_semantic_matcher.py -q`

Expected: failure because `OllamaProvider.list_models` does not exist.

- [x] **Step 3: Implement the adapter method**

Add `list_models()` to call `/api/tags`, validate `models` as a list, collect non-empty `name` values, and wrap transport or payload errors in `ProviderError("Unable to discover Ollama models")`.

- [x] **Step 4: Verify adapter tests pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_semantic_matcher.py -q`

Expected: all semantic matcher tests pass.

### Task 2: Streamlit Model Selector

**Files:**
- Modify: `app.py`
- Modify: `sdmx_alignment/config.py`
- Test: `tests/test_config.py`
- Test: `tests/test_app.py`

- [x] **Step 1: Write failing selector tests**

Add a pure `choose_ollama_model(models, configured)` test in `tests/test_config.py` proving that an installed configured model wins, otherwise the first discovered model wins, and an empty list returns an empty string.

- [x] **Step 2: Verify the tests fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config.py -q`

Expected: import failure because the selection helper does not exist.

- [x] **Step 3: Implement discovery UI**

Add the pure selection helper to `sdmx_alignment/config.py`. Add a cached `discover_ollama_models(endpoint, timeout)` helper to `app.py`, a selectbox for discovered models, a refresh button that clears the cache, and a manual text field only when discovery fails or returns no models.

- [x] **Step 4: Verify UI tests pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config.py tests/test_app.py -q`

Expected: all app tests pass.

### Task 3: Integration Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-09-17-ollama-model-discovery.md`

- [x] **Step 1: Run the complete suite**

Run: `.venv/Scripts/python.exe -m pytest -q`

Expected: all tests pass.

- [x] **Step 2: Run a real model-discovery smoke test**

Instantiate `OllamaProvider` with `http://127.0.0.1:11434`, call `list_models()`, and verify `qwen2.5:0.5b-instruct-q4_0` is returned.

- [x] **Step 3: Copy changed files to the live workshop directory**

Copy the provider, app, tests, design, and plan while preserving unrelated live files.

- [x] **Step 4: Verify the live Streamlit health endpoint**

Request `http://127.0.0.1:8501/_stcore/health` and expect HTTP 200 with body `ok`.
