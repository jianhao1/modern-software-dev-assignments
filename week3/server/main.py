from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.mcp_server import run_http, run_stdio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Binance market data MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="MCP transport to run. Defaults to stdio.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if args.transport == "http":
            run_http()
        else:
            run_stdio()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
