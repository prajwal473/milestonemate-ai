import ast
from pathlib import Path


APP = Path(__file__).resolve().parents[1] / "app"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_ai_modules_do_not_depend_on_payments():
    for path in (APP / "ai").rglob("*.py"):
        assert not any(name == "app.payments" or name.startswith("app.payments.") for name in _imports(path)), path


def test_shared_services_do_not_depend_on_ai_or_payments():
    for path in (APP / "services").rglob("*.py"):
        imports = _imports(path)
        assert not any(
            name == prefix or name.startswith(prefix + ".")
            for name in imports
            for prefix in ("app.ai", "app.payments")
        ), path
