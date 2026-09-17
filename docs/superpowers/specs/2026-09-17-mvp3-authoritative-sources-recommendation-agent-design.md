# MVP3 Authoritative Sources and Recommendation Agent Design

## Objective

Revise the SDMX Alignment Assistant so its primary workflow starts with a user-uploaded SDMX DataStructure or resolvable Dataflow, discovers structural standards from authoritative sources with the SDMX Global Registry as the default, optionally considers a selected methodological standard, and produces evidence-grounded recommendations under human control.

The revision must retain the working Streamlit application, safe parser, deterministic comparator, modular LLM providers, review workflow, controlled transformation, validation, and audit exports.

## Scope

The MVP will:

- remove the Load Local Demo and Load BOP Demo buttons from the production UI;
- retain sample XML files as development and automated-test fixtures;
- use a cache-first source layer with an optional live SDMX Global Registry refresh;
- represent the Global Registry, IMF, OECD, Eurostat, and curated repositories as trusted sources without coupling discovery to one provider;
- allow separate selection of one structural reference and one applicable methodological standard;
- generate deterministic recommendations first and bounded AI recommendations only when an LLM is available;
- reject ungrounded AI identifiers, artefacts, requirements, and citations;
- retain the existing five-state human-review workflow;
- permit only finalized, reviewer-approved structured actions to modify XML;
- include advisory recommendations in the audit package without silently changing XML.

The MVP will not become a complete registry crawler, a full SDMX validator, a methodology corpus search engine, or an autonomous DSD editor.

## Current Components and Changes

| Component | Decision |
|---|---|
| Streamlit UI | Retain; remove demo buttons and add source status, optional refresh, methodology selection, and recommendation evidence. |
| SDMX parser | Retain, including Dataflow-to-DSD resolution. |
| Deterministic comparator | Retain as the first analysis stage. |
| LLM provider abstraction | Retain for OpenAI, Ollama, and deterministic fallback. |
| Discovery scoring | Retain and extend with source trust and availability metadata. |
| Curated reference library | Retain as the offline cache and fallback. |
| Human review | Retain Accept, Reject, Modify, Mark Unresolved, and No Action Required. |
| Transformation | Retain controlled actions; do not allow free-form AI XML editing. |
| Validation and exports | Retain and extend with recommendation and source provenance. |

## Demo Removal

The two demo buttons are UI-only conveniences. Their dependencies are sample files and Streamlit tests that click the buttons. Removing the buttons does not affect parsing, discovery, comparison, review, transformation, or validation.

The XML samples remain in `samples/` and `tests/fixtures/`. Test setup will load them through pure functions or the upload control. The production UI will not expose the BOP automatic-decision accelerator. This prevents an uploaded structure from being confused with a pre-scripted demonstration.

## Reference Source Architecture

### Source Contract

A reference source supplies normalized `ReferenceStandard` records and, when available, SDMX-ML bytes for a selected artefact. Each record includes:

- source ID and source name;
- source type;
- trust classification;
- agency ID, artefact ID, and version;
- artefact name and description;
- canonical source URL;
- retrieval timestamp;
- retrieval mode: `live`, `cache`, or `curated`;
- availability state and diagnostic message;
- related methodological citations.

The application consumes the normalized contract and does not depend directly on provider-specific response shapes.

### Sources

The source catalog includes:

1. `SDMX_GLOBAL_REGISTRY`, the default structural source at `https://registry.sdmx.org/sdmx/v2/`.
2. `IMF`, an authoritative institutional source and methodology issuer.
3. `OECD`, an authoritative institutional source and methodology issuer.
4. `EUROSTAT`, an authoritative institutional source and methodology issuer.
5. `CURATED_LOCAL`, the offline workshop and test fallback.

IMF, OECD, and Eurostat can appear as agencies in the Global Registry or as future provider adapters. The source catalog makes that distinction explicit and avoids hard-coding discovery to one endpoint.

### Cache-First Flow

1. Load the curated manifest and cached authoritative artefacts immediately.
2. Mark every candidate with its source and retrieval mode.
3. Rank authoritative Global Registry cache entries before curated workshop and synthetic fixtures when relevance evidence is otherwise comparable.
4. Offer an explicit `Refresh from Global Registry` command.
5. On refresh, call the official structure endpoint with a short timeout and bounded response size.
6. Parse returned DSD metadata and update only the browser-session catalog.
7. If refresh fails, retain cached entries and show a non-blocking fallback message.

Live refresh will never erase a working cache or block deterministic comparison.

### Live Query Boundary

The adapter will use the Global Registry's SDMX REST structure service. Initial live support is intentionally bounded to exact or agency-scoped DataStructure retrieval rather than downloading every registry artefact. Requests use the configured endpoint, timeout, SDMX-ML response type, and safe XML parser. A selected live result must be fetched with enough references to support structural comparison.

Official service documentation: `https://registry.sdmx.org/webservice/structure.html`.

## Methodological Standards

Methodological standards are separate from structural DSDs. A methodology catalog stores an identifier, title, issuer, version, description, canonical URL, publication date, applicable domains, and a small set of curated principles with citations.

After structural-reference selection, the UI offers only methodologies related to that reference or domain, plus `No methodological standard selected`. Selecting a methodology supplies bounded evidence to the recommendation engine; it does not imply that the DSD is officially compliant with that methodology.

For the BOP workflow, BPM7 and BPM6 remain clearly identified as IMF methodological standards, while the selected DSD retains its actual structural issuer and provenance.

## Recommendation Model

Each recommendation is a structured record containing:

- recommendation ID and linked finding ID;
- local element ID, label, description, and source path when available;
- reference element ID, label, description, and source path when available;
- methodological principle ID and text when applicable;
- proposed recommendation;
- rationale;
- evidence statements;
- origin: `deterministic` or `ai`;
- provider and model for AI results;
- authoritative citations selected from an allow-list;
- recommendation category;
- confidence when provided;
- grounding status;
- review status, note, reviewer, and review timestamp;
- structured transformation action when one is available.

Categories include missing dimension, missing attribute, concept mapping, code mapping, representation difference, missing definition, ambiguous terminology, metadata improvement, local extension, and insufficient information.

## Deterministic Recommendations

The existing comparison findings become deterministic recommendations before any LLM call. Their local and reference evidence comes directly from parsed source paths, representations, codelists, and code mappings. Missing elements and representation differences receive explicit recommendations and reasons generated from fixed templates.

Deterministic findings remain available when no LLM is configured.

## AI Standards Recommendation Agent

The agent runs only after structural-reference and methodology selection. It receives a bounded JSON context containing:

- the selected finding;
- the local and reference elements already identified by deterministic comparison;
- allowed local and reference IDs;
- selected methodological principles;
- allowed citation IDs and URLs;
- explicit instructions to return structured JSON and to abstain when evidence is insufficient.

The agent focuses on ambiguous names, statistical meaning conflicts, unclear code labels, inconsistent representations, missing definitions, local terminology, downstream misinterpretation risk, and missing context.

The output validator rejects a recommendation when it:

- names a local or reference element outside the allow-list;
- cites a source outside the selected trusted-source allow-list;
- claims a methodological requirement absent from the supplied principles;
- proposes a code or codelist absent from the selected structures;
- omits evidence or rationale;
- cannot be parsed as the required structured response.

Rejected, failed, unavailable, or weakly grounded AI output becomes exactly:

`Insufficient information for a reliable recommendation.`

The provider never receives API credentials, whole unrelated structures, or unselected methodology content.

## Human Review and Transformation

Every reviewable recommendation supports:

- Accept;
- Reject;
- Modify;
- Mark Unresolved;
- No Action Required.

AI recommendations never edit XML directly. The existing alignment plan remains the transformation gate. A recommendation can contribute to XML only when it maps to a supported structured action and the reviewer accepts or modifies it before finalizing the plan.

The supported XML-changing actions remain `MAP` and `ADD_MISSING_ELEMENT`. `REUSE` and `KEEP_LOCAL_EXTENSION` are recorded but do not mutate XML. Metadata and ambiguity recommendations without a safe structured XML action are advisory: approval records them in the audit report but does not manufacture a description, annotation, concept, code, codelist, or citation.

## User Interface Flow

1. Upload an SDMX DataStructure or resolvable Dataflow.
2. Display the parsed or resolved local structure and provenance.
3. Display source status with SDMX Global Registry identified as the default and cached/live state shown.
4. Optionally refresh the registry.
5. Show ranked structural candidates with agency, ID, version, name, source, trust, retrieval mode, and evidence.
6. Select one structural reference.
7. Select an applicable methodology or explicitly select none.
8. Run deterministic comparison automatically.
9. Run the AI Recommendation Agent explicitly when an LLM is ready; otherwise retain deterministic recommendations and flag semantic items for review.
10. Review recommendations and finalize the approved change set.
11. Generate the revised DSD using approved structured actions.
12. Display technical checks, reference alignment, before/after metrics, and downloadable XML, JSON, and CSV evidence.

## Error Handling

- Invalid XML: show the existing safe parse error.
- Dataflow with an unavailable referenced DSD: identify the exact missing agency, ID, and version.
- Registry timeout, HTTP error, oversized response, or invalid XML: preserve cache and show fallback status.
- No reference candidate: allow manual selection from available cached entries.
- No methodology: continue with structural comparison and label methodology evidence unavailable.
- No LLM: continue deterministically and mark semantic recommendations for human review.
- Invalid LLM output: replace it with the required insufficient-information result and retain diagnostic details only in safe application state.

## Audit and Trust Signals

Exports include:

- uploaded file identity and Dataflow resolution, if used;
- structural reference source, retrieval mode, URL, and timestamp;
- selected methodological standard and citations;
- deterministic and AI recommendation counts;
- model/provider identifiers without credentials;
- grounding validation result;
- human decisions and notes;
- finalized reviewer and timestamp;
- transformation actions and outcomes;
- technical validation and reference-alignment disclaimers.

The UI must continue to state that the MVP provides alignment assistance, not official SDMX certification or methodological compliance determination.

## Testing and Acceptance Criteria

1. The production UI contains no Load Local Demo or Load BOP Demo buttons.
2. Sample and BOP fixtures remain usable through tests and the upload control.
3. `DSD_BOP@DF_BOP.xml` resolves its exact DSD reference from the cache.
4. The Global Registry is displayed as the primary source and each candidate shows source and retrieval mode.
5. Registry refresh success adds normalized session entries without deleting cached entries.
6. Registry refresh failure leaves discovery usable and reports cached fallback.
7. IMF, OECD, Eurostat, and curated-local source definitions are represented independently of the Global Registry adapter.
8. Structural and methodological selections remain separate.
9. Deterministic recommendations work with no LLM.
10. Grounded AI output retains only allowed IDs and citations.
11. Invented concepts, codes, codelists, artefacts, requirements, or citations are rejected.
12. Insufficient evidence produces the exact required abstention sentence.
13. All five review states persist in session state and exports.
14. AI cannot bypass plan finalization or transformation controls.
15. Existing technical checks and before/after reporting continue to pass.
16. The complete automated suite and a real-browser upload-to-export workflow pass before release.

## Delivery Strategy

Implementation will proceed in test-driven vertical slices:

1. remove demo UI dependencies while preserving fixtures;
2. introduce source models and cache-first aggregation;
3. add the bounded Global Registry adapter and graceful fallback;
4. add methodology selection;
5. add recommendation models and deterministic recommendation generation;
6. add the grounded AI agent and output validator;
7. integrate review, audit exports, and Streamlit views;
8. run full automated and browser verification before syncing the live project.
