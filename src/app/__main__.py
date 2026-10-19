"""Command-line entry point: `python -m app --version` prints the installed version."""

import sys
from importlib.metadata import version

USAGE = "usage: python -m app --version"
EXIT_OK = 0
EXIT_USAGE = 2


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments != ["--version"]:
        print(USAGE, file=sys.stderr)
        return EXIT_USAGE
    print(f"app {version('app')}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
