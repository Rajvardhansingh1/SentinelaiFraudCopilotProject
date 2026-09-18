import ast
from pathlib import Path

AGENTS_DIR = Path(__file__).parent.parent.parent / "agents"
FORBIDDEN_MODULES = {"groq", "google.generativeai"}


def _imported_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_no_agent_file_imports_a_provider_sdk_directly():
    for path in AGENTS_DIR.rglob("*.py"):
        modules = _imported_modules(path.read_text())
        violations = modules & FORBIDDEN_MODULES
        assert not violations, f"{path} imports provider SDK directly: {violations}"
