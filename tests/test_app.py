from pathlib import Path

from streamlit.testing.v1 import AppTest

from sdmx_alignment.models.recommendations import StandardsRecommendationResult
from sdmx_alignment.models.semantic import ProviderReadiness
from sdmx_alignment.semantic_matcher.ollama_provider import OllamaProvider


REMOVED_DEMO_BUTTONS = {
    "Load local demo",
    "Load BOP demo",
    "Apply transparent BOP demo decisions",
}


def upload_and_discover(app, fixture_name):
    upload = Path(__file__).parent / "fixtures" / fixture_name
    app.file_uploader[0].upload(upload.name, upload.read_bytes(), "application/xml").run()
    next(button for button in app.button if button.label == "Discover standards").click().run()


def assert_demo_buttons_are_absent(app):
    assert REMOVED_DEMO_BUTTONS.isdisjoint(button.label for button in app.button)


def assert_analysis_is_cleared(app):
    assert app.session_state.local_structure is None
    assert app.session_state.discovery_result is None
    assert app.session_state.reference_structure is None
    assert app.session_state.comparison is None
    assert app.session_state.alignment_plan is None
    assert app.session_state.original_xml is None
    assert app.session_state.reference_xml is None
    assert app.session_state.transformation is None
    assert app.session_state.technical_validation is None
    assert app.session_state.reference_alignment is None
    assert app.session_state.revised_comparison is None
    assert app.session_state.before_after is None
    assert not app.metric


def review_all_bop_findings(app):
    findings = [
        (finding.id, finding.local, finding.reference)
        for finding in app.session_state.comparison.findings
        if finding.review_status != "not_required"
    ]
    for finding_id, local, reference in findings:
        next(item for item in app.selectbox if item.label == "Finding").select(finding_id).run()
        decision = "accepted" if reference else "no_action"
        next(item for item in app.radio if item.label == "Decision").set_value(decision)
        if decision == "accepted":
            action = "MAP" if local else "ADD_MISSING_ELEMENT"
            next(item for item in app.selectbox if item.label == "Action when accepted").select(action)
        next(item for item in app.text_area if item.label == "Reviewer note").set_value(
            "Reviewed against the BOP fixture evidence."
        )
        next(button for button in app.button if button.label == "Save review").click().run()


def test_app_uses_one_upload_and_discovery_flow():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=15).run()

    assert not app.exception
    assert app.title[0].value == "AI-Assisted SDMX Standards Alignment Workbench"
    assert len(app.file_uploader) == 1
    assert app.file_uploader[0].label == "Local DSD"
    assert_demo_buttons_are_absent(app)

    upload_and_discover(app, "local-demo.xml")

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

    upload_and_discover(app, "local-bop-demo.xml")

    assert not app.exception
    assert any("Balance of Payments and International Investment Position" in item.value for item in app.markdown)
    assert any("BPM7" in item.value for item in app.markdown)

    app.button(key="select_reference_BOP").click().run()

    assert not app.exception
    assert any("Reason why" in item.value for item in app.markdown)
    assert_demo_buttons_are_absent(app)

    review_all_bop_findings(app)
    reviewer = next(item for item in app.text_input if item.label == "Reviewer name or initials")
    reviewer.set_value("PSA reviewer").run()
    next(button for button in app.button if button.label == "Finalize approved change set").click().run()
    next(button for button in app.button if button.label == "Generate revised DSD").click().run()

    assert not app.exception
    assert any("MVP SDMX Technical Checks" in item.value for item in app.markdown)
    assert any("Before and After" in item.value for item in app.markdown)
    assert app.session_state.technical_validation.status == "PASS"
    assert app.session_state.reference_alignment.status == "PARTIALLY_ALIGNED"
    assert {item.label for item in app.download_button} >= {
        "Download revised DSD",
        "Download audit JSON",
        "Download change log CSV",
    }


def test_bop_discovery_uses_global_registry_reference_for_comparison():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()

    assert any(
        "SDMX Global Registry - primary source" in item.value
        for item in app.markdown
    )
    assert any(item.label == "Registry agency ID" for item in app.text_input)
    assert any(item.label == "Registry DSD ID" for item in app.text_input)
    assert any(item.label == "Registry version" for item in app.text_input)

    upload_and_discover(app, "local-bop-demo.xml")

    registry_button = app.button(key="select_reference_BOP")
    assert registry_button
    registry_button.click().run()

    assert not app.exception
    assert app.session_state.selected_reference_identity == "IMF:BOP(2.6.0)"
    assert app.session_state.reference_structure.agency_id == "IMF"
    assert app.session_state.reference_structure.id == "BOP"
    assert any("SDMX_GLOBAL_REGISTRY" in item.value for item in app.caption)


def test_app_resolves_uploaded_dataflow_to_its_library_dsd():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    upload = Path(__file__).parent / "fixtures" / "DSD_BOP@DF_BOP.xml"

    app.file_uploader[0].upload(upload.name, upload.read_bytes(), "application/xml").run()
    next(button for button in app.button if button.label == "Discover standards").click().run()

    assert not app.exception
    assert not app.error
    assert any("resolved from the curated reference library" in item.value for item in app.success)
    assert any("SDMXWS:DSD_BOP(1.0)" in item.value for item in app.markdown)


def test_replacing_upload_clears_previous_analysis_before_discovery():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    upload_and_discover(app, "local-demo.xml")
    app.button(key="select_reference_DSD_REFERENCE_EMP").click().run()

    replacement = Path(__file__).parent / "fixtures" / "local-bop-demo.xml"
    app.file_uploader[0].upload(
        replacement.name,
        replacement.read_bytes(),
        "application/xml",
    ).run()

    assert not app.exception
    assert any(replacement.name in item.value for item in app.caption)
    assert_analysis_is_cleared(app)
    assert all("DSD_LOCAL_EMP" not in item.value for item in app.markdown)


def test_invalid_replacement_does_not_retain_previous_analysis():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    upload_and_discover(app, "local-demo.xml")
    app.button(key="select_reference_DSD_REFERENCE_EMP").click().run()

    app.file_uploader[0].upload("invalid.xml", b"<not-sdmx>", "application/xml").run()
    next(button for button in app.button if button.label == "Discover standards").click().run()

    assert not app.exception
    assert app.error
    assert_analysis_is_cleared(app)
    assert all("DSD_LOCAL_EMP" not in item.value for item in app.markdown)


def test_bop_fixture_matches_preserved_sample():
    root = Path(__file__).parents[1]

    assert (root / "tests" / "fixtures" / "local-bop-demo.xml").read_bytes() == (
        root / "samples" / "local-bop-demo.xml"
    ).read_bytes()


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


def test_ai_recommendation_command_is_disabled_without_ready_provider():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    upload_and_discover(app, "local-bop-demo.xml")
    app.button(key="select_reference_BOP").click().run()

    command = next(button for button in app.button if button.label == "Run AI recommendations")

    assert command.disabled is True
    assert app.session_state.recommendations == {}


def test_ai_recommendations_run_explicitly_and_render_grounded_evidence(monkeypatch):
    class ReadyMatcher:
        provider_name = "fake"
        recommendations = 0

        def is_ready(self):
            return ProviderReadiness(ready=True, message="ready")

        def match(self, request):
            raise AssertionError("comparison must not run AI automatically")

        def recommend(self, request):
            type(self).recommendations += 1
            return StandardsRecommendationResult(
                local_element_id=request.local.id,
                reference_element_id=request.reference.id,
                code_ids=[],
                recommendation="Reuse the selected reference concept after expert review.",
                reason="The supplied local and reference definitions support this candidate alignment.",
                evidence=["Both element identifiers are present in the selected comparison."],
                citation_ids=[request.citations[0].id] if request.citations else [],
                principle_id=request.principles[0].id if request.principles else None,
                confidence=0.84,
                provider="fake",
                model="grounded-test-model",
                grounding_status="grounded",
            )

        def complete(self, question, context):
            return "not used"

    monkeypatch.setattr(
        "sdmx_alignment.semantic_matcher.factory.create_matcher",
        lambda settings: ReadyMatcher(),
    )
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    upload_and_discover(app, "local-bop-demo.xml")
    app.button(key="select_reference_BOP").click().run()

    assert ReadyMatcher.recommendations == 0
    methodology = next(item for item in app.selectbox if item.label == "Methodology")
    methodology.select("BPM7").run()
    command = next(button for button in app.button if button.label == "Run AI recommendations")
    assert command.disabled is False
    command.click().run()

    rendered = "\n".join(
        str(item.value)
        for collection in (app.markdown, app.caption, app.info, app.warning)
        for item in collection
    )
    assert not app.exception
    assert ReadyMatcher.recommendations > 0
    assert app.session_state.recommendations
    assert "Reuse the selected reference concept after expert review." in rendered
    assert "The supplied local and reference definitions support this candidate alignment." in rendered
    assert "Both element identifiers are present" in rendered
    assert "AI-assisted recommendation" in rendered
    assert "BPM7_CONTEXT" in rendered
    assert "BPM7" in rendered
