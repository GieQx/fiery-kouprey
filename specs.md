You are acting as a senior software architect, SDMX practitioner, and hackathon engineer.

Build the requirements for a MINIMUM VIABLE PRODUCT called:

SDMX Alignment Assistant

The goal is to create a small but convincing hackathon application that compares one local SDMX DSD against one selected reference DSD and helps a statistical producer identify meaningful alignment issues.

This is NOT a full SDMX validator.

The MVP should focus on:
- structural comparison;
- concept comparison;
- codelist/code comparison;
- AI-assisted semantic matching;
- human review;
- explainable results.

The MVP must be feasible to build in 1–2 hours.

Core demo flow:

1. User uploads or selects:
   - one local SDMX DSD;
   - one reference SDMX DSD.

2. The system parses both DSDs and extracts:
   - dimension IDs;
   - names/descriptions;
   - concept references;
   - codelist references;
   - codelist values;
   - attributes;
   - representations.

3. The system performs deterministic comparison first:
   - exact ID match;
   - exact label/name match;
   - exact code match;
   - missing element;
   - representation difference.

4. For unmatched concepts or codes, the system uses AI-assisted semantic matching.

Examples:

Local:
AREA

Reference:
REF_AREA

Result:
Possible equivalent concept.
Confidence: 0.91.
Reason:
Both represent the geographic reference area of an observation.

Local:
SEX
Codes:
1 = Male
2 = Female
9 = Total

Reference:
SEX
Codes:
M = Male
F = Female
T = Total

Result:
Concept matches.
Code mapping required.

Local:
EMP_STATUS

Reference:
STATUS_IN_EMPLOYMENT

Result:
Potential semantic match.
Human review required.

Important principles:

- deterministic checks must not use AI;
- AI is only used for semantic matching and explanation;
- AI recommendations must never be automatically accepted;
- every AI suggestion must be marked as requiring human review;
- do not say that a local DSD is “wrong” just because it differs from a reference DSD;
- describe differences as alignment or interoperability issues;
- all findings must be traceable to both source DSD elements.

MVP FUNCTIONAL REQUIREMENTS

FR-001
The user can upload two SDMX-ML structure files.

FR-002
The user can identify one file as:
- Local DSD
- Reference DSD

FR-003
The system parses both files and extracts DSD structure information.

FR-004
The system compares dimensions.

For each dimension show:
- local ID;
- reference ID;
- local label;
- reference label;
- matching method;
- alignment status.

FR-005
The system compares referenced concepts.

FR-006
The system compares referenced codelists.

FR-007
The system compares code values and labels.

FR-008
The deterministic comparison engine must identify:
- exact match;
- name match;
- missing in local;
- missing in reference;
- code mismatch;
- representation mismatch.

FR-009
If deterministic matching cannot resolve a concept, the system may send:
- ID;
- name;
- description;
- annotations if available

to an AI semantic matcher.

FR-010
The AI returns:
- suggested reference concept;
- relation;
- confidence;
- short explanation.

Allowed relation values:
- equivalent
- similar
- broader
- narrower
- uncertain
- incompatible

FR-011
All AI results must be clearly labeled:
“AI-assisted suggestion — human review required.”

FR-012
The reviewer can:
- Accept
- Reject
- Mark Unresolved

FR-013
The user can add a short reviewer note.

FR-014
The application displays a summary dashboard showing:
- exact matches;
- possible semantic matches;
- code mappings required;
- missing elements;
- unresolved items.

Do not create a single overall score.

FR-015
The findings table must contain:

- Element Type
- Local Element
- Reference Element
- Match Type
- Alignment Status
- Confidence
- Explanation
- Review Status

FR-016
The system supports filtering findings by:
- Exact
- Partial
- Mapping Required
- Missing
- AI Suggested
- Unresolved

FR-017
The user can export results as JSON.

Optional:
CSV export if time allows.

OUT OF SCOPE FOR MVP

Do NOT implement:
- user accounts;
- authentication;
- organization management;
- multi-project workflows;
- database-heavy persistence;
- PDF generation;
- complex access control;
- automated DSD modification;
- automated mapping deployment;
- full SDMX registry;
- complete SDMX validation;
- advanced visualization;
- production deployment architecture;
- version history;
- approval chains.

TECHNICAL STACK

Use the simplest practical stack.

Preferred:

Frontend:
- React or Next.js
- Tailwind CSS or simple CSS

Backend:
- Python FastAPI

Parsing:
- use an existing Python SDMX library if reliable for structure messages;
- otherwise use XML parsing with lxml for the specific MVP fields.

Persistence:
- in-memory session or SQLite only if needed.

AI:
- configurable LLM endpoint;
- abstract AI calls behind a service module;
- application should still work without AI for deterministic comparisons.

ARCHITECTURE

Keep modules separate:

frontend/
backend/
  parser/
  comparator/
  semantic_matcher/
  models/
  api/

Suggested processing flow:

Upload
↓
Parse structures
↓
Normalize extracted elements
↓
Deterministic comparison
↓
Identify unresolved elements
↓
AI semantic matching
↓
Human review
↓
Export results

COMPARISON LOGIC

Use this matching order:

1. exact ID match
2. exact normalized label match
3. exact concept reference match
4. exact codelist/code label match
5. simple normalized lexical similarity
6. AI semantic similarity
7. unresolved

Normalization may include:
- lowercase;
- trim whitespace;
- replace underscores with spaces;
- basic token normalization.

Do not use AI before deterministic matching.

DATA MODEL

Define a simple Finding object:

{
  "id": "finding-001",
  "element_type": "concept",
  "local_id": "AREA",
  "local_label": "Area",
  "reference_id": "REF_AREA",
  "reference_label": "Reference area",
  "match_method": "ai_semantic",
  "alignment_status": "possible_equivalent",
  "confidence": 0.91,
  "explanation": "Both concepts represent the geographic reference area.",
  "review_status": "pending",
  "review_note": ""
}

UI REQUIREMENTS

Screen 1:
Upload / Select Files

Show two cards:
Local DSD
Reference DSD

Button:
Compare Structures

Screen 2:
Comparison Summary

Cards:
Exact Matches
Semantic Matches
Mapping Required
Missing
Unresolved

Below:
Findings table.

Screen 3 or Modal:
Detailed Finding

Show side-by-side:

LOCAL
ID
Name
Description
Codes

REFERENCE
ID
Name
Description
Codes

Then:

System Finding
AI Explanation
Confidence

Buttons:
Accept
Reject
Unresolved

For the hackathon demo, prioritize usability over visual complexity.

HACKATHON DEMO DATA

Create sample DSD data if no real DSDs are available.

The demo must contain at least these examples:

Example 1:
AREA
vs
REF_AREA

Expected:
Semantic match.

Example 2:
SEX
Local codes:
1 Male
2 Female
9 Total

Reference codes:
M Male
F Female
T Total

Expected:
Concept exact/near match.
Code mapping required.

Example 3:
EMP_STATUS
vs
STATUS_IN_EMPLOYMENT

Expected:
AI-assisted semantic suggestion.

Example 4:
A local dimension with no equivalent reference element.

Expected:
Local extension.

Example 5:
A reference-required element missing locally.

Expected:
Missing reference element.

TRUSTWORTHINESS REQUIREMENTS

Every finding must record:
- local element;
- reference element;
- matching method;
- deterministic or AI;
- confidence if AI;
- reviewer decision.

If AI fails, the app must:
- show the element as unresolved;
- continue processing other findings.

Never fabricate SDMX metadata.

SUCCESS CRITERIA

The MVP is successful if:

1. Two DSDs can be loaded.
2. Their main structural elements are extracted.
3. Exact matches are identified correctly.
4. Code differences are identified.
5. At least one AI-assisted semantic match works.
6. The AI recommendation is explainable.
7. The user can accept or reject the recommendation.
8. Results can be exported as JSON.
9. The entire workflow can be demonstrated in under 5 minutes.

DELIVERABLES

First, before coding, produce:

1. concise MVP requirements;
2. architecture;
3. proposed repository structure;
4. data model;
5. API endpoints;
6. UI screen descriptions;
7. implementation sequence;
8. acceptance criteria;
9. test cases;
10. 5-minute hackathon demo script.

Then stop.

Do not start implementation until I explicitly say:

START IMPLEMENTATION