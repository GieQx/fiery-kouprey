Please revise the existing application with the following changes.

1. Remove Demo Load Buttons
Review whether it is safe to remove the following buttons:
- Load Local Demo
- Load BOP Demo

Since the intended workflow is now based on users uploading their own DSD files, these demo buttons are no longer needed for the main application flow.

If they are only used for demonstration/testing and are not required by other parts of the application, remove them from the user interface while preserving any reusable demo data or test fixtures in the codebase for development/testing purposes.

2. Default Reference Source: SDMX Global Registry
Update the reference standards discovery logic so that the SDMX Global Registry is treated as the primary/default source for structural reference artefacts.

The application should:
- search or map relevant reference DSDs from the SDMX Global Registry by default;
- retrieve or display available metadata such as agency, artefact ID, version, name, and source;
- clearly identify the SDMX Global Registry as the source;
- allow the application to support additional trusted reference sources as well.

Do not hard-code the solution to the Global Registry only.

Design and add authoritative sources to the reference-source layer, such as:
- IMF;
- OECD;
- Eurostat;
- other official SDMX registries or curated standards repositories.

If live registry access is unavailable, the application should degrade gracefully and use locally cached or curated reference artefacts where available.

3. Add an AI Standards Recommendation Agent
Add an AI-assisted component that analyzes the uploaded local DSD after the user selects:

- a reference DSD / structural standard; and
- a methodological standard, where applicable.

The AI Agent should suggest additional components, mappings, or metadata that may improve alignment with the selected standards.

Possible recommendations may include:
- missing dimensions;
- missing attributes;
- missing concepts;
- missing codelists or codes;
- representation changes;
- concept mappings;
- metadata improvements;
- clarification of ambiguous labels or definitions;
- additional annotations or descriptions;
- recommendations that reduce possible sources of confusion or misinterpretation.

For every recommendation, show:

- the local element concerned;
- the relevant reference element or methodological principle;
- the proposed recommendation;
- the reason why;
- the evidence used;
- whether the recommendation came from deterministic comparison or AI analysis;
- the authoritative source or citation where applicable.

The AI should explicitly focus on identifying and resolving possible sources of confusion such as:
- ambiguous concept names;
- similar concepts with different statistical meanings;
- unclear code labels;
- inconsistent representations;
- missing definitions;
- local terminology that differs from international terminology;
- elements that could be misinterpreted by downstream users.
- elements that do not provide/ or no available additional context to the AI system.

4. Human-in-the-Loop Requirement
The AI Agent must never directly modify the DSD.

All recommendations must be presented to the user for review with options such as:

- Accept
- Reject
- Modify
- Mark Unresolved
- No Action Required

Only approved recommendations may be included in the final transformation.

5. Trustworthiness
Do not allow the AI to invent:
- SDMX concepts;
- codes;
- codelists;
- reference artefacts;
- methodological requirements;
- citations.

Recommendations must be grounded in:
- the uploaded local DSD;
- the selected reference DSD;
- the selected methodological standard;
- trusted reference metadata;
- authoritative sources.

If the evidence is insufficient, return:
“Insufficient information for a reliable recommendation.”

6. Preserve Existing Working Components
Do not unnecessarily rewrite working components.

Reuse the existing:
- Streamlit UI;
- DSD parser;
- comparator;
- LLM provider abstraction;
- standards discovery logic;
- review workflow;
- transformation logic.

Refactor only where needed to support these changes.

Before implementing, briefly identify:
1. which current components will be changed;
2. whether removing the demo buttons has any dependencies;
3. how the SDMX Global Registry integration will work;
4. where the new AI Standards Recommendation Agent will fit into the existing workflow.

Then implement the changes.