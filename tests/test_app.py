from pathlib import Path

from streamlit.testing.v1 import AppTest

from sdmx_alignment.semantic_matcher.ollama_provider import OllamaProvider


def test_app_uses_one_upload_and_discovery_flow():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=15).run()

    assert not app.exception
    assert app.title[0].value == "AI-Assisted SDMX Standards Alignment Workbench"
    assert len(app.file_uploader) == 1
    assert app.file_uploader[0].label == "Local DSD"
    assert any(button.label == "Load local demo" for button in app.button)
    assert any(button.label == "Load BOP demo" for button in app.button)

    app.button(key="load_local_demo").click().run()

    assert not app.exception
    assert any("Candidate standards found" in item.value for item in app.markdown)
    assert any("DSD_REFERENCE_EMP" in item.value for item in app.markdown)

    app.button(key="select_reference_DSD_REFERENCE_EMP").click().run()

    assert not app.exception
    assert {metric.label for metric in app.metric} >= {
        "Exact",
        "Semantic suggestions",
        "Mapping required",
        "Missing",
        "Unresolved",
    }
    assert any("DSD_LOCAL_EMP" in item.value for item in app.markdown)


def test_bop_demo_shows_separate_sources_and_generation_workflow():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()

    app.button(key="load_bop_demo").click().run()

    assert not app.exception
    assert any("Balance of Payments workshop structural reference" in item.value for item in app.markdown)
    assert any("BPM7" in item.value for item in app.markdown)

    app.button(key="select_reference_DSD_BOP").click().run()

    assert not app.exception
    assert any("Reason why" in item.value for item in app.markdown)
    assert any(button.label == "Apply transparent BOP demo decisions" for button in app.button)

    app.button(key="apply_bop_demo_decisions").click().run()
    reviewer = next(item for item in app.text_input if item.label == "Reviewer name or initials")
    reviewer.set_value("PSA reviewer").run()
    next(button for button in app.button if button.label == "Finalize approved change set").click().run()
    next(button for button in app.button if button.label == "Generate revised DSD").click().run()

    assert not app.exception
    assert any("MVP SDMX Technical Checks" in item.value for item in app.markdown)
    assert any("Before and After" in item.value for item in app.markdown)
    assert {item.label for item in app.download_button} >= {
        "Download revised DSD",
        "Download audit JSON",
        "Download change log CSV",
    }


def test_app_resolves_uploaded_dataflow_to_its_library_dsd():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    upload = Path(__file__).parent / "fixtures" / "DSD_BOP@DF_BOP.xml"

    app.file_uploader[0].upload(upload.name, upload.read_bytes(), "application/xml").run()
    next(button for button in app.button if button.label == "Discover standards").click().run()

    assert not app.exception
    assert not app.error
    assert any("resolved from the curated reference library" in item.value for item in app.success)
    assert any("SDMXWS:DSD_BOP(1.0)" in item.value for item in app.markdown)


def test_app_discovers_and_selects_installed_ollama_models(monkeypatch):
    monkeypatch.setattr(
        OllamaProvider,
        "list_models",
        lambda self: ["qwen2.5:0.5b-instruct-q4_0", "llama3.2:3b"],
    )
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=15).run()

    provider = next(item for item in app.selectbox if item.label == "Provider")
    provider.select("Ollama").run()

    model = next(item for item in app.selectbox if item.label == "Ollama model")
    assert model.options == ["qwen2.5:0.5b-instruct-q4_0", "llama3.2:3b"]
    assert model.value == "qwen2.5:0.5b-instruct-q4_0"
    assert any(button.label == "Refresh models" for button in app.button)
