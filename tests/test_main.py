"""The command-line entry point `python -m app`."""

import subprocess
import sys
from importlib.metadata import version

import pytest

from app.__main__ import main
from tests.imports import APP_DIR, imported_modules

USAGE = "usage: python -m app --version\n"
VERSION_LINE = f"app {version('app')}\n"
FORBIDDEN_LAYERS = ("app.domain", "app.service", "app.repository", "app.api")


def test_version_flag_prints_the_installed_version(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--version"])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == VERSION_LINE
    assert captured.err == ""


@pytest.mark.parametrize(
    "argv",
    [[], ["--help"], ["x"], ["--version", "x"]],
)
def test_any_other_arguments_are_a_usage_error(
    capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    code = main(argv)

    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    assert captured.err == USAGE


@pytest.mark.parametrize(
    ("sys_argv", "expected"),
    [(["app", "--version"], 0), (["app"], 2)],
)
def test_main_without_argument_reads_sys_argv(
    monkeypatch: pytest.MonkeyPatch, sys_argv: list[str], expected: int
) -> None:
    monkeypatch.setattr(sys, "argv", sys_argv)

    assert main() == expected


def test_entry_point_imports_no_layer() -> None:
    offenders = {
        module
        for module in imported_modules(APP_DIR / "__main__.py")
        if any(module == layer or module.startswith(f"{layer}.") for layer in FORBIDDEN_LAYERS)
    }

    assert offenders == set()


@pytest.mark.parametrize(
    ("args", "expected_code", "expected_out", "expected_err"),
    [
        (["--version"], 0, VERSION_LINE, ""),
        ([], 2, "", USAGE),
    ],
)
def test_running_the_module_as_a_child_process(
    args: list[str],
    expected_code: int,
    expected_out: str,
    expected_err: str,
) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "app", *args],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == expected_code
    assert result.stdout == expected_out
    assert result.stderr == expected_err
