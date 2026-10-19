"""The committed OpenAPI schema and the paths it names."""

import json
from pathlib import Path

from app.api.main import app

OPENAPI_FILE = Path(__file__).parents[2] / "docs" / "openapi.json"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def test_committed_schema_matches_the_app() -> None:
    committed = json.loads(OPENAPI_FILE.read_text(encoding="utf-8"))

    assert committed == app.openapi()


def test_schema_names_the_todo_paths_with_the_todos_tag() -> None:
    paths = app.openapi()["paths"]

    for path in ("/todos", "/todos/{todo_id}"):
        assert path in paths
        operations = [op for method, op in paths[path].items() if method in HTTP_METHODS]
        assert operations
        assert all("todos" in op["tags"] for op in operations)
