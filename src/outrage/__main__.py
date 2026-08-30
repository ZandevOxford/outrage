"""Dispatch the hook CLI while preserving the MCP server module fallback."""

import sys

from .cli import main as cli_main
from .server import main as server_main

if __name__ == "__main__":
    if sys.argv[1:2] == ["sessionstart"]:
        raise SystemExit(cli_main())
    raise SystemExit(server_main())
