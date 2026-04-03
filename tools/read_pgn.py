import argparse
import sys

from annotate.cli import strip_comments


def main() -> None:
    parser = argparse.ArgumentParser(description="Strip comments from a PGN file.")
    parser.add_argument("filename", help="Path to the .pgn file")
    args = parser.parse_args()

    with open(args.filename) as f:
        pgn_text = f.read()

    sys.stdout.write(strip_comments(pgn_text))


if __name__ == "__main__":
    main()
