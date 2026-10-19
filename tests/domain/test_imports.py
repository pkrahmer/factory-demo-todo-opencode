"""The domain stays free of frameworks and of the outer layers."""

from tests.imports import APP_DIR, imported_modules

DOMAIN_DIR = APP_DIR / "domain"
FORBIDDEN_FRAMEWORKS = {"fastapi", "pydantic", "sqlalchemy"}


def _is_forbidden(module: str) -> bool:
    top = module.split(".", maxsplit=1)[0]
    if top in FORBIDDEN_FRAMEWORKS:
        return True
    outside_domain = module != "app.domain" and not module.startswith("app.domain.")
    return top == "app" and module != "app" and outside_domain


def test_domain_imports_no_framework_and_no_outer_layer() -> None:
    sources = sorted(DOMAIN_DIR.rglob("*.py"))
    assert sources, f"no modules found under {DOMAIN_DIR}"

    offenders = {
        f"{path.relative_to(DOMAIN_DIR)}: {module}"
        for path in sources
        for module in imported_modules(path)
        if _is_forbidden(module)
    }

    assert offenders == set()
