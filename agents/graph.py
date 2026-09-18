from langgraph.graph import END, StateGraph

from agents.extractor import OcrError, extract_fields, run_ocr
from agents.forensics import analyze as run_forensics
from agents.policy_checker import check_policy
from agents.report_writer import write_report
from agents.state import FraudCaseState


def _append_error(state: FraudCaseState, error: dict) -> list[dict]:
    return [*state.get("errors", []), error]


def extractor_node(state: FraudCaseState) -> FraudCaseState:
    session_id = state["session_id"]
    try:
        ocr_text = run_ocr(state["image_path"])
    except OcrError as exc:
        return {
            "ocr_text": None,
            "extracted_fields": None,
            "extraction_guardrails": None,
            "errors": _append_error(state, {"node": "extractor", "code": "ocr_failed", "message": str(exc)}),
        }

    fields, guardrails, error = extract_fields(session_id, ocr_text)
    return {
        "ocr_text": ocr_text,
        "extracted_fields": fields,
        "extraction_guardrails": guardrails,
        "errors": _append_error(state, error) if error else state.get("errors", []),
    }


def forensics_node(state: FraudCaseState) -> FraudCaseState:
    try:
        result = run_forensics(state["image_path"])
        return {"forensics_result": result.model_dump()}
    except Exception as exc:
        return {
            "forensics_result": None,
            "errors": _append_error(state, {"node": "forensics", "code": "forensics_failed", "message": str(exc)}),
        }


def policy_checker_node(state: FraudCaseState) -> FraudCaseState:
    verdict, guardrails, error = check_policy(state["session_id"], state.get("extracted_fields"))
    return {
        "policy_verdict": verdict,
        "policy_guardrails": guardrails,
        "errors": _append_error(state, error) if error else state.get("errors", []),
    }


def report_writer_node(state: FraudCaseState) -> FraudCaseState:
    report_text, guardrails, error = write_report(
        state["session_id"],
        state.get("extracted_fields"),
        state.get("forensics_result"),
        state.get("policy_verdict"),
    )
    return {
        "report_text": report_text,
        "report_guardrails": guardrails,
        "errors": _append_error(state, error) if error else state.get("errors", []),
    }


def build_graph():
    graph = StateGraph(FraudCaseState)
    graph.add_node("extractor", extractor_node)
    graph.add_node("forensics", forensics_node)
    graph.add_node("policy_checker", policy_checker_node)
    graph.add_node("report_writer", report_writer_node)

    graph.set_entry_point("extractor")
    graph.add_edge("extractor", "forensics")
    graph.add_edge("forensics", "policy_checker")
    graph.add_edge("policy_checker", "report_writer")
    graph.add_edge("report_writer", END)

    return graph.compile()


app = build_graph()
