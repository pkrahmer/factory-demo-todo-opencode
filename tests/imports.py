"""Reading the imports of a module under `src/app`, for the tests of the layer rules."""

import ast
from pathlib import Path

import app

APP_DIR = Path(app.__file__).parent


def imported_modules(path: Path) -> list[str]:
    """Return the absolute names of every module and name imported by the source at `path`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    package = ["app", *path.relative_to(APP_DIR).parent.parts]
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


def belongs_to(module: str, package: str) -> bool:
    """Return whether `module` is `package` itself or one of its submodules."""
    return module == package or module.startswith(f"{package}.")
