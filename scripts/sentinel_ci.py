"""Phase 8 (D-047): CI entrypoint for running SentinelAI's security tests
against a target and enforcing an explicitly configured failure policy.

Talks to a *running* SentinelAI instance over plain HTTP only — it never
imports provider SDKs and never needs an API key itself. The target instance
holds its own provider credentials server-side (D-041/D-002); nothing here
requires putting a secret in source code or in CI config.

Usage:
    python -m scripts.sentinel_ci --target http://localhost:8000
    python -m scripts.sentinel_ci --target http://localhost:8000 \\
        --category prompt_injection,jailbreak \\
        --fail-on-severity critical,high \\
        --check-regression --max-regressions 0 \\
        --json-out results.json --md-out summary.md

    # Phase 8/9 (D-058): a real CI pipeline should use a persistent,
    # project-scoped API key (created once via POST /v1/projects/{id}/api-keys)
    # instead of the default one-off throwaway account:
    python -m scripts.sentinel_ci --target http://localhost:8000 \\
        --api-key "$SENTINEL_API_KEY" --project-id "$SENTINEL_PROJECT_ID"
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

import requests

from proxy.ci import CIPolicy, evaluate, format_human_summary


def _bootstrap_auth(target: str) -> dict:
    """Phase 2 (D-055): every request now needs a bearer token. Falls back to
    signing up a throwaway user + project each run when no persistent
    credential is configured (SENTINEL_API_KEY / --api-key), keeping
    sentinel_ci's original "no setup required" behavior intact for a first
    run — Phase 8 (D-058) prefers a real, persistent project association
    once one exists."""
    email = f"ci-{secrets.token_hex(8)}@sentinelai.local"
    password = secrets.token_hex(16)
    signup = requests.post(f"{target}/v1/auth/signup", json={"email": email, "password": password}, timeout=30)
    signup.raise_for_status()
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    project = requests.post(f"{target}/v1/projects", json={"name": "CI"}, headers=headers, timeout=30)
    project.raise_for_status()
    return {"headers": headers, "project_id": project.json()["id"]}


def _resolve_auth(target: str, api_key: str | None, project_id: int | None) -> dict:
    """Phase 8/9 (D-058): a persistent, project-scoped API key
    (--api-key/SENTINEL_API_KEY + --project-id/SENTINEL_PROJECT_ID) is the
    credential a real CI pipeline should use — associated with one project
    across every run, unlike the throwaway-account fallback below."""
    if api_key and project_id:
        return {"headers": {"Authorization": f"ApiKey {api_key}"}, "project_id": project_id}
    if api_key or project_id:
        raise SystemExit("--api-key and --project-id must be given together (or neither, to bootstrap a throwaway project).")
    return _bootstrap_auth(target)


def _fetch_results(target: str, category: str | None, auth: dict) -> list[dict]:
    params = {"project_id": auth["project_id"], "source": "ci_cd"}
    if category:
        params["category"] = category
    resp = requests.post(f"{target}/v1/findings/sync", params=params, headers=auth["headers"], timeout=120)
    resp.raise_for_status()
    return resp.json()["results"]


def _fetch_regression_report(target: str, auth: dict) -> dict | None:
    resp = requests.get(
        f"{target}/v1/regression-report", params={"project_id": auth["project_id"]}, headers=auth["headers"], timeout=60
    )
    if resp.status_code == 200:
        return resp.json()
    if resp.status_code in (404, 409):
        detail = resp.json().get("detail", {})
        print(f"Regression check skipped: {detail.get('message', resp.text)}", file=sys.stderr)
        return None
    resp.raise_for_status()
    return None  # unreachable, satisfies type checkers


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", required=True, help="Base URL of a running SentinelAI proxy, e.g. http://localhost:8000")
    parser.add_argument(
        "--api-key", default=os.environ.get("SENTINEL_API_KEY"),
        help="Persistent project-scoped API key (or SENTINEL_API_KEY env var). Requires --project-id. "
             "Without one, a throwaway user+project is created for this run only."
    )
    parser.add_argument(
        "--project-id", type=int, default=(int(v) if (v := os.environ.get("SENTINEL_PROJECT_ID")) else None),
        help="Project to associate with --api-key (or SENTINEL_PROJECT_ID env var)."
    )
    parser.add_argument("--category", default=None, help="Comma-separated test categories to run (default: all)")
    parser.add_argument("--fail-on-status", default="FAIL", help="Comma-separated statuses that count toward failure (default: FAIL)")
    parser.add_argument("--fail-on-severity", default=None, help="Comma-separated severities that count toward failure (default: any severity)")
    parser.add_argument("--max-failures", type=int, default=0, help="Fail only if more than this many results match the policy (default: 0)")
    parser.add_argument("--check-regression", action="store_true", help="Also fetch the latest regression report and factor it into the policy")
    parser.add_argument("--max-regressions", type=int, default=0, help="Fail only if more than this many regressions (default: 0; requires --check-regression)")
    parser.add_argument("--json-out", default=None, help="Write machine-readable results + verdict to this file")
    parser.add_argument("--md-out", default=None, help="Write the human-readable Markdown summary to this file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    auth = _resolve_auth(args.target, args.api_key, args.project_id)
    results = _fetch_results(args.target, args.category, auth)

    regression_report = None
    if args.check_regression:
        regression_report = _fetch_regression_report(args.target, auth)

    policy = CIPolicy(
        fail_on_statuses=frozenset(s.strip() for s in args.fail_on_status.split(",") if s.strip()),
        fail_on_severities=frozenset(s.strip() for s in args.fail_on_severity.split(",") if s.strip()) if args.fail_on_severity else None,
        max_failures=args.max_failures,
        max_regressions=args.max_regressions,
    )
    verdict = evaluate(results, policy, regression_report)
    summary = format_human_summary(results, verdict, args.target)
    print(summary)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps({"results": results, "verdict": verdict}, indent=2, default=str))
    if args.md_out:
        Path(args.md_out).write_text(summary)

    return 1 if verdict["should_fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
