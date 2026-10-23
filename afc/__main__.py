"""Entry point: sh bin/afc ..."""

import sys

from afc import cli


def main() -> None:
    sys.exit(cli.main(sys.argv[1:]))


if __name__ == "__main__":
    main()
