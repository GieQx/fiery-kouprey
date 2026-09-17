Revise and refine the existing MVP_BLUEPRINT for the SDMX Standards Discovery and Alignment Assistant.

The objective is to address the conceptual and technical weaknesses identified during review while keeping the solution realistic for a 1–2 day hackathon.

The application should not be positioned as a full SDMX validator, compliance checker, or interoperability certification tool.

Instead, position it as a producer-support tool that helps users:

1. discover potentially relevant SDMX reference standards;
2. understand structural and semantic differences;
3. identify possible mappings;
4. assess alignment and interoperability issues;
5. make the final decision through human review.

Update the MVP_BLUEPRINT based on the following requirements.

--------------------------------------------------
1. STRENGTHEN THE CORE PROBLEM
--------------------------------------------------

Clarify that:

- technically valid SDMX does not necessarily mean semantically aligned or interoperable SDMX;
- producers may not know which existing SDMX standard is relevant to their local DSD;
- manual discovery and comparison of standards can be time-consuming;
- structural similarity does not automatically imply statistical equivalence.

The application should therefore support both:

A. Standards Discovery
B. Detailed Alignment Assessment

--------------------------------------------------
2. CHANGE THE INITIAL USER FLOW
--------------------------------------------------

The user should initially upload only the local DSD.

The system should then:

1. parse the local DSD;
2. extract concepts, dimensions, codelists, representations, labels, definitions, annotations, and other available metadata;
3. search a curated Reference Standards Library;
4. identify candidate reference DSDs;
5. explain why each candidate may be relevant;
6. allow the user to select the reference standard;
7. perform detailed alignment assessment;
8. provide findings and suggested actions;
9. require human review;
10. export the reviewed results.

The system must never automatically decide which reference standard is authoritative.

--------------------------------------------------
3. REFERENCE STANDARDS LIBRARY
--------------------------------------------------

Add a curated Reference Standards Library.

Each reference artefact should record at minimum:

- agency ID;
- artefact ID;
- version;
- name;
- description;
- source/provenance;
- domain or subject area;
- date retrieved or registered.

The system should clearly show the exact version of the reference standard used in the comparison.

If no suitable candidate is identified, show:

“No suitable reference standard identified.”

Do not force a match.

For the hackathon MVP, the library can contain only a small number of curated reference DSDs.

--------------------------------------------------
4. CANDIDATE STANDARD DISCOVERY
--------------------------------------------------

Candidate reference standards should be identified using multiple signals.

Use deterministic evidence first:

- exact concept ID overlap;
- exact label/name overlap;
- concept scheme overlap;
- codelist overlap;
- code label overlap;
- structural similarity;
- representation similarity.

AI may then be used to identify semantic relationships that deterministic matching cannot resolve.

Do not use a black-box overall ranking without explanation.

For every candidate standard, show why it was identified, for example:

- 6 exact concept matches;
- 2 shared codelists;
- 3 potential semantic concept matches;
- similar domain metadata.

If candidates are ordered, make the ordering explainable and do not present it as proof that the top candidate is the correct standard.

--------------------------------------------------
5. SEPARATE VALIDITY FROM ALIGNMENT
--------------------------------------------------

Explicitly distinguish:

- invalid SDMX;
- valid SDMX with structural differences;
- semantically equivalent concepts with different representations;
- partial alignment;
- legitimate local extensions;
- missing reference elements;
- genuine semantic conflict;
- unresolved relationships.

Do not label a local DSD as “wrong” simply because it differs from a reference structure.

--------------------------------------------------
6. AVOID A SINGLE COMPLIANCE SCORE
--------------------------------------------------

Do not produce a single overall compliance or alignment score.

Instead show evidence and category-level results such as:

- Structural Alignment
- Concept Alignment
- Codelist Alignment
- Representation Alignment
- Metadata Completeness

The primary output should be findings, not a score.

--------------------------------------------------
7. IMPROVE FINDING CLASSIFICATION
--------------------------------------------------

Use statuses such as:

- Exact Alignment
- Equivalent
- Partial Alignment
- Mapping Required
- Representation Difference
- Local Extension
- Reference-Only Element
- Metadata Gap
- Potential Semantic Correspondence
- Potential Semantic Conflict
- Insufficient Metadata
- Unresolved

Allow “No Action Required” where a difference is intentional and acceptable.

--------------------------------------------------
8. ADDRESS SEMANTIC FALSE POSITIVES
--------------------------------------------------

Do not rely only on concept IDs or labels.

When evaluating semantic similarity, consider where available:

- definition;
- description;
- concept scheme;
- annotations;
- representation;
- codelist;
- code definitions;
- statistical context.

Example:

AGE

must not automatically be considered equivalent if the two structures use different statistical definitions, age concepts, or representations.

If metadata is insufficient, classify the result as:

“Insufficient Metadata”

instead of guessing.

--------------------------------------------------
9. AI TRUSTWORTHINESS
--------------------------------------------------

AI should only be used for unresolved semantic interpretation and explanatory assistance.

AI must NOT be used for deterministic checks.

All AI-assisted findings must show:

- matching method;
- evidence used;
- proposed relationship;
- explanation;
- confidence indicator, if used;
- human review status.

Do not present AI confidence as a statistically calibrated probability.

Treat it only as a similarity or matching signal.

Add wording such as:

“AI-assisted suggestion — expert validation required.”

If the AI service is unavailable, the deterministic comparison must continue normally.

--------------------------------------------------
10. HUMAN REVIEW
--------------------------------------------------

The user must retain final control.

For each AI-assisted or ambiguous finding, allow:

- Accept
- Reject
- Modify
- Mark Unresolved
- Mark No Action Required
- Add Reviewer Note

The application must never automatically finalize a semantic mapping.

--------------------------------------------------
11. ACTIONABLE RECOMMENDATIONS
--------------------------------------------------

The solution should not stop at identifying differences.

Where possible, recommend an action.

Example:

Finding:
SEX uses different code values.

Local:
1 = Male
2 = Female
9 = Total

Reference:
M = Male
F = Female
T = Total

Result:
Concept aligned.
Code mapping required.

Suggested action:
Create a code mapping.

Suggested mapping:
1 → M
2 → F
9 → T

Recommendations must remain proposals requiring human confirmation.

--------------------------------------------------
12. TRACEABILITY AND PROVENANCE
--------------------------------------------------

Every finding must be traceable.

Record:

- local agency;
- local artefact ID;
- local version;
- local element;
- reference agency;
- reference artefact ID;
- reference version;
- reference element;
- source/provenance;
- matching method;
- deterministic or AI-assisted;
- evidence used;
- timestamp;
- reviewer decision;
- reviewer note.

--------------------------------------------------
13. DEFINE THE CLAIMS OF THE MVP CAREFULLY
--------------------------------------------------

The MVP must NOT claim to provide:

- complete SDMX interoperability certification;
- authoritative standards selection;
- full SDMX validation;
- regulatory compliance assessment;
- automatic harmonization.

Instead, describe the output as:

“SDMX Standards Discovery and Alignment Assessment”

or:

“Producer-assisted structural and semantic alignment review.”

--------------------------------------------------
14. RETAIN SIMPLE HACKATHON ARCHITECTURE
--------------------------------------------------

Keep Streamlit as the main application framework.

Preferred architecture:

Streamlit UI
   ↓
SDMX Parser
   ↓
Normalized Metadata Model
   ↓
Reference Standards Discovery
   ↓
Deterministic Comparator
   ↓
Optional AI Semantic Matcher
   ↓
Human Review
   ↓
JSON / CSV Export

Do not introduce unnecessary React, FastAPI, authentication, or production infrastructure unless clearly required.

--------------------------------------------------
15. RETAIN CONFIGURABLE LLM PROVIDERS
--------------------------------------------------

The application should support:

- OpenAI API
- Ollama

Use a provider abstraction so that the application logic is not tied to one model.

Example settings:

LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=...

or

LLM_PROVIDER=ollama
OLLAMA_BASE_URL=...
OLLAMA_MODEL=...

If no LLM is configured, the application must still support deterministic discovery and comparison.

--------------------------------------------------
16. ADD A SMALL BENCHMARK / TEST SET
--------------------------------------------------

Add an expert-validated sample test set for the hackathon.

Include known examples of:

- exact match;
- equivalent concept with different ID;
- same concept with different codes;
- partial semantic match;
- local extension;
- missing reference element;
- false semantic similarity;
- insufficient metadata.

Use this test set to demonstrate that the system can distinguish obvious matches from ambiguous cases.

--------------------------------------------------
17. KEEP THE MVP SMALL
--------------------------------------------------

For the hackathon, limit the MVP to:

- one uploaded local DSD;
- a small curated library of reference standards;
- 3–5 candidate reference DSDs maximum;
- one selected reference for detailed comparison;
- concept/dimension/codelist-level analysis;
- deterministic matching;
- optional AI semantic assistance;
- human review;
- JSON/CSV export.

Do not expand into a full registry or governance platform.

--------------------------------------------------
18. REVISE THE MVP BLUEPRINT SECTIONS
--------------------------------------------------

Revise the following sections accordingly:

1. Executive Summary
2. Problem Statement
3. Opportunity / Gap Addressed
4. Objectives
5. Scope
6. Out of Scope
7. Core User Flow
8. User Stories
9. Functional Requirements
10. Reference Standards Library
11. Standards Discovery Logic
12. Detailed Alignment Logic
13. AI Requirements
14. Trustworthiness and Human Oversight
15. Finding Classification
16. Actionable Recommendation Logic
17. Traceability and Provenance
18. Architecture
19. Data Model
20. UI Screens
21. Export Format
22. Acceptance Criteria
23. Test Cases
24. Hackathon Demo Scenario
25. Success Metrics
26. Risks and Limitations
27. Post-Hackathon Roadmap

Also include a final section:

“Key Design Principles”

Include at least:

- Valid SDMX does not always mean interoperable SDMX.
- Structural similarity does not imply semantic equivalence.
- AI recommends; experts decide.
- Evidence must accompany recommendations.
- Differences are not automatically errors.
- Reference standards must be versioned and traceable.
- No suitable match is a valid result.
- Deterministic checks come before AI.
- Local extensions may be legitimate.
- The tool assists harmonization; it does not certify compliance.

Do not start implementation.

Only revise and refine the MVP_BLUEPRINT.