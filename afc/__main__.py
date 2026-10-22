"""Entry point: python3 -m afc ..."""

import sys

from afc import cli


def main() -> None:
    sys.exit(cli.main(sys.argv[1:]))


if __name__ == "__main__":
    main()
