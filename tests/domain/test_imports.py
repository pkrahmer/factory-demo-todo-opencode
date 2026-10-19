"""The domain stays free of frameworks and of the outer layers."""

import ast
from pathlib import Path

import app

DOMAIN_DIR = Path(app.__file__).parent / "domain"
FORBIDDEN_FRAMEWORKS = {"fastapi", "pydantic", "sqlalchemy"}


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    package = ["app", "domain", *path.relative_to(DOMAIN_DIR).parent.parts]
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                base = node.module or ""
            else:
                anchor = package[: len(package) - (node.level - 1)]
                base = ".".join([*anchor, *([node.module] if node.module else [])])
            modules.append(base)
            modules.extend(f"{base}.{alias.name}" for alias in node.names)
    return modules


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
        for module in _imported_modules(path)
        if _is_forbidden(module)
    }

    assert offenders == set()
