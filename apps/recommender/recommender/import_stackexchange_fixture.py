from __future__ import annotations

import argparse
import json
from pathlib import Path

from recommender.content import DEFAULT_FIXTURE_PATH, import_stackexchange_posts_xml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Stack Exchange Data Dump Posts.xml into Papaya content fixture JSONL")
    parser.add_argument("posts_xml", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_FIXTURE_PATH)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--comments-xml", type=Path, default=None)
    parser.add_argument("--answers-per-thread", type=int, default=5)
    parser.add_argument("--comments-per-post", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    written = import_stackexchange_posts_xml(
        args.posts_xml,
        args.output,
        limit=args.limit,
        comments_xml=args.comments_xml,
        answers_per_thread=args.answers_per_thread,
        comments_per_post=args.comments_per_post,
    )
    print(json.dumps({"output": str(args.output), "rows": written}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
