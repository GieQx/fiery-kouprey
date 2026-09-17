# AI-Assisted SDMX Standards Alignment Workbench

A Streamlit hackathon MVP that takes a statistical producer from standards discovery to a reviewed and validated SDMX revision. Deterministic evidence runs before optional AI assistance, experts approve every executable change, and AI never writes XML.

## Run

```powershell
uv sync
uv run streamlit run app.py
```

The app also works without an LLM. For optional semantic assistance, select OpenAI or Ollama in the sidebar. Ollama models are discovered automatically from the configured endpoint.

## Five-Minute BOP Demo

1. Select **Load BOP demo**.
2. Inspect the ranked references and select **Balance of Payments workshop structural reference**.
3. Verify that the structural reference is shown separately from IMF BPM7/BPM6 methodology and SDMX registry sources.
4. Inspect the alignment assessment and its reason-why evidence.
5. In **Human review**, select **Apply transparent BOP demo decisions**. This explicit accelerator is available only for the built-in synthetic demo.
6. In **Approved changes**, enter reviewer initials and finalize the change set.
7. In **Generate and prove**, generate the revised DSD.
8. Review the scoped technical checks, reference alignment result, and before-and-after metrics.
9. Download the revised XML, audit JSON, and CSV change log.

## Source Integrity

- `SDMXWS:DSD_BOP(1.0)` is a workshop-supplied structural demonstration artefact. It is not presented as an IMF DSD.
- IMF BPM7 and BPM6 are methodological standards with authoritative IMF links. They are not treated as DSDs.
- Shared SDMX structures and codelists link to the SDMX Global Registry.
- Synthetic references and local demos are labeled as such.

## Trust Contract

- The original uploaded XML is preserved.
- Discovery and comparison are deterministic first.
- AI is limited to semantic interpretation and explanation.
- AI suggestions require expert validation.
- Only accepted or modified-and-approved typed actions enter the change set.
- Revised XML is produced by an lxml transformation engine, not free-form generation.
- Failed transformation actions prevent a technical PASS result.
- Audit exports contain sources, evidence, decisions, model provenance, transformations, and validation results, but never credentials.

## Validation Boundary

`MVP SDMX Technical Checks` cover safe XML parsing, application reparsing, component identity uniqueness, dimension positions, codelist reference resolution, and transformation completion. A PASS is not official SDMX certification or complete XSD/business-rule validation.

`Reference Alignment Assessment` recomputes the deterministic comparison against the same selected reference. Structural alignment does not guarantee complete real-world interoperability.

## LLM Modes

- **No LLM:** complete deterministic workflow, including generation and validation.
- **OpenAI:** uses `OPENAI_API_KEY` and a configurable model.
- **Ollama:** uses a configurable endpoint and automatically discovered installed model.

## Test

```powershell
uv run pytest -q
```

## Continuation Path

The architecture can later add official SDMX schema/FMR validation, live registry and institutional catalogs, mapping repositories, additional statistical domains, dataset validation, persistence, and integration with .Stat Suite or production SDMX pipelines.
