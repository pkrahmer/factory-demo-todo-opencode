"""Checks of HTTP response bodies shared by the API test modules."""


def assert_only_detail(body: object, prefix: str = "") -> None:
    """Assert that `body` holds only a `detail` string, starting with `prefix`."""
    assert isinstance(body, dict)
    assert set(body) == {"detail"}
    assert isinstance(body["detail"], str)
    assert body["detail"].startswith(prefix)
