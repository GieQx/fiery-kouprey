from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from sdmx_alignment.alignment_plan import build_alignment_plan, finalize_alignment_plan
from sdmx_alignment.comparator.engine import compare_structures
from sdmx_alignment.config import LLMSettings, choose_ollama_model
from sdmx_alignment.discovery import discover_candidates
from sdmx_alignment.evaluation import FIXED_QUESTION, context_hash, create_evaluation, dsd_context
from sdmx_alignment.export import (
    export_audit_package,
    export_change_log_csv,
    export_evidence_package,
)
from sdmx_alignment.models.structures import DSDStructure
from sdmx_alignment.parser.sdmx_structure import StructureParseError, parse_structure
from sdmx_alignment.reference_library import (
    LibraryEntry,
    load_reference_library,
    resolve_uploaded_structure,
)
from sdmx_alignment.reporting import build_before_after_report
from sdmx_alignment.review import apply_review, default_action
from sdmx_alignment.semantic_matcher.base import ProviderError
from sdmx_alignment.semantic_matcher.factory import create_matcher
from sdmx_alignment.semantic_matcher.ollama_provider import OllamaProvider
from sdmx_alignment.semantic_matcher.service import enrich_unresolved, generate_assessment
from sdmx_alignment.transformation import transform_dsd
from sdmx_alignment.validation import assess_reference_alignment, validate_revised_dsd


BASE_DIR = Path(__file__).parent
SCORE_LABELS = {
    "reuse": "Reusable concepts and codelists",
    "code_mapping": "Required code mappings",
    "gaps": "Missing elements and local extensions",
    "limitations": "Unresolved issues and limitations",
    "evidence": "Claim-level DSD evidence",
}
ANALYSIS_STATE_DEFAULTS = {
    "local_structure": None,
    "reference_structure": None,
    "discovery_result": None,
    "selected_reference_identity": None,
    "comparison": None,
    "alignment_plan": None,
    "evaluation": None,
    "baseline_answer": "",
    "improved_answer": "",
    "answer_snapshot": None,
    "original_xml": None,
    "upload_resolution_message": None,
    "reference_xml": None,
    "transformation": None,
    "technical_validation": None,
    "reference_alignment": None,
    "revised_comparison": None,
    "before_after": None,
}


st.set_page_config(page_title="AI-Assisted SDMX Standards Alignment Workbench", page_icon="SA", layout="wide")
st.markdown(
    """
    <style>
    :root { --navy:#17324d; --teal:#087f78; --gold:#d89a30; --line:#d6dfdd; --ink:#17252a; }
    .block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1500px; }
    h1, h2, h3 { color: var(--navy); letter-spacing: 0; }
    h1 { font-size: 2rem !important; margin-bottom: .15rem !important; }
    [data-testid="stMetric"] { border: 1px solid var(--line); border-top: 4px solid var(--teal); padding: .75rem; background: white; }
    .status-line { color:#52656b; margin-bottom:1.2rem; }
    .ai-banner { border-left:5px solid var(--gold); background:#fff7e8; padding:.75rem 1rem; color:#6b4a12; }
    .evidence { border-left:5px solid var(--teal); background:#eef6f4; padding:.7rem 1rem; }
    .small-label { color:#617279; font-size:.78rem; font-weight:700; text-transform:uppercase; }
    div[data-testid="stFileUploader"] { border:1px solid var(--line); padding:.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize_state():
    defaults = {**ANALYSIS_STATE_DEFAULTS, "upload_fingerprint": None}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_analysis_state():
    for key, value in ANALYSIS_STATE_DEFAULTS.items():
        st.session_state[key] = value


@st.cache_data(ttl=15, show_spinner=False)
def discover_ollama_models(endpoint: str, timeout: float) -> list[str]:
    return OllamaProvider(endpoint, "", timeout=timeout).list_models()


def provider_settings():
    defaults = LLMSettings.from_env()
    labels = {"No LLM": "none", "OpenAI": "openai", "Ollama": "ollama"}
    inverse = {value: key for key, value in labels.items()}
    with st.sidebar:
        st.header("LLM provider")
        selected = st.selectbox(
            "Provider",
            list(labels),
            index=list(labels).index(inverse.get(defaults.provider, "No LLM")),
        )
        provider = labels[selected]
        openai_override = ""
        openai_model = defaults.openai_model
        ollama_url = defaults.ollama_base_url
        ollama_model = defaults.ollama_model
        if provider == "openai":
            openai_override = st.text_input("API key override", type="password")
            if defaults.openai_api_key:
                st.caption("OPENAI_API_KEY is available from the environment.")
            openai_model = st.text_input("OpenAI model", value=defaults.openai_model)
        elif provider == "ollama":
            ollama_url = st.text_input("Ollama endpoint", value=defaults.ollama_base_url)
            try:
                ollama_models = discover_ollama_models(ollama_url, defaults.timeout_seconds)
            except ProviderError:
                st.warning("Could not discover models from this Ollama endpoint.")
                ollama_model = st.text_input("Ollama model", value=defaults.ollama_model)
            else:
                selected_model = choose_ollama_model(ollama_models, defaults.ollama_model)
                if ollama_models:
                    ollama_model = st.selectbox(
                        "Ollama model",
                        ollama_models,
                        index=ollama_models.index(selected_model),
                    )
                else:
                    st.warning("No installed Ollama models were found.")
                    ollama_model = st.text_input("Ollama model", value=defaults.ollama_model)
            if st.button("Refresh models", width="stretch"):
                discover_ollama_models.clear()
                st.rerun()
        timeout = st.number_input("Timeout (seconds)", min_value=1, max_value=180, value=int(defaults.timeout_seconds))
        settings = LLMSettings(
            provider=provider,
            openai_api_key=openai_override or defaults.openai_api_key,
            openai_model=openai_model,
            ollama_base_url=ollama_url,
            ollama_model=ollama_model,
            timeout_seconds=timeout,
        )
        matcher = create_matcher(settings)
        if provider == "none":
            st.info("Deterministic mode")
        elif st.button("Test connection", width="stretch"):
            readiness = matcher.is_ready()
            (st.success if readiness.ready else st.warning)(readiness.message)
        st.caption("Deterministic comparison always runs first.")
    return settings, matcher


def run_comparison(local: DSDStructure, reference: DSDStructure, matcher):
    result = compare_structures(local, reference)
    result = enrich_unresolved(result, matcher)
    st.session_state.local_structure = local
    st.session_state.reference_structure = reference
    st.session_state.comparison = result
    st.session_state.alignment_plan = build_alignment_plan(result)
    st.session_state.evaluation = None
    st.session_state.baseline_answer = ""
    st.session_state.improved_answer = ""
    st.session_state.answer_snapshot = None
    st.session_state.transformation = None
    st.session_state.technical_validation = None
    st.session_state.reference_alignment = None
    st.session_state.revised_comparison = None
    st.session_state.before_after = None


def load_local_structure(file_name: str, xml_bytes: bytes, library: list[LibraryEntry]):
    resolution = resolve_uploaded_structure(file_name, xml_bytes, library)
    local = resolution.structure
    discovery_result = discover_candidates(local, library)
    clear_analysis_state()
    st.session_state.local_structure = local
    st.session_state.discovery_result = discovery_result
    st.session_state.original_xml = resolution.structure_xml
    st.session_state.upload_resolution_message = resolution.message


def select_reference(entry: LibraryEntry, matcher):
    st.session_state.selected_reference_identity = entry.metadata.identity
    st.session_state.reference_xml = entry.xml_bytes
    run_comparison(st.session_state.local_structure, entry.structure, matcher)


def render_discovery_candidates(library: list[LibraryEntry], matcher):
    result = st.session_state.discovery_result
    if result is None:
        return

    st.subheader("Discover reference standards")
    st.markdown(f"**{result.message}**")
    st.caption("Candidate ordering indicates discovery relevance, not authority or statistical equivalence.")

    entry_by_identity = {entry.metadata.identity: entry for entry in library}
    for candidate in result.candidates:
        with st.container(border=True):
            heading, action = st.columns([4, 1])
            with heading:
                st.markdown(f"**{candidate.reference.name}**  ")
                st.markdown(f"`{candidate.reference.identity}` | **{candidate.discovery_tier.title()} evidence**")
                st.caption(
                    f"Structural reference | Issuer: {candidate.reference.issuer} | Domain: {candidate.reference.domain} | "
                    f"Provenance: {candidate.reference.provenance} | "
                    f"Registered: {candidate.reference.retrieved_at.isoformat()}"
                )
                st.write(candidate.explanation)
                evidence_text = " | ".join(
                    f"{item.signal.replace('_', ' ')}: {item.count}"
                    for item in candidate.evidence
                    if item.count
                )
                st.caption(evidence_text)
                if candidate.reference.source_url:
                    st.markdown(f"Authoritative structure source: [{candidate.reference.source_url}]({candidate.reference.source_url})")
                if candidate.reference.related_sources:
                    st.markdown("**Related methodology and shared SDMX sources**")
                    for source in candidate.reference.related_sources:
                        source_type = source.artefact_type.replace("_", " ").title()
                        st.markdown(
                            f"- **{source.id} - {source.name}** ({source.version})  "
                            f"\n  {source_type} | {source.issuer} | [Authoritative source]({source.source_url})"
                        )
            with action:
                if st.button(
                    "Select",
                    key=f"select_reference_{candidate.reference.artefact_id}",
                    type="primary" if candidate.discovery_tier == "strong" else "secondary",
                    width="stretch",
                ):
                    select_reference(entry_by_identity[candidate.reference.identity], matcher)
                    st.rerun()

    with st.expander("Browse all library entries"):
        identity = st.selectbox(
            "Reference standard",
            [entry.metadata.identity for entry in library],
            format_func=lambda value: next(
                f"{entry.metadata.name} - {value}" for entry in library if entry.metadata.identity == value
            ),
        )
        if st.button("Use selected library entry", key="select_library_reference"):
            select_reference(entry_by_identity[identity], matcher)
            st.rerun()

    selected = st.session_state.selected_reference_identity
    if selected:
        metadata = entry_by_identity[selected].metadata
        st.success(
            f"Selected reference: {metadata.identity} | {metadata.provenance}. "
            "Selection is a producer decision, not an authoritative system determination."
        )


def render_source_selection(library: list[LibraryEntry], matcher):
    st.subheader("1. Discover - Upload Local DSD")
    local_file = st.file_uploader("Local DSD", type=["xml"], key="local_upload")
    local_xml = local_file.getvalue() if local_file else None
    upload_fingerprint = (
        (local_file.name, hashlib.sha256(local_xml).hexdigest())
        if local_file
        else None
    )
    if upload_fingerprint != st.session_state.upload_fingerprint:
        clear_analysis_state()
        st.session_state.upload_fingerprint = upload_fingerprint
    if local_file:
        st.caption(f"{local_file.name} | {local_file.size:,} bytes")

    if st.button(
        "Discover standards",
        type="primary",
        width="stretch",
        disabled=local_file is None,
    ):
        try:
            load_local_structure(local_file.name, local_xml, library)
        except StructureParseError as exc:
            st.error(str(exc))
        except Exception:
            st.error("Standards discovery could not be completed. Check the local DSD and library configuration.")

    local = st.session_state.local_structure
    if local:
        if st.session_state.upload_resolution_message:
            st.success(st.session_state.upload_resolution_message)
        st.markdown(
            f"**Local structure:** `{local.agency_id}:{local.id}({local.version})` | "
            f"{len(local.dimensions)} dimensions | {len(local.codelists)} codelists"
        )
    render_discovery_candidates(library, matcher)


def finding_rows(result):
    return [
        {
            "ID": item.id,
            "Type": item.element_type,
            "Local": item.local.id if item.local else "-",
            "Reference": item.reference.id if item.reference else "-",
            "Match": item.match_method,
            "Status": item.alignment_status,
            "Confidence": item.confidence,
            "Explanation": item.explanation,
            "Review": item.review_status,
            "Action": item.recommended_action or "-",
        }
        for item in result.findings
    ]


def render_finding_detail(finding):
    left, right = st.columns(2)
    with left:
        st.markdown("<div class='small-label'>Local</div>", unsafe_allow_html=True)
        if finding.local:
            st.json(finding.local.model_dump(), expanded=False)
        else:
            st.caption("No local counterpart")
    with right:
        st.markdown("<div class='small-label'>Reference</div>", unsafe_allow_html=True)
        if finding.reference:
            st.json(finding.reference.model_dump(), expanded=False)
        else:
            st.caption("No reference counterpart")
    if finding.is_ai_assisted:
        st.markdown("<div class='ai-banner'><b>AI-assisted suggestion - human review required.</b></div>", unsafe_allow_html=True)
        st.caption(f"Provider: {finding.llm_provider} | Model: {finding.llm_model} | Confidence: {finding.confidence:.2f}")
    st.markdown(
        f"<div class='evidence'><b>Reason why</b><br>{finding.explanation}<br>"
        f"<small>Classification: {finding.finding_classification.replace('_', ' ').title()} | "
        f"Method: {finding.match_method.replace('_', ' ')}</small></div>",
        unsafe_allow_html=True,
    )
    if finding.code_mappings:
        st.dataframe(pd.DataFrame([item.model_dump() for item in finding.code_mappings]), width="stretch")


def render_review_tab(result):
    plan = st.session_state.alignment_plan
    if plan and plan.status == "final":
        st.warning("The alignment plan is final. Reopen it before changing review decisions.")
        if st.button("Reopen plan"):
            plan.status = "draft"
            plan.reviewer = None
            plan.finalized_at = None
            st.rerun()
        return
    finding_id = st.selectbox(
        "Finding",
        [item.id for item in result.findings],
        format_func=lambda value: next(
            f"{item.id}: {(item.local.id if item.local else '-')} -> {(item.reference.id if item.reference else '-')}"
            for item in result.findings if item.id == value
        ),
    )
    finding = next(item for item in result.findings if item.id == finding_id)
    render_finding_detail(finding)
    with st.form(f"review-{finding.id}"):
        status_options = ["accepted", "modified", "rejected", "unresolved", "no_action"]
        current_status = finding.review_status if finding.review_status in status_options else "accepted"
        status = st.radio("Decision", status_options, index=status_options.index(current_status), horizontal=True)
        actions = ["REUSE", "MAP", "KEEP_LOCAL_EXTENSION", "ADD_MISSING_ELEMENT"]
        suggested = finding.recommended_action or default_action(finding)
        action = st.selectbox("Action when accepted", actions, index=actions.index(suggested))
        note = st.text_area("Reviewer note", value=finding.review_note, max_chars=500)
        if st.form_submit_button("Save review", type="primary"):
            apply_review(result, finding.id, status, action if status in {"accepted", "modified"} else None, note)
            st.session_state.alignment_plan = build_alignment_plan(result)
            st.rerun()


def render_plan_tab(result):
    plan = st.session_state.alignment_plan or build_alignment_plan(result)
    st.session_state.alignment_plan = plan
    status_color = "green" if plan.status == "final" else "orange"
    st.markdown(f"**Plan status:** :{status_color}[{plan.status.upper()}]")
    if plan.decisions:
        st.dataframe(pd.DataFrame([item.model_dump() for item in plan.decisions]), width="stretch")
    else:
        st.info("No approved alignment decisions yet.")
    if plan.unresolved_finding_ids:
        st.warning("Unresolved: " + ", ".join(plan.unresolved_finding_ids))
    if plan.status == "draft":
        reviewer = st.text_input("Reviewer name or initials", key="plan_reviewer")
        if st.button("Finalize approved change set", type="primary", disabled=not reviewer.strip()):
            st.session_state.alignment_plan = finalize_alignment_plan(plan, reviewer)
            st.rerun()
    else:
        st.caption(f"Finalized by {plan.reviewer} at {plan.finalized_at.isoformat()}")
    st.download_button(
        "Download alignment plan JSON",
        plan.model_dump_json(indent=2),
        file_name="alignment-plan.json",
        mime="application/json",
    )


def render_answer_test(settings, matcher):
    local = st.session_state.local_structure
    reference = st.session_state.reference_structure
    plan = st.session_state.alignment_plan
    context = dsd_context(local, reference)
    digest = context_hash(context)
    st.markdown("**Fixed question**")
    st.info(FIXED_QUESTION)
    mode = st.radio("Capture method", ["In-app provider", "Paste workshop answers"], horizontal=True)

    if mode == "In-app provider":
        ready = matcher.is_ready()
        if not ready.ready:
            st.warning(ready.message)
        if st.button("Capture baseline", disabled=not ready.ready):
            try:
                st.session_state.baseline_answer = generate_assessment(FIXED_QUESTION, context, matcher)
                st.session_state.answer_snapshot = {
                    "provider": settings.provider,
                    "model": settings.openai_model if settings.provider == "openai" else settings.ollama_model,
                    "context_hash": digest,
                }
            except Exception as exc:
                st.error(str(exc))
        improved_disabled = not ready.ready or not plan or plan.status != "final" or not st.session_state.baseline_answer
        if st.button("Capture improved", disabled=improved_disabled):
            snapshot = st.session_state.answer_snapshot
            current_model = settings.openai_model if settings.provider == "openai" else settings.ollama_model
            if not snapshot or snapshot != {"provider": settings.provider, "model": current_model, "context_hash": digest}:
                st.error("Provider, model, or DSD context changed. Capture a new baseline.")
            else:
                improved_context = {**context, "reviewed_alignment_plan": plan.model_dump(mode="json")}
                try:
                    st.session_state.improved_answer = generate_assessment(FIXED_QUESTION, improved_context, matcher)
                except Exception as exc:
                    st.error(str(exc))
    else:
        provider = st.text_input("Captured provider", value="workshop-ai")
        model = st.text_input("Captured model", value="record model/version")
        baseline = st.text_area("Baseline answer", value=st.session_state.baseline_answer, height=150)
        improved = st.text_area("Improved answer", value=st.session_state.improved_answer, height=150)
        if st.button("Save pasted answers"):
            st.session_state.baseline_answer = baseline.strip()
            st.session_state.improved_answer = improved.strip()
            st.session_state.answer_snapshot = {"provider": provider, "model": model, "context_hash": digest}
            st.rerun()

    left, right = st.columns(2)
    with left:
        st.markdown("**Baseline answer**")
        st.write(st.session_state.baseline_answer or "Not captured")
    with right:
        st.markdown("**Improved answer**")
        st.write(st.session_state.improved_answer or "Not captured")

    if st.session_state.baseline_answer and st.session_state.improved_answer:
        with st.form("score_answers"):
            st.markdown("**Evidence-based scorecard**")
            baseline_scores, improved_scores = {}, {}
            for key, label in SCORE_LABELS.items():
                cols = st.columns([2, 1, 1])
                cols[0].write(label)
                baseline_scores[key] = cols[1].number_input(
                    f"Baseline {label}", 0, 2, 0, key=f"base-{key}", label_visibility="collapsed"
                )
                improved_scores[key] = cols[2].number_input(
                    f"Improved {label}", 0, 2, 0, key=f"improved-{key}", label_visibility="collapsed"
                )
            critical = st.text_area("Critical errors, one per line")
            evaluator_note = st.text_area("Evaluator note")
            if st.form_submit_button("Save measured result", type="primary"):
                snapshot = st.session_state.answer_snapshot or {}
                st.session_state.evaluation = create_evaluation(
                    provider=snapshot.get("provider", settings.provider),
                    model=snapshot.get("model", "unknown"),
                    capture_method="pasted" if mode != "In-app provider" else "in_app",
                    context_hash=digest,
                    baseline_answer=st.session_state.baseline_answer,
                    improved_answer=st.session_state.improved_answer,
                    baseline_scores=baseline_scores,
                    improved_scores=improved_scores,
                    critical_errors=[line.strip() for line in critical.splitlines() if line.strip()],
                    evaluator_note=evaluator_note,
                )
                st.rerun()
    evaluation = st.session_state.evaluation
    if evaluation:
        cols = st.columns(3)
        cols[0].metric("Baseline answer", f"{evaluation.baseline_total}/10")
        cols[1].metric("Improved answer", f"{evaluation.improved_total}/10")
        cols[2].metric("Measured delta", f"{evaluation.measured_delta:+d}")
        if evaluation.critical_errors:
            st.error("Critical errors: " + "; ".join(evaluation.critical_errors))
    else:
        st.caption("Measured result: Not measured")


def render_generate_and_prove(result, selected_reference):
    plan = st.session_state.alignment_plan
    if not plan or plan.status != "final":
        st.info("Finalize the approved change set before generating a revised DSD.")
        return
    st.caption(
        "Generation is deterministic: original XML plus approved structured changes. "
        "AI does not write or approve XML."
    )
    if st.button("Generate revised DSD", type="primary", key="generate_revised_dsd"):
        try:
            transformation = transform_dsd(
                st.session_state.original_xml,
                st.session_state.reference_xml,
                result,
                plan,
            )
            revised = parse_structure("revised-dsd.xml", transformation.revised_xml)
            revised_comparison = compare_structures(revised, st.session_state.reference_structure)
            technical = validate_revised_dsd(transformation.revised_xml, transformation)
            alignment = assess_reference_alignment(revised, st.session_state.reference_structure)
            before_after = build_before_after_report(result, revised_comparison, transformation)
            st.session_state.transformation = transformation
            st.session_state.technical_validation = technical
            st.session_state.reference_alignment = alignment
            st.session_state.revised_comparison = revised_comparison
            st.session_state.before_after = before_after
            st.rerun()
        except Exception as exc:
            st.error(f"Revised DSD generation failed safely: {exc}")

    transformation = st.session_state.transformation
    if transformation is None:
        return
    technical = st.session_state.technical_validation
    alignment = st.session_state.reference_alignment
    report = st.session_state.before_after

    st.markdown("### MVP SDMX Technical Checks")
    (st.success if technical.status == "PASS" else st.error)(f"Technical validity: {technical.status}")
    st.dataframe(pd.DataFrame([item.model_dump() for item in technical.checks]), hide_index=True, width="stretch")
    st.caption(technical.disclaimer)

    st.markdown("### Reference Alignment Assessment")
    st.markdown(f"**Reference alignment: {alignment.status.replace('_', ' ')}**")
    alignment_metrics = st.columns(3)
    alignment_metrics[0].metric("Outstanding code mappings", alignment.outstanding_code_mappings)
    alignment_metrics[1].metric("Unresolved semantic issues", alignment.unresolved_semantic_issues)
    alignment_metrics[2].metric("Local extensions retained", alignment.local_extensions_retained)
    st.caption(alignment.disclaimer)

    st.markdown("### Before and After")
    before_cols = st.columns(4)
    before_cols[0].metric("Exact before", report.before.exact)
    before_cols[1].metric("Exact after", report.after.exact, delta=report.exact_alignment_delta)
    before_cols[2].metric("Unresolved before", report.before.unresolved)
    before_cols[3].metric("Unresolved after", report.after.unresolved, delta=report.unresolved_delta)
    st.caption(
        f"{report.applied_changes} human-approved XML changes | "
        f"{report.deterministic_findings} deterministic findings | "
        f"{report.ai_assisted_findings} AI-assisted findings"
    )

    downloads = st.columns(3)
    downloads[0].download_button(
        "Download revised DSD",
        transformation.revised_xml,
        file_name="revised-dsd.xml",
        mime="application/xml",
        type="primary",
    )
    audit = export_audit_package(
        result,
        st.session_state.revised_comparison,
        plan,
        transformation,
        technical,
        alignment,
        report,
        selected_reference,
    )
    downloads[1].download_button(
        "Download audit JSON",
        audit,
        file_name="sdmx-alignment-audit.json",
        mime="application/json",
    )
    downloads[2].download_button(
        "Download change log CSV",
        export_change_log_csv(plan, transformation),
        file_name="sdmx-change-log.csv",
        mime="text/csv",
    )


def render_results(settings, matcher, selected_reference):
    result = st.session_state.comparison
    st.divider()
    st.subheader("2. Decide - Assess and Review")
    st.markdown(
        f"**Local:** `{result.local_dsd.agency_id}:{result.local_dsd.id}({result.local_dsd.version})`  &nbsp;  "
        f"**Reference:** `{result.reference_dsd.agency_id}:{result.reference_dsd.id}({result.reference_dsd.version})`"
    )
    metrics = st.columns(5)
    for col, label, value in zip(
        metrics,
        ["Exact", "Semantic suggestions", "Mapping required", "Missing", "Unresolved"],
        [result.summary.exact, result.summary.semantic_suggestions, result.summary.mapping_required, result.summary.missing, result.summary.unresolved],
    ):
        col.metric(label, value)
    tabs = st.tabs(["Alignment assessment", "Human review", "Approved changes", "Generate and prove", "Audit"])
    with tabs[0]:
        filters = st.multiselect(
            "Show statuses",
            ["exact", "partial", "mapping_required", "missing_local", "missing_reference", "possible_equivalent", "unresolved"],
            default=["exact", "partial", "mapping_required", "missing_local", "missing_reference", "possible_equivalent", "unresolved"],
        )
        rows = [row for row in finding_rows(result) if row["Status"] in filters]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        selected = st.selectbox("Inspect finding", [item.id for item in result.findings], key="inspect_finding")
        render_finding_detail(next(item for item in result.findings if item.id == selected))
    with tabs[1]:
        render_review_tab(result)
    with tabs[2]:
        render_plan_tab(result)
    with tabs[3]:
        render_generate_and_prove(result, selected_reference)
    with tabs[4]:
        plan = st.session_state.alignment_plan or build_alignment_plan(result)
        payload = export_evidence_package(result, plan, st.session_state.evaluation)
        st.download_button(
            "Download evidence package",
            payload,
            file_name="sdmx-alignment-evidence.json",
            mime="application/json",
            type="primary",
        )
        st.caption("Includes comparison evidence, reviewed alignment plan, and measured answer evaluation when available.")


initialize_state()
settings, matcher = provider_settings()
try:
    reference_library = load_reference_library(BASE_DIR / "reference_library" / "manifest.json")
except Exception as exc:
    reference_library = []
    st.error(f"Reference Standards Library could not be loaded: {exc}")

st.title("AI-Assisted SDMX Standards Alignment Workbench")
st.markdown(
    "<div class='status-line'>Discover evidence. Decide with expert control. Generate and prove a reviewed SDMX revision.</div>",
    unsafe_allow_html=True,
)
if reference_library:
    render_source_selection(reference_library, matcher)
if st.session_state.comparison:
    selected_reference = next(
        entry.metadata
        for entry in reference_library
        if entry.metadata.identity == st.session_state.selected_reference_identity
    )
    render_results(settings, matcher, selected_reference)
