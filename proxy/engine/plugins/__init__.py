"""Importing this package registers every built-in plugin's tests. Import it
once (proxy/engine/plugins) wherever the full test suite is needed."""

from proxy.engine.plugins import agent_policy_tests  # noqa: F401
from proxy.engine.plugins import injection_tests  # noqa: F401
from proxy.engine.plugins import jailbreak_tests  # noqa: F401
from proxy.engine.plugins import sensitive_disclosure_tests  # noqa: F401
from proxy.engine.plugins import system_prompt_extraction_tests  # noqa: F401
from proxy.engine.plugins import unsafe_output_tests  # noqa: F401
