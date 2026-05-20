from __future__ import annotations

import sys

from generate_recommendations import main, parse_args, run_generation

__all__ = ["main", "parse_args", "run_generation"]


if __name__ == "__main__":
    sys.exit(main())
