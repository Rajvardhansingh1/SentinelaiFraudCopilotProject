from unittest.mock import patch

from frontend.lib.pipeline_client import run_on_receipt


def test_run_on_receipt_returns_error_state_instead_of_raising():
    with patch("frontend.lib.pipeline_client._get_graph") as mock_get_graph:
        mock_get_graph.return_value.invoke.side_effect = RuntimeError("boom")
        state = run_on_receipt("sess-1", "fake.jpg")
    assert state["errors"][0]["code"] == "pipeline_failed"
    assert state["extracted_fields"] is None
    assert state["report_text"] is None
