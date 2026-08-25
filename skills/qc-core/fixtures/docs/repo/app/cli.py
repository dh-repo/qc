"""Real CLI. The only flag is --help."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="qc-docs-fixture")
    parser.parse_args()
    print("ok")


if __name__ == "__main__":
    main()
