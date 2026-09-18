"""Runs the Phase 4 LangGraph pipeline over the labeled synthetic dataset and computes
the 7 metrics spec.md names. Metrics are measured, never claimed without running this
(CLAUDE.md section 10).

Usage: python -m scripts.run_eval_suite --limit 5
"""

import argparse
import csv
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
LABELS_PATH = ROOT / "data" / "labels.csv"
RECEIPTS_DIR = ROOT / "data" / "synthetic_receipts"
DEFAULT_OUT_DIR = ROOT / "eval_reports"

# Phase 4's tamper_likelihood is categorical (low/medium/high); this cutoff turns it
# binary for precision/recall. Consumed here, not decided here (PHASE5_PLAN.md §9 item 4).
TAMPER_POSITIVE_LEVELS = {"medium", "high"}


def load_labels(path: Path = LABELS_PATH) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def field_extraction_accuracy(results: list[dict]) -> dict:
    fields = ["vendor", "date", "total"]
    correct = {f: 0 for f in fields}
    total = 0
    for r in results:
        if r["extracted_fields"] is None:
            continue
        total += 1
        for f in fields:
            expected = r["ground_truth"][f]
            actual = r["extracted_fields"].get(f)
            if str(actual) == str(expected):
                correct[f] += 1
    return {f: (correct[f] / total if total else 0.0) for f in fields}


def tamper_detection_precision_recall(results: list[dict]) -> dict:
    tp = fp = fn = tn = 0
    for r in results:
        actual_tampered = r["ground_truth"]["genuine_or_tampered"] == "tampered"
        forensics = r.get("forensics_result")
        predicted_tampered = forensics is not None and forensics["tamper_likelihood"] in TAMPER_POSITIVE_LEVELS
        if actual_tampered and predicted_tampered:
            tp += 1
        elif actual_tampered and not predicted_tampered:
            fn += 1
        elif not actual_tampered and predicted_tampered:
            fp += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {"precision": precision, "recall": recall, "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def policy_violation_accuracy(results: list[dict]) -> float:
    correct = 0
    total = 0
    for r in results:
        verdict = r.get("policy_verdict")
        if verdict is None:
            continue
        total += 1
        expected = r["ground_truth"]["expected_policy_violation"] == "True"
        actual = not verdict.get("compliant", True)
        if actual == expected:
            correct += 1
    return correct / total if total else 0.0


def hallucination_distribution(results: list[dict]) -> dict:
    scores = [
        (r.get("report_guardrails") or {})["hallucination"]["score"]
        for r in results
        if (r.get("report_guardrails") or {}).get("hallucination")
    ]
    if not scores:
        return {"count": 0}
    return {
        "count": len(scores),
        "mean": statistics.mean(scores),
        "median": statistics.median(scores),
        "min": min(scores),
        "max": max(scores),
        "note": "D-017 lexical-overlap MVP heuristic, not a calibrated NLI hallucination rate",
    }


def end_to_end_latency(results: list[dict]) -> dict:
    latencies = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]
    if not latencies:
        return {"count": 0}
    sorted_lat = sorted(latencies)
    p50 = sorted_lat[len(sorted_lat) // 2]
    p95 = sorted_lat[int(len(sorted_lat) * 0.95)] if len(sorted_lat) > 1 else sorted_lat[0]
    return {"count": len(latencies), "mean_ms": statistics.mean(latencies), "p50_ms": p50, "p95_ms": p95}


def injection_catch_rate(holdout_prompts: list[str], check_injection_fn) -> dict:
    if not holdout_prompts:
        return {"count": 0}
    caught = sum(1 for p in holdout_prompts if check_injection_fn(p).flagged)
    return {"count": len(holdout_prompts), "caught": caught, "catch_rate": caught / len(holdout_prompts)}


def run_pipeline_on_sample(row: dict, graph) -> dict:
    image_path = str(RECEIPTS_DIR / row["filename"])
    start = time.monotonic()
    try:
        state = graph.invoke({"session_id": f"eval-{row['sample_id']}", "image_path": image_path, "errors": []})
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            "sample_id": row["sample_id"],
            "ground_truth": row,
            "extracted_fields": state.get("extracted_fields"),
            "forensics_result": state.get("forensics_result"),
            "policy_verdict": state.get("policy_verdict"),
            "report_guardrails": state.get("report_guardrails"),
            "errors": state.get("errors", []),
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        return {
            "sample_id": row["sample_id"],
            "ground_truth": row,
            "extracted_fields": None,
            "forensics_result": None,
            "policy_verdict": None,
            "report_guardrails": None,
            "errors": [{"node": "eval_suite", "code": "sample_failed", "message": str(exc)}],
            "latency_ms": None,
        }


def run_suite(limit: int | None = None, out_dir: Path = DEFAULT_OUT_DIR) -> dict:
    from agents.graph import build_graph
    from proxy.middleware.injection_detector import check_injection

    rows = load_labels()
    if limit:
        rows = rows[:limit]

    graph = build_graph()
    results = [run_pipeline_on_sample(row, graph) for row in rows]

    holdout_path = ROOT / "data" / "holdout_injection_prompts.json"
    holdout_prompts = json.loads(holdout_path.read_text())["prompts"] if holdout_path.exists() else []

    metrics = {
        "field_extraction_accuracy": field_extraction_accuracy(results),
        "tamper_detection": tamper_detection_precision_recall(results),
        "policy_violation_accuracy": policy_violation_accuracy(results),
        "hallucination_distribution": hallucination_distribution(results),
        "end_to_end_latency": end_to_end_latency(results),
        "injection_catch_rate": injection_catch_rate(holdout_prompts, check_injection),
        "sample_count": len(results),
        "failed_samples": [r["sample_id"] for r in results if r["extracted_fields"] is None and r["errors"]],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"{timestamp}_eval_report.json"
    md_path = out_dir / f"{timestamp}_eval_report.md"

    json_path.write_text(json.dumps({"metrics": metrics, "results": results}, indent=2, default=str))
    md_path.write_text(_render_markdown(metrics))

    return {"metrics": metrics, "json_path": str(json_path), "md_path": str(md_path)}


def _render_markdown(metrics: dict) -> str:
    lines = ["# Evaluation Report", "", f"Samples: {metrics['sample_count']}", ""]
    lines.append("## Field Extraction Accuracy")
    for field, acc in metrics["field_extraction_accuracy"].items():
        lines.append(f"- {field}: {acc:.2%}")
    lines.append("")
    lines.append("## Tamper Detection")
    td = metrics["tamper_detection"]
    lines.append(f"- precision: {td['precision']:.2%}, recall: {td['recall']:.2%}")
    lines.append("")
    lines.append(f"## Policy Violation Accuracy: {metrics['policy_violation_accuracy']:.2%}")
    lines.append("")
    lines.append("## Hallucination Distribution (D-017 heuristic, not calibrated NLI)")
    lines.append(f"```\n{json.dumps(metrics['hallucination_distribution'], indent=2)}\n```")
    lines.append("")
    lines.append("## End-to-End Latency")
    lines.append(f"```\n{json.dumps(metrics['end_to_end_latency'], indent=2)}\n```")
    lines.append("")
    lines.append("## Injection Catch Rate")
    lines.append(f"```\n{json.dumps(metrics['injection_catch_rate'], indent=2)}\n```")
    if metrics["failed_samples"]:
        lines.append("")
        lines.append(f"## Failed Samples: {metrics['failed_samples']}")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()
    report = run_suite(limit=args.limit, out_dir=args.out_dir)
    print(f"Wrote {report['json_path']} and {report['md_path']}")
