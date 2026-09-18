import streamlit as st

from frontend.lib.dashboard_data import (
    cost_summary,
    fetch_calls,
    guardrail_catch_counts,
    hallucination_scores,
    latency_summary,
    traffic_by_operation,
)


def render() -> None:
    st.title("Evaluation Dashboard")
    st.caption("Every call logged by the proxy — guardrail catches, hallucination scores, cost, and latency.")

    if st.button("Refresh"):  # D-028: manual refresh, no polling loop
        st.session_state["dashboard_calls"] = fetch_calls()

    if "dashboard_calls" not in st.session_state:
        st.session_state["dashboard_calls"] = fetch_calls()

    calls = st.session_state["dashboard_calls"]

    if not calls:
        st.info("No calls logged yet — run something in the Red-Team Playground or Review Receipt first.")
        return

    cost = cost_summary(calls)
    latency = latency_summary(calls)
    catches = guardrail_catch_counts(calls)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total calls", len(calls))
    m2.metric("Guardrail catches", sum(catches.values()))
    m3.metric("Total cost", f"${cost['total_usd']:.4f}")
    m4.metric("Avg latency", f"{latency['avg_ms']:.0f} ms")

    st.divider()

    left, right = st.columns(2)
    with left:
        st.subheader("Traffic by operation")
        st.bar_chart(traffic_by_operation(calls))
    with right:
        st.subheader("Guardrail catches")
        st.write(catches or "No guardrail has triggered yet.")

    scores = hallucination_scores(calls)
    if scores:
        st.subheader("Hallucination scores")
        st.line_chart(scores)

    cost_col, latency_col = st.columns(2)
    with cost_col:
        st.subheader("Cost")
        st.write(cost)
    with latency_col:
        st.subheader("Latency")
        st.write(latency)
