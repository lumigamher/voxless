"""PyInstaller entry shim — invokes voxless.__main__:main as a proper package."""

from __future__ import annotations

import sys

from voxless.__main__ import main


if __name__ == "__main__":
    sys.exit(main())
