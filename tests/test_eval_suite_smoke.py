import pytest
import requests

from agents.proxy_client import PROXY_BASE_URL
from scripts.run_eval_suite import run_suite


def _proxy_reachable() -> bool:
    try:
        requests.get(f"{PROXY_BASE_URL}/health", timeout=1.0)
        return True
    except requests.RequestException:
        return False


@pytest.mark.skipif(not _proxy_reachable(), reason="no live SentinelAI proxy reachable at PROXY_BASE_URL")
def test_eval_suite_smoke_run_on_three_samples(tmp_path):
    report = run_suite(limit=3, out_dir=tmp_path)
    assert report["metrics"]["sample_count"] == 3
    from pathlib import Path

    assert Path(report["json_path"]).is_file()
    assert Path(report["md_path"]).is_file()
