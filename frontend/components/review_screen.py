import tempfile
import uuid
from pathlib import Path

import streamlit as st

from frontend.db.models import ReviewDecision
from frontend.db.session import get_session
from frontend.lib.pipeline_client import run_on_receipt
from frontend.lib.session import get_session_id

RECEIPTS_DIR = Path(__file__).parent.parent.parent / "data" / "synthetic_receipts"

SAMPLE_RECEIPTS = [
    {"label": "Sample: genuine receipt", "path": str(RECEIPTS_DIR / "genuine" / "genuine_001.jpg")},
    {"label": "Sample: tampered receipt", "path": str(RECEIPTS_DIR / "tampered" / "tampered_001.jpg")},
    {"label": "Sample: hidden attack in receipt", "path": str(RECEIPTS_DIR / "adversarial" / "adversarial_001.jpg")},
]


def compute_display(state: dict) -> dict:
    """Pure logic, unit-testable without Streamlit — mirrors redteam_playground.handle_response."""
    report_guardrails = state.get("report_guardrails") or {}
    hallucination = report_guardrails.get("hallucination") or {}
    hallucination_score = hallucination.get("score", 0.0)
    confidence = 1 - hallucination_score  # D-026

    policy_verdict = state.get("policy_verdict") or {}
    verdict = "non_compliant" if not policy_verdict.get("compliant", True) else "compliant"

    # D-037: surface the SentinelAI <-> Fraud Copilot connection — OCR'd receipt text
    # goes through the same injection detector the Red-Team Playground exercises.
    extraction_guardrails = state.get("extraction_guardrails") or {}
    ocr_injection = extraction_guardrails.get("injection") or {}
    injection_during_extraction = bool(ocr_injection.get("flagged")) or any(
        e.get("code") == "injection_detected" for e in state.get("errors", [])
    )

    return {
        "extracted_fields": state.get("extracted_fields"),
        "forensics_result": state.get("forensics_result"),
        "policy_verdict": policy_verdict,
        "report_text": state.get("report_text"),
        "verdict": verdict,
        "confidence": confidence,
        "hallucination_pct": hallucination_score,
        "errors": state.get("errors", []),
        "injection_during_extraction": injection_during_extraction,
        "injection_matched_patterns": ocr_injection.get("matched_patterns", []),
    }


def record_review_decision(session_id: str, receipt_ref: str, display: dict, human_decision: str, notes: str) -> None:
    db = get_session()
    try:
        db.add(
            ReviewDecision(
                session_id=session_id,
                receipt_ref=receipt_ref,
                system_verdict=display["verdict"],
                confidence=display["confidence"],
                hallucination_pct=display["hallucination_pct"],
                human_decision=human_decision,
                reviewer_notes=notes or None,
            )
        )
        db.commit()
    finally:
        db.close()


def render() -> None:
    st.title("Review Receipt")
    st.caption("Upload or pick a receipt. The agent pipeline extracts, forensically checks, and policy-checks it — you make the call.")
    session_id = get_session_id()

    receipt_path = None
    st.write("**Start with a sample, or upload your own:**")
    cols = st.columns(len(SAMPLE_RECEIPTS))
    for col, sample in zip(cols, SAMPLE_RECEIPTS):
        if col.button(sample["label"], use_container_width=True):
            receipt_path = sample["path"]
            st.session_state["review_receipt_path"] = receipt_path

    uploaded = st.file_uploader("Or upload a receipt", type=["png", "jpg", "jpeg"])
    if uploaded is not None:
        # Security: never build the on-disk path from the client-supplied filename
        # (path traversal / temp-dir collision risk — client controls uploaded.name).
        suffix = Path(uploaded.name).suffix.lower()
        if suffix not in (".png", ".jpg", ".jpeg"):
            suffix = ".jpg"
        tmp_path = Path(tempfile.gettempdir()) / f"{uuid.uuid4().hex}{suffix}"
        tmp_path.write_bytes(uploaded.getvalue())
        st.session_state["review_receipt_path"] = str(tmp_path)

    receipt_path = st.session_state.get("review_receipt_path")
    if not receipt_path:
        st.info("Pick a sample above or upload a receipt to begin.")
        return

    st.caption(f"Loaded: `{Path(receipt_path).name}`")
    if st.button("Run analysis", type="primary"):
        with st.spinner("Extracting fields, checking forensics, running policy and hallucination checks..."):
            state = run_on_receipt(session_id, receipt_path)
        st.session_state["review_state"] = state

    state = st.session_state.get("review_state")
    if not state:
        return

    display = compute_display(state)

    st.divider()

    if display["injection_during_extraction"]:
        patterns = ", ".join(display["injection_matched_patterns"]) or "a known attack pattern"
        st.error(
            f"🛡️ SentinelAI's injection detector — the same engine protecting the Red-Team "
            f"Playground — caught a prompt injection hidden in this receipt's scanned text "
            f"(matched: {patterns}) before it reached the policy checker."
        )

    with st.container(border=True):
        st.subheader("Extraction evidence")
        st.write(display["extracted_fields"])

    with st.container(border=True):
        st.subheader("Forensics evidence")
        st.write(display["forensics_result"])

    with st.container(border=True):
        st.subheader("Policy evidence")
        st.write(display["policy_verdict"])

    with st.container(border=True):
        st.subheader("System Assessment (not a decision)")
        m1, m2, m3 = st.columns(3)
        m1.metric("Verdict", display["verdict"])
        m2.metric("Confidence", f"{display['confidence']:.0%}")
        m3.metric("Hallucination %", f"{display['hallucination_pct']:.1%}")
        st.caption("This is model output, not a final decision. A human must approve or reject below.")
        if display["report_text"]:
            st.write(display["report_text"])

    with st.container(border=True):
        st.subheader("Human Review — Final Decision")
        st.warning("The system above never auto-approves or auto-rejects. You decide.")
        notes = st.text_area("Reviewer notes (optional)")
        col1, col2 = st.columns(2)
        approve = col1.button("Approve", type="primary", use_container_width=True)
        reject = col2.button("Reject", use_container_width=True)
        if approve or reject:
            decision = "approved" if approve else "rejected"
            record_review_decision(session_id, receipt_path, display, decision, notes)
            st.success(f"Recorded: {decision} by reviewer.")
