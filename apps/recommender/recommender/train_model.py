from __future__ import annotations

import sys

from train_model import main, parse_args, run_training

__all__ = ["main", "parse_args", "run_training"]


if __name__ == "__main__":
    sys.exit(main())
