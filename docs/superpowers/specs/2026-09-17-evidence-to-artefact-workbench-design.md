# Evidence-to-Artefact SDMX Workbench Design

## Objective

Revise the existing Streamlit application into an AI-Assisted SDMX Standards Discovery, Alignment, and Validation Workbench. The MVP must answer a producer's complete question: which reference may be relevant, what differs, what should change, why it matters, and whether the reviewed revision passes scoped technical checks and aligns better.

The application assists producers. It does not certify compliance, select an authoritative standard on the user's behalf, or perform fully automated harmonization.

## Winning Demo Narrative

The primary demonstration uses Balance of Payments and follows one evidence-to-artefact path:

1. Load a synthetic local BOP DSD with deliberate, documented alignment issues.
2. Discover up to five curated candidates and show why each was suggested.
3. Select the workshop BOP structural reference explicitly.
4. Distinguish the structural reference from IMF BPM methodology and shared SDMX artefacts.
5. Run deterministic comparison before optional AI semantic assistance.
6. Review proposed changes with local evidence, reference evidence, source, reason, and method.
7. Accept, modify and approve, reject, mark unresolved, or mark no action required.
8. Finalize an approved change set with reviewer identity and notes.
9. Generate revised XML deterministically from the original XML plus approved structured changes.
10. Run scoped technical checks and recompare the revision with the same reference.
11. Show before-and-after metrics and export the revised XML, change log, and audit package.

## Curated Source Model

Every catalog record has an artefact type, issuer, identity/version, description, provenance, source URL, retrieval date, and related standards.

The demo keeps these source classes separate:

- `structural_reference`: `SDMXWS:DSD_BOP(1.0)`, supplied by the workshop. It is a demonstration structural artefact and must not be presented as an IMF DSD.
- `methodological_standard`: IMF Balance of Payments and International Investment Position Manual, seventh edition (BPM7), released in 2025.
- `methodological_standard`: IMF Balance of Payments and International Investment Position Manual, sixth edition (BPM6), published in 2010.
- `shared_sdmx_artefact_source`: SDMX Global Registry and SDMX cross-domain codelists.

Methodological standards provide context and citations but are never passed to the structural comparator as if they were DSDs. Discovery candidates without sufficient evidence are omitted, and an empty result is valid.

## Architecture

The existing modules remain the foundation:

```text
Streamlit UI
  -> secure SDMX parser and normalized metadata
  -> curated standards catalog and discovery engine
  -> explicit producer reference selection
  -> deterministic comparator
  -> optional provider-neutral AI semantic assistant
  -> human review and approved change set
  -> deterministic XML transformation engine
  -> scoped technical validation engine
  -> revised-reference comparison
  -> before/after report and audit exporters
```

New transformation, validation, and audit modules must remain independent of OpenAI and Ollama. If no LLM is available, deterministic discovery, comparison, review, generation, validation, and export continue to work.

## Discovery and Comparison

Discovery analyzes DSD identity, names, descriptions, dimensions, attributes, concept references, codelists, code labels, representations, annotations, and available metadata. Candidate cards show evidence counts and examples, source class, provenance, version, issuer, source links, and why suggested.

Comparison order is:

1. Exact component ID.
2. Exact concept reference.
3. Exact normalized label.
4. Exact codelist and code evidence.
5. Curated known mapping.
6. Lexical similarity.
7. Optional AI semantic similarity.
8. Unresolved.

The comparator will expose judge-readable classifications including exact alignment, equivalent, partial alignment, mapping required, representation difference, local extension, reference-only element, metadata gap, potential semantic correspondence, potential semantic conflict, insufficient metadata, unresolved, and no action required. Differences are not automatically errors.

## Recommendation Evidence

Every actionable finding displays:

- local and reference IDs, labels, definitions, concept references, representations, and relevant codes;
- proposed action and a concrete reason why;
- interoperability impact;
- supporting structural reference and related methodology citations;
- matching method and deterministic evidence;
- AI provider/model and a non-calibrated semantic similarity signal when AI assisted;
- the notice `AI-assisted suggestion - expert validation required.`

AI may interpret semantics and explain candidates. It may not create standards, codelists, codes, XML, approvals, or compliance claims.

## Human Review

Review choices are accept, modify and approve, reject, unresolved, and no action required. A reviewer note is available for every finding. Modified decisions retain both the original recommendation and final approved structured action.

Exact deterministic findings need no change and are included in the audit as no action required. Only accepted or modified-and-approved actions enter the change set. Finalization requires reviewer identity and freezes the change set until explicitly reopened.

## Controlled Transformation

The original uploaded bytes remain immutable and downloadable. The transformer works on a parsed copy and accepts only typed approved actions:

- rename or map a local component to a selected reference component;
- update its concept identity and representation/codelist reference from that reference component;
- apply an explicit reviewed code mapping;
- add an approved missing component by cloning its exact reference structure and required referenced artefacts;
- retain a local extension unchanged;
- record no action without changing XML.

The MVP does not delete components, generate free-form XML, infer new codes, or apply rejected/unresolved actions. Each executed action returns a success or failure result. Any failed action leaves the original preserved and prevents a technical PASS claim.

## Validation and Reassessment

Validation is split into two visibly separate panels.

### MVP SDMX Technical Checks

- XML remains well formed with DTD and external entities disabled.
- The revised message reparses through the application parser.
- DataStructure identity is present.
- Component IDs are unique within their component lists.
- dimension positions are valid and non-duplicated;
- codelist references required by transformed components resolve in the generated message;
- every approved action has a corresponding successful transformation result.

The result is `PASS` or `FAIL` and always states that these checks are not official SDMX certification or full schema validation.

### Reference Alignment Assessment

The revised structure is compared against the same selected reference. The result is `ALIGNED`, `PARTIALLY ALIGNED`, or `ISSUES REMAIN`, accompanied by outstanding mappings, unresolved semantic issues, retained local extensions, and validation errors. Structural alignment is not represented as proof of complete real-world interoperability.

## Before and After

The final dashboard compares the original and revised summaries. It attributes improvements separately to deterministic matching, AI-assisted suggestions, and human-approved transformations. It shows at minimum exact/equivalent alignments, mappings, missing/reference-only elements, unresolved issues, retained extensions, executed changes, and technical validation outcome.

No fabricated time-saving number is shown. A measured session duration may be displayed only when recorded by the application.

## Audit and Exports

The audit record includes original and revised identities, selected reference identity and provenance, related methodological sources, findings, methods, evidence, AI provider/model, AI explanation, reviewer decision/note, approved action, transformation result, validation result, and UTC timestamps.

Exports are:

- original XML;
- revised XML;
- JSON evidence and audit package;
- CSV decision and change log;
- JSON validation and before/after report.

## Streamlit Experience

The app remains an operational workbench rather than a marketing page. The workflow is organized into three compact stages:

1. `Discover`: upload/demo, local DSD profile, candidates, source details, explicit selection.
2. `Decide`: summary metrics, findings, detailed evidence, human review, approved change set.
3. `Generate and Prove`: revised XML, validation, re-comparison, before/after, audit exports.

The UI reuses current controls and restrained workshop colors. It avoids nested cards, keeps evidence scannable, and makes the current stage and blocking requirements obvious.

## MVP Boundaries

Deferred continuation paths are official XSD/FMR certification, live registry writes, unrestricted web search, arbitrary XML generation, dataset-level validation, multiple simultaneous local DSDs, and broad multi-domain transformation. The catalog and provider interfaces remain extensible for registry APIs, institutional catalogs, mapping repositories, and production SDMX workflows.

## Verification

Tests cover catalog provenance, discovery source separation, comparison classifications, every review decision, change-set construction, deterministic transformation, preservation of original bytes, validation failures, revised-reference comparison, before/after metrics, audit completeness, no-LLM operation, and the complete Streamlit demonstration flow.

The final browser verification runs the five-minute BOP path at desktop and mobile widths and confirms that controls, evidence, downloads, and status panels render without overlap.
