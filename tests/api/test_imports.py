"""Only the composition root of the API chooses the concrete repository."""

from tests.imports import APP_DIR, belongs_to, imported_modules

API_DIR = APP_DIR / "api"


def _is_repository(module: str) -> bool:
    return belongs_to(module, "app.repository")


def test_only_main_imports_the_repository_layer() -> None:
    sources = sorted(API_DIR.rglob("*.py"))
    assert sources, f"no modules found under {API_DIR}"

    offenders = {
        f"{path.relative_to(API_DIR)}: {module}"
        for path in sources
        if path != API_DIR / "main.py"
        for module in imported_modules(path)
        if _is_repository(module)
    }

    assert offenders == set()
