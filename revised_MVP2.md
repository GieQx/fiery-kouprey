Revise the existing hackathon application into an:

AI-Assisted SDMX Standards Discovery, Alignment, and Validation Workbench

The current application already supports local DSD analysis and comparison. Refine it so the workflow is stronger, more trustworthy, more useful to statistical producers, and better aligned with the hackathon judging criteria.

The revised application should support the following end-to-end workflow:

1. Upload a Local DSD
2. Analyze the uploaded DSD
3. Suggest relevant international statistical standards and reference DSDs
4. Show authoritative citations and sources for each suggested standard
5. Let the user select the standard they want to use
6. Compare the local DSD with the selected reference
7. Propose structural and semantic changes
8. Explain the reason for every proposed change
9. Require human approval before applying any change
10. Generate a revised SDMX artefact using only approved changes
11. Validate the revised artefact
12. Test its alignment with the selected reference DSD
13. Present a final audit trail and before-and-after results

--------------------------------------------------
1. CORE USE CASE
--------------------------------------------------

The application should answer this producer question:

“I already have a local DSD. Which international standards may be relevant, how does my DSD differ from the selected standard, what should I change, why should I change it, and will the revised artefact be technically valid and better aligned?”

Do not position the application as:
- a fully automated harmonization system;
- a compliance certification system;
- an authoritative standards selector.

Position it as:
- a producer-support tool;
- an AI-assisted standards discovery tool;
- an alignment assessment tool;
- a human-controlled DSD transformation workflow.

--------------------------------------------------
2. INTERNATIONAL STANDARDS DISCOVERY
--------------------------------------------------

After the local DSD is uploaded, analyze:

- DSD name and description;
- dimensions;
- concepts;
- concept schemes;
- codelists;
- code labels;
- representations;
- annotations;
- available metadata.

Use this information to suggest potentially relevant international standards.

Examples may include:

- IMF Balance of Payments standards;
- BPM6;
- BPM7;
- IMF reference DSDs;
- OECD Benchmark Definition of Foreign Direct Investment;
- OECD reference DSDs;
- other curated SDMX standards available in the application.

The system must distinguish between:

A. Structural SDMX Reference
Example:
IMF BOP DSD

B. Statistical / Methodological Standard
Example:
BPM6 or BPM7

C. AI Interpretation
Example:
“This concept appears related to direct investment because…”

Do not treat methodological manuals and DSDs as the same type of artefact.

--------------------------------------------------
3. AUTHORITATIVE SOURCES AND CITATIONS
--------------------------------------------------

Every suggested international standard must display:

- standard name;
- issuing organization;
- version or edition;
- short description;
- authoritative source;
- source URL;
- date/version information where available;
- why the standard was suggested.

Example:

IMF Balance of Payments / IIP Reference DSD

Why suggested:
- external sector concepts detected;
- overlap with balance of payments dimensions;
- direct investment terminology found.

Authoritative source:
International Monetary Fund

Related methodology:
BPM6 / BPM7

The application must not invent standards, codes, citations, versions, or URLs.

For the hackathon MVP, use a curated catalog of authoritative standards instead of unrestricted web search.

--------------------------------------------------
4. USER SELECTS THE STANDARD
--------------------------------------------------

The AI must not automatically decide which standard is authoritative.

Show a small set of relevant candidate standards.

For each candidate, show evidence such as:

- exact concept overlaps;
- shared codelists;
- shared code labels;
- domain similarity;
- structural similarity;
- semantic similarity.

The user must explicitly select the reference standard to use.

If no suitable standard is identified, show:

“No suitable reference standard identified.”

Do not force a match.

--------------------------------------------------
5. DETAILED ALIGNMENT ASSESSMENT
--------------------------------------------------

After the user selects a reference standard, compare the local DSD with the reference.

Compare at minimum:

- dimensions;
- dimension order;
- concepts;
- concept references;
- codelists;
- code values;
- code labels;
- representations;
- attributes;
- measures;
- mandatory/optional components;
- definitions;
- annotations;
- available metadata.

Use deterministic comparison first.

Matching order should be:

1. exact ID match;
2. exact concept reference match;
3. exact normalized label match;
4. exact codelist/code match;
5. known mapping;
6. lexical similarity;
7. AI-assisted semantic similarity;
8. unresolved.

Do not use AI for checks that can be performed deterministically.

--------------------------------------------------
6. FINDING CLASSIFICATION
--------------------------------------------------

Use clear statuses such as:

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
- No Action Required

Do not automatically describe differences as errors.

A local extension may be legitimate.

--------------------------------------------------
7. PROPOSED CHANGES
--------------------------------------------------

For every proposed change, show:

LOCAL
- element ID;
- label;
- definition;
- current representation;
- current codes if applicable.

REFERENCE
- element ID;
- label;
- definition;
- representation;
- reference codes.

PROPOSED ACTION
Examples:
- rename/map concept;
- map codes;
- change representation;
- add missing component;
- retain local extension;
- no action required.

REASON WHY
Explain:
- what differs;
- why it matters;
- how it affects alignment/interoperability;
- which reference standard supports the recommendation.

Also show:

- matching method;
- deterministic or AI-assisted;
- evidence used;
- confidence signal if AI-assisted.

--------------------------------------------------
8. AI TRUSTWORTHINESS
--------------------------------------------------

AI must only assist with:

- semantic interpretation;
- concept matching;
- explaining differences;
- recommending possible mappings;
- generating understandable reasons.

AI must NOT:

- invent SDMX codes;
- invent codelists;
- invent authoritative standards;
- silently modify the DSD;
- automatically approve mappings;
- declare a structure compliant solely from semantic similarity.

Every AI-generated recommendation must display:

“AI-assisted suggestion — expert validation required.”

If confidence is displayed, do not present it as a statistically calibrated probability.

Treat it only as a semantic similarity signal.

--------------------------------------------------
9. HUMAN-IN-THE-LOOP REVIEW
--------------------------------------------------

For each recommendation, provide:

- Accept
- Reject
- Modify
- Mark Unresolved
- Mark No Action Required
- Add Reviewer Note

Only accepted or modified-and-approved changes may be applied to the final artefact.

The system must record the reviewer decision.

--------------------------------------------------
10. FINAL ARTEFACT GENERATION
--------------------------------------------------

Generate the revised DSD only from approved recommendations.

Use this workflow:

Original DSD
    ↓
Approved Change Set
    ↓
Transformation Engine
    ↓
Revised DSD

The transformation must not depend on free-form AI generation of XML.

Prefer deterministic generation/modification based on approved structured changes.

Preserve the original DSD.

Generate:

- revised SDMX artefact;
- change log;
- accepted changes;
- rejected changes;
- unresolved issues.

--------------------------------------------------
11. VALIDATION
--------------------------------------------------

After generating the revised DSD, perform two separate assessments:

A. SDMX Technical Validation
Check whether the generated artefact is structurally and technically valid.

B. Reference Alignment Assessment
Compare the revised DSD against the selected reference standard.

Do not simply show:

“Interoperable: Yes/No”

Instead show something like:

SDMX Technical Validity:
PASS / FAIL

Reference Alignment:
ALIGNED / PARTIALLY ALIGNED / ISSUES REMAIN

Outstanding Code Mappings:
X

Unresolved Semantic Issues:
X

Local Extensions Retained:
X

Validation Errors:
X

Clearly explain that structural/reference alignment does not guarantee complete real-world interoperability.

--------------------------------------------------
12. BEFORE AND AFTER VIEW
--------------------------------------------------

Add a strong before-and-after summary for hackathon demonstration.

Example:

BEFORE
- 6 exact matches
- 5 unresolved concepts
- 4 code mismatches
- 2 missing reference elements

AFTER
- 10 exact/equivalent alignments
- 3 approved code mappings
- 1 local extension retained
- 0 unresolved critical issues
- generated DSD passes technical validation

Show which improvements resulted from:
- deterministic matching;
- AI-assisted recommendations;
- human decisions.

--------------------------------------------------
13. AUDIT TRAIL
--------------------------------------------------

Every action must be traceable.

Record:

- original local DSD;
- local agency ID;
- artefact ID;
- version;
- selected reference standard;
- reference agency;
- reference artefact ID;
- reference version;
- source/citation;
- finding;
- matching method;
- evidence;
- AI model/provider if used;
- AI explanation;
- reviewer decision;
- approved change;
- transformation result;
- validation result;
- timestamp.

--------------------------------------------------
14. HACKATHON CRITERIA
--------------------------------------------------

Make the design explicitly support these judging criteria:

TRUSTWORTHINESS
- no invented codes or standards;
- curated authoritative references;
- deterministic checks before AI;
- human approval required;
- original artefact preserved;
- AI failure must not break deterministic functionality.

TRANSPARENCY
- show why each standard was suggested;
- show source URLs and versions;
- show every proposed change;
- show whether the finding came from deterministic logic or AI;
- maintain an audit trail;
- keep the workflow reproducible.

IMPACT
- show measurable before-and-after improvement;
- show reduction in unresolved alignment issues;
- optionally show comparison time before vs AI-assisted workflow.

USEFULNESS
- address the producer pain of:
  “Which standard should I use?”
  “What should I change?”
  “Why should I change it?”
  “Can I generate a revised DSD safely?”

CONTINUATION
Design the MVP so it can later support:
- more curated standards;
- SDMX registries;
- IMF / OECD APIs;
- additional statistical domains;
- institutional standards catalogs;
- mapping repositories;
- integration with .Stat Suite or production SDMX workflows.

--------------------------------------------------
15. MVP SCOPE
--------------------------------------------------

Keep the hackathon MVP realistic.

Limit the scope to:

- one uploaded local DSD;
- a small curated catalog of international standards;
- maximum 3–5 suggested standards;
- one selected reference DSD;
- concept/dimension/codelist analysis;
- deterministic comparison;
- AI-assisted semantic recommendations;
- human review;
- approved change set;
- revised DSD generation;
- technical validation;
- reference alignment assessment;
- JSON/CSV audit export.

Prefer one statistical domain for the primary demo.

Balance of Payments / External Sector Statistics is a good candidate because it can demonstrate:

- reference DSD;
- methodological standard;
- multiple related concepts;
- code mappings;
- explainable alignment recommendations.

--------------------------------------------------
16. TECHNICAL ARCHITECTURE
--------------------------------------------------

Keep the existing Streamlit-based MVP architecture.

Suggested architecture:

Streamlit UI
   ↓
SDMX Parser
   ↓
Normalized Metadata Model
   ↓
Standards Discovery Engine
   ↓
Curated Standards Catalog
   ↓
User Selects Reference
   ↓
Deterministic Alignment Engine
   ↓
AI Semantic Assistant
   ↓
Human Review
   ↓
Approved Change Set
   ↓
DSD Transformation Engine
   ↓
Validation Engine
   ↓
Final Artefact + Audit Trail

Retain configurable LLM support for:

- OpenAI API
- Ollama

The application must still work without an LLM for deterministic functions.

--------------------------------------------------
17. IMPORTANT DESIGN PRINCIPLES
--------------------------------------------------

Include and follow these principles throughout the application:

- Valid SDMX does not always mean interoperable SDMX.
- Structural similarity does not guarantee semantic equivalence.
- Methodological standards and DSDs are different artefact types.
- AI recommends; experts decide.
- Every recommendation must have evidence.
- Differences are not automatically errors.
- Local extensions may be legitimate.
- No suitable standard is a valid result.
- Deterministic checks must come before AI.
- Only approved changes are applied.
- Final XML generation should be deterministic.
- Reference artefacts must be versioned and traceable.
- The tool assists standards alignment; it does not certify regulatory compliance.

--------------------------------------------------
18. REVISE THE APPLICATION
--------------------------------------------------

Update the existing application and supporting documentation accordingly.

Prioritize the following screens:

1. Upload Local DSD
2. Suggested International Standards
3. Standard Details and Authoritative Sources
4. Alignment Assessment
5. Proposed Changes with “Reason Why”
6. Human Review
7. Approved Change Summary
8. Generate Revised DSD
9. Validation Results
10. Before-and-After Comparison
11. Audit Trail / Export

Do not redesign working components unnecessarily.

Reuse the current parser, comparator, UI, LLM abstraction, and Streamlit structure where possible.

Refactor only where necessary to support the revised workflow.

The final application should be polished enough for a 5-minute live hackathon demonstration.