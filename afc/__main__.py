"""Entry point: python3 -m afc ..."""

import importlib.util
import sys


def main() -> None:
    # afc.cli arrives in a later task; until then there is nothing to run.
    if importlib.util.find_spec("afc.cli") is None:
        sys.exit("afc: CLI is not available yet")
    from afc import cli

    sys.exit(cli.main(sys.argv[1:]))


if __name__ == "__main__":
    main()
