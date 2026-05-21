from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import html
import json
from pathlib import Path
import random
from typing import Any

import polars as pl

from recommender.content import DEFAULT_FIXTURE_PATH, ThreadContentFixture, load_stackexchange_fixture
from recommender.data import BehaviorData, BusinessData

BIG_TEST_SEED = 9400
EDGE_CASE_SEEDS = {
    "sparse_noisy": 9401,
    "fresh_content": 9402,
    "feedback_heavy": 9403,
}


PROFILE_WEIGHTS = {
    "backend-heavy": {"backend": 0.78, "frontend": 0.07, "devops": 0.08, "mixed": 0.05, "noise": 0.02},
    "frontend-heavy": {"backend": 0.07, "frontend": 0.78, "devops": 0.08, "mixed": 0.05, "noise": 0.02},
    "devops-heavy": {"backend": 0.10, "frontend": 0.06, "devops": 0.76, "mixed": 0.06, "noise": 0.02},
    "mixed-fullstack": {"backend": 0.29, "frontend": 0.29, "devops": 0.24, "mixed": 0.16, "noise": 0.02},
    "noisy/low-signal": {"backend": 0.23, "frontend": 0.23, "devops": 0.23, "mixed": 0.11, "noise": 0.20},
}

THREAD_CATEGORIES = {
    "backend": ["go", "backend", "postgresql"],
    "frontend": ["frontend", "react", "nextjs"],
    "devops": ["devops", "docker", "linux"],
    "mixed": ["fullstack", "architecture", "integration"],
    "noise": ["offtopic", "career", "tools"],
}

THREAD_TITLE_PARTS = {
    "backend": ["Go profiling", "PostgreSQL indexes", "Gin middleware", "Backend caching", "SQL migrations"],
    "frontend": ["React hooks", "Next.js routing", "Frontend forms", "Chakra UI", "Client cache"],
    "devops": ["Docker compose", "Linux logs", "CI pipeline", "Redis ops", "Deployment rollback"],
    "mixed": ["Fullstack auth flow", "API contract", "Realtime updates", "Forum architecture", "Search UX"],
    "noise": ["Desk setup", "Conference notes", "Editor themes", "Career path", "Tooling chatter"],
}


@dataclass(frozen=True)
class SyntheticScale:
    users: int = 50
    threads: int = 1000
    posts_min: int = 5000
    posts_max: int = 50000
    comments_min: int = 5000
    comments_max: int = 250000
    events_min: int = 60000
    events_max: int = 250000
    min_user_events: int = 60
    posts_per_thread_min: int = 5
    posts_per_thread_max: int = 50
    comments_per_post_min: int = 1
    comments_per_post_max: int = 5
    fixture_limit: int = 1000

    @classmethod
    def smoke(cls) -> "SyntheticScale":
        return cls(
            users=20,
            threads=200,
            posts_min=1000,
            posts_max=1200,
            comments_min=4000,
            comments_max=6000,
            events_min=12000,
            events_max=18000,
            min_user_events=30,
            posts_per_thread_min=5,
            posts_per_thread_max=7,
            comments_per_post_min=4,
            comments_per_post_max=5,
            fixture_limit=200,
        )


@dataclass
class SyntheticForumDataset:
    business: BusinessData
    behavior: BehaviorData
    user_profiles: pl.DataFrame
    thread_profiles: pl.DataFrame
    report: dict[str, Any]


def generate_synthetic_forum_dataset(
    scale: SyntheticScale = SyntheticScale(),
    seed: int = 42,
    now: datetime | None = None,
    fixture_path: Path | None = None,
) -> SyntheticForumDataset:
    """Generate deterministic forum activity that looks like real user journeys."""
    rng = random.Random(seed)
    now = now or datetime(2026, 5, 19, 12, tzinfo=timezone.utc)
    start = now - timedelta(days=75)
    fixture = load_stackexchange_fixture(fixture_path or DEFAULT_FIXTURE_PATH)

    users, user_profiles = _generate_users(scale.users, start, rng)
    threads, thread_profiles, fixtures_by_thread = _generate_threads(scale.threads, users, user_profiles, start, rng, fixture)
    posts = _generate_posts(scale, threads, thread_profiles, user_profiles, start, rng, fixtures_by_thread)
    comments = _generate_comments(scale, posts, thread_profiles, user_profiles, rng, fixtures_by_thread)
    likes, like_events = _generate_likes(posts, comments, user_profiles, rng)
    journey_events = _generate_journey_events(scale, users, user_profiles, threads, thread_profiles, now, rng)
    content_events = _content_events(posts, comments)

    events = sorted(content_events + like_events + journey_events, key=lambda row: row["created_at"])
    events_frame = pl.DataFrame(events)
    user_thread_daily = _user_thread_daily(events_frame)
    recommendation_daily = _recommendation_daily(events)

    business = BusinessData(
        users=pl.DataFrame(users),
        threads=pl.DataFrame(threads),
        posts=pl.DataFrame(posts),
        comments=pl.DataFrame(comments),
        likes=pl.DataFrame(likes),
    )
    behavior = BehaviorData(
        events=events_frame,
        user_thread_daily=user_thread_daily,
        recommendation_daily=recommendation_daily,
    )
    report = _build_report(business, behavior, user_profiles, thread_profiles)
    return SyntheticForumDataset(
        business=business,
        behavior=behavior,
        user_profiles=pl.DataFrame(user_profiles),
        thread_profiles=pl.DataFrame(thread_profiles),
        report=report,
    )


def validate_synthetic_forum_dataset(
    dataset: SyntheticForumDataset,
    scale: SyntheticScale = SyntheticScale(),
) -> list[str]:
    errors: list[str] = []
    business = dataset.business
    behavior = dataset.behavior

    if business.users.height != scale.users:
        errors.append(f"expected {scale.users} users, got {business.users.height}")
    if business.threads.height != scale.threads:
        errors.append(f"expected {scale.threads} threads, got {business.threads.height}")
    if not scale.posts_min <= business.posts.height <= scale.posts_max:
        errors.append(f"posts must be in [{scale.posts_min}, {scale.posts_max}], got {business.posts.height}")
    if not scale.comments_min <= business.comments.height <= scale.comments_max:
        errors.append(f"comments must be in [{scale.comments_min}, {scale.comments_max}], got {business.comments.height}")
    if not scale.events_min <= behavior.events.height <= scale.events_max:
        errors.append(f"events must be in [{scale.events_min}, {scale.events_max}], got {behavior.events.height}")

    event_counts = behavior.events.group_by("user_id").agg(pl.len().alias("events_count"))
    low_signal_users = event_counts.filter(pl.col("events_count") < scale.min_user_events)
    if low_signal_users.height:
        errors.append(f"users below {scale.min_user_events} events: {low_signal_users.get_column('user_id').to_list()}")

    thread_counts = dataset.thread_profiles.group_by("topic").agg(pl.len().alias("threads"))
    topics = set(thread_counts.get_column("topic").to_list())
    if {"backend", "frontend", "devops", "mixed", "noise"} - topics:
        errors.append("dataset must include backend, frontend, devops, mixed, and noise topics")

    event_types = set(behavior.events.get_column("event_type").to_list())
    required_events = {
        "thread_viewed",
        "post_created",
        "comment_created",
        "post_liked",
        "comment_liked",
        "recommendation_impression",
        "recommendation_clicked",
    }
    missing_events = required_events - event_types
    if missing_events:
        errors.append(f"missing event types: {sorted(missing_events)}")

    if business.threads.filter(pl.col("title").str.strip_chars() == "").height:
        errors.append("threads must not have empty titles")
    if business.threads.filter(pl.col("content").str.strip_chars() == "").height:
        errors.append("threads must not have empty real-content text")
    if business.threads.filter(pl.col("categories").list.len() == 0).height:
        errors.append("threads must have categories or tags")
    if not _posts_have_existing_threads(business.posts, business.threads):
        errors.append("some posts reference missing threads")
    if not _comments_have_existing_posts(business.comments, business.posts):
        errors.append("some comments reference missing posts")
    real_profiles = dataset.thread_profiles.filter(pl.col("source") != "synthetic-template")
    if real_profiles.height and real_profiles.filter((pl.col("license") == "") | (pl.col("attribution") == "")).height:
        errors.append("real-content fixture rows must include license and attribution")

    if not _posts_are_after_threads(business.posts, business.threads):
        errors.append("some posts are earlier than their threads")
    if not _comments_are_after_posts(business.comments, business.posts):
        errors.append("some comments are earlier than their posts")
    if behavior.recommendation_daily.is_empty():
        errors.append("recommendation_daily must contain feedback loop aggregates")

    return errors


def build_synthetic_split_report(
    dataset: SyntheticForumDataset,
    half_life_days: float = 21.0,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Explain which future interactions are held out for model evaluation."""
    from recommender.etl import prepare_data

    prepared = prepare_data(dataset.business, dataset.behavior, half_life_days=half_life_days, now=now)
    train_pairs = _pair_set(prepared.train_interactions)
    test_pairs = _pair_set(prepared.test_interactions)
    leaked_pairs = sorted(train_pairs & test_pairs)

    test_with_topics = (
        prepared.test_interactions.join(dataset.thread_profiles, on="thread_id", how="left")
        if prepared.test_interactions.height
        else prepared.test_interactions.with_columns(pl.lit(None).alias("topic"))
    )
    profile_lookup = {
        row["user_id"]: row["profile"]
        for row in dataset.user_profiles.select("user_id", "profile").iter_rows(named=True)
    }
    topic_by_user = (
        test_with_topics.group_by(["user_id", "topic"])
        .agg(pl.len().alias("events"))
        .sort(["user_id", "events"], descending=[False, True])
        if test_with_topics.height
        else pl.DataFrame(schema={"user_id": pl.Utf8, "topic": pl.Utf8, "events": pl.Int64})
    )
    users: dict[str, dict[str, Any]] = {}
    for row in topic_by_user.iter_rows(named=True):
        user_report = users.setdefault(
            row["user_id"],
            {
                "profile": profile_lookup.get(row["user_id"], "unknown"),
                "future_topics": {},
                "future_thread_ids": [],
            },
        )
        user_report["future_topics"][row["topic"] or "unknown"] = row["events"]

    for row in test_with_topics.select("user_id", "thread_id").unique().sort(["user_id", "thread_id"]).iter_rows(named=True):
        user_report = users.setdefault(
            row["user_id"],
            {
                "profile": profile_lookup.get(row["user_id"], "unknown"),
                "future_topics": {},
                "future_thread_ids": [],
            },
        )
        user_report["future_thread_ids"].append(row["thread_id"])

    return {
        "split_strategy": "time-ordered holdout on aggregated user/thread interactions",
        "half_life_days": half_life_days,
        "interactions": prepared.interactions.height,
        "train_interactions": prepared.train_interactions.height,
        "test_interactions": prepared.test_interactions.height,
        "test_users": prepared.test_interactions.get_column("user_id").n_unique()
        if prepared.test_interactions.height
        else 0,
        "test_threads": prepared.test_interactions.get_column("thread_id").n_unique()
        if prepared.test_interactions.height
        else 0,
        "leaked_user_thread_pairs": leaked_pairs,
        "evaluates_future_events_only": len(leaked_pairs) == 0,
        "why_relevant": (
            "Held-out rows are the latest user/thread interactions after the global time split; "
            "they represent future user behavior that was excluded from train_interactions."
        ),
        "users": users,
    }


def build_synthetic_big_test_report(
    dataset: SyntheticForumDataset,
    seed: int,
    scale: SyntheticScale = SyntheticScale(),
    edge_case_seeds: dict[str, int] | None = None,
    half_life_days: float = 21.0,
    now: datetime | None = None,
    include_evaluation: bool = False,
) -> dict[str, Any]:
    validation_errors = validate_synthetic_forum_dataset(dataset, scale=scale)
    split_report = build_synthetic_split_report(dataset, half_life_days=half_life_days, now=now)
    report = {
        "seed": seed,
        "edge_case_seeds": edge_case_seeds or EDGE_CASE_SEEDS,
        "scale": dataset.report,
        "profiles": dataset.report.get("profiles", {}),
        "topics": dataset.report.get("topics", {}),
        "event_types": dataset.report.get("event_types", {}),
        "validation_errors": validation_errors,
        "split": split_report,
    }
    if include_evaluation:
        from recommender.evaluation import build_big_test_evaluation_report

        report["evaluation"] = build_big_test_evaluation_report(dataset, half_life_days=half_life_days, now=now)
    return report


def write_synthetic_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_ready(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _pair_set(frame: pl.DataFrame) -> set[tuple[str, str]]:
    if frame.is_empty():
        return set()
    return {
        (row["user_id"], row["thread_id"])
        for row in frame.select("user_id", "thread_id").unique().iter_rows(named=True)
    }


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(inner) for key, inner in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(inner) for inner in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Papaya synthetic recommendation fixture report")
    parser.add_argument("--seed", type=int, default=BIG_TEST_SEED)
    parser.add_argument("--half-life-days", type=float, default=21.0)
    parser.add_argument("--output", type=Path, default=Path("apps/recommender/artifacts/synthetic-big-test-report.json"))
    parser.add_argument("--include-evaluation", action="store_true")
    parser.add_argument("--mode", choices=["smoke", "big"], default="big")
    parser.add_argument("--fixture-path", type=Path, default=DEFAULT_FIXTURE_PATH)
    parser.add_argument("--print", action="store_true", dest="print_report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    now = datetime(2026, 5, 19, 12, tzinfo=timezone.utc)
    scale = SyntheticScale.smoke() if args.mode == "smoke" else SyntheticScale()
    dataset = generate_synthetic_forum_dataset(scale=scale, seed=args.seed, now=now, fixture_path=args.fixture_path)
    report = build_synthetic_big_test_report(
        dataset,
        seed=args.seed,
        scale=scale,
        half_life_days=args.half_life_days,
        now=now,
        include_evaluation=args.include_evaluation,
    )
    write_synthetic_report(args.output, report)
    if args.print_report:
        print(json.dumps(_json_ready(report), indent=2, sort_keys=True))
    return 0


def _generate_users(count: int, start: datetime, rng: random.Random) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    profile_names = list(PROFILE_WEIGHTS)
    profile_counts = _scaled_counts(count, [12, 12, 12, 10, 4])
    users: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    idx = 0
    for profile, profile_count in zip(profile_names, profile_counts, strict=True):
        for _ in range(profile_count):
            user_id = f"user-{idx:03d}"
            users.append(
                {
                    "user_id": user_id,
                    "username": f"{profile.replace('/', '-').replace('-', '_')}_{idx:03d}",
                    "created_at": start + timedelta(days=rng.randint(0, 8), hours=rng.randint(0, 23)),
                }
            )
            profiles.append({"user_id": user_id, "profile": profile})
            idx += 1
    return users, profiles


def _generate_threads(
    count: int,
    users: list[dict[str, Any]],
    user_profiles: list[dict[str, Any]],
    start: datetime,
    rng: random.Random,
    fixture: list[ThreadContentFixture],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, ThreadContentFixture]]:
    topic_counts = _scaled_counts(count, [55, 55, 55, 20, 15])
    topics = ["backend", "frontend", "devops", "mixed", "noise"]
    users_by_profile = _users_by_profile(user_profiles)
    fixture_by_topic = _fixture_by_topic(fixture)
    threads: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    fixtures_by_thread: dict[str, ThreadContentFixture] = {}
    idx = 0
    for topic, topic_count in zip(topics, topic_counts, strict=True):
        for local_idx in range(topic_count):
            thread_id = f"thread-{idx:03d}"
            created_at = start + timedelta(days=rng.randint(5, 55), hours=rng.randint(0, 23))
            author_pool = _author_pool_for_topic(topic, users, users_by_profile)
            author = rng.choice(author_pool)
            fixture_row = _fixture_for_topic(topic, local_idx, fixture_by_topic)
            if fixture_row:
                fixtures_by_thread[thread_id] = fixture_row
            title = html.unescape(fixture_row.title) if fixture_row else f"{rng.choice(THREAD_TITLE_PARTS[topic])} #{local_idx + 1}"
            categories = _categories_from_fixture(topic, fixture_row)
            content = _thread_content(topic, title, categories, fixture_row, rng)
            threads.append(
                {
                    "thread_id": thread_id,
                    "title": title,
                    "categories": categories,
                    "content": content,
                    "author_user_id": author,
                    "created_at": created_at,
                    "updated_at": created_at + timedelta(days=rng.randint(0, 18), hours=rng.randint(0, 23)),
                }
            )
            profiles.append(
                {
                    "thread_id": thread_id,
                    "topic": topic,
                    "source": fixture_row.source if fixture_row else "synthetic-template",
                    "source_url": fixture_row.source_url if fixture_row else "",
                    "license": fixture_row.license if fixture_row else "",
                    "attribution": fixture_row.attribution if fixture_row else "",
                }
            )
            idx += 1
    return threads, profiles, fixtures_by_thread


def _generate_posts(
    scale: SyntheticScale,
    threads: list[dict[str, Any]],
    thread_profiles: list[dict[str, Any]],
    user_profiles: list[dict[str, Any]],
    start: datetime,
    rng: random.Random,
    fixtures_by_thread: dict[str, ThreadContentFixture],
) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    users = [row["user_id"] for row in user_profiles]
    users_by_profile = _users_by_profile(user_profiles)
    topic_by_thread = {row["thread_id"]: row["topic"] for row in thread_profiles}
    idx = 0
    for thread in threads:
        topic = topic_by_thread[thread["thread_id"]]
        author_pool = _participant_pool_for_topic(topic, users, users_by_profile)
        target_posts = rng.randint(scale.posts_per_thread_min, scale.posts_per_thread_max)
        thread_posts = 0
        for source_post in _fixture_posts(fixtures_by_thread.get(thread["thread_id"]))[:target_posts]:
            if idx >= scale.posts_max:
                break
            created_at = _content_time(thread["created_at"], idx + 1)
            posts.append(
                {
                    "post_id": f"post-{idx:05d}",
                    "thread_id": thread["thread_id"],
                    "user_id": _source_user_id(str(source_post.get("owner_source_id", "")), author_pool),
                    "content": source_post.get("content") or _post_content(topic, thread["title"], thread["categories"], rng),
                    "created_at": created_at,
                    "updated_at": created_at + timedelta(hours=1),
                    "source_kind": "stackexchange",
                    "source_post_id": str(source_post.get("source_post_id", "")),
                    "source_role": str(source_post.get("role", "post")),
                    "source_created_at": str(source_post.get("created_at", "")),
                    "source_url": str(source_post.get("source_url", "")),
                    "license": str(source_post.get("license", "")),
                    "attribution": str(source_post.get("attribution", "")),
                }
            )
            idx += 1
            thread_posts += 1
        while thread_posts < target_posts:
            if idx >= scale.posts_max:
                break
            created_at = max(thread["created_at"], start) + timedelta(days=rng.randint(0, 18), hours=rng.randint(0, 23))
            posts.append(_synthetic_post_row(f"post-{idx:05d}", thread, topic, rng.choice(author_pool if rng.random() < 0.88 else users), created_at, rng))
            idx += 1
            thread_posts += 1
    while len(posts) < scale.posts_min:
        thread = rng.choice(threads)
        topic = topic_by_thread[thread["thread_id"]]
        author_pool = _participant_pool_for_topic(topic, users, users_by_profile)
        created_at = max(thread["created_at"], start) + timedelta(days=rng.randint(0, 18), hours=rng.randint(0, 23))
        posts.append(_synthetic_post_row(f"post-{len(posts):05d}", thread, topic, rng.choice(author_pool), created_at, rng))
    return posts


def _generate_comments(
    scale: SyntheticScale,
    posts: list[dict[str, Any]],
    thread_profiles: list[dict[str, Any]],
    user_profiles: list[dict[str, Any]],
    rng: random.Random,
    fixtures_by_thread: dict[str, ThreadContentFixture],
) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    users = [row["user_id"] for row in user_profiles]
    users_by_profile = _users_by_profile(user_profiles)
    topic_by_thread = {row["thread_id"]: row["topic"] for row in thread_profiles}
    real_comments_by_source_post = _fixture_comments_by_source_post(fixtures_by_thread)
    idx = 0
    for post in posts:
        topic = topic_by_thread[post["thread_id"]]
        author_pool = _participant_pool_for_topic(topic, users, users_by_profile)
        target_comments = rng.randint(scale.comments_per_post_min, scale.comments_per_post_max)
        post_comments = 0
        for source_comment in real_comments_by_source_post.get(str(post.get("source_post_id", "")), [])[:target_comments]:
            if idx >= scale.comments_max:
                break
            created_at = _content_time(post["created_at"], idx + 1)
            comments.append(
                {
                    "comment_id": f"comment-{idx:06d}",
                    "post_id": post["post_id"],
                    "thread_id": post["thread_id"],
                    "user_id": _source_user_id(str(source_comment.get("owner_source_id", "")), author_pool),
                    "content": source_comment.get("content") or _comment_content(topic, rng),
                    "created_at": created_at,
                    "updated_at": created_at,
                    "source_kind": "stackexchange",
                    "source_comment_id": str(source_comment.get("source_comment_id", "")),
                    "source_created_at": str(source_comment.get("created_at", "")),
                    "source_url": str(source_comment.get("source_url", "")),
                    "license": str(source_comment.get("license", "")),
                    "attribution": str(source_comment.get("attribution", "")),
                }
            )
            idx += 1
            post_comments += 1
        while post_comments < target_comments:
            if idx >= scale.comments_max:
                break
            created_at = post["created_at"] + timedelta(hours=rng.randint(1, 120))
            comments.append(_synthetic_comment_row(f"comment-{idx:06d}", post, topic, rng.choice(author_pool if rng.random() < 0.82 else users), created_at, rng))
            idx += 1
            post_comments += 1
    while len(comments) < scale.comments_min:
        post = rng.choice(posts)
        topic = topic_by_thread[post["thread_id"]]
        author_pool = _participant_pool_for_topic(topic, users, users_by_profile)
        created_at = post["created_at"] + timedelta(hours=rng.randint(1, 120))
        comments.append(_synthetic_comment_row(f"comment-{len(comments):06d}", post, topic, rng.choice(author_pool), created_at, rng))
    return comments


def _generate_likes(
    posts: list[dict[str, Any]],
    comments: list[dict[str, Any]],
    user_profiles: list[dict[str, Any]],
    rng: random.Random,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    users = [row["user_id"] for row in user_profiles]
    liked_pairs: set[tuple[str, str, str]] = set()
    likes: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    candidates = [("post", row) for row in posts] + [("comment", row) for row in comments]
    for idx in range(1500):
        likable_type, item = rng.choice(candidates)
        user_id = rng.choice(users)
        entity_id = item[f"{likable_type}_id"]
        pair = (user_id, likable_type, entity_id)
        if pair in liked_pairs:
            continue
        liked_pairs.add(pair)
        created_at = item["created_at"] + timedelta(hours=rng.randint(2, 168))
        thread_id = item["thread_id"]
        like_id = f"like-{len(likes):05d}"
        event_type = "post_liked" if likable_type == "post" else "comment_liked"
        likes.append(
            {
                "like_id": like_id,
                "user_id": user_id,
                "likable_id": entity_id,
                "likable_type": likable_type,
                "thread_id": thread_id,
                "created_at": created_at,
            }
        )
        events.append(_event(user_id, event_type, likable_type, entity_id, thread_id, created_at, {"source": "forum"}))
    return likes, events


def _generate_journey_events(
    scale: SyntheticScale,
    users: list[dict[str, Any]],
    user_profiles: list[dict[str, Any]],
    threads: list[dict[str, Any]],
    thread_profiles: list[dict[str, Any]],
    now: datetime,
    rng: random.Random,
) -> list[dict[str, Any]]:
    profile_by_user = {row["user_id"]: row["profile"] for row in user_profiles}
    threads_by_topic = _threads_by_topic(threads, thread_profiles)
    events: list[dict[str, Any]] = []
    for user in users:
        user_id = user["user_id"]
        profile = profile_by_user[user_id]
        visits = rng.randint(42, 70) if profile == "noisy/low-signal" else rng.randint(100, 135)
        for visit_idx in range(visits):
            topic = _weighted_topic(PROFILE_WEIGHTS[profile], rng)
            thread = rng.choice(threads_by_topic[topic])
            created_at = now - timedelta(days=rng.randint(0, 55), hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
            if created_at < thread["created_at"]:
                created_at = thread["created_at"] + timedelta(hours=rng.randint(1, 72))
            events.append(_event(user_id, "thread_viewed", "thread", thread["thread_id"], thread["thread_id"], created_at, {"visit": visit_idx}))
            if rng.random() < 0.45:
                position = rng.randint(1, 20)
                events.append(
                    _event(
                        user_id,
                        "recommendation_impression",
                        "thread",
                        thread["thread_id"],
                        thread["thread_id"],
                        created_at + timedelta(seconds=3),
                        {
                            "model_version": "synthetic-v1",
                            "position": position,
                            "recommendation_source": "model",
                            "placement": "home_recommendations",
                        },
                    )
                )
                if rng.random() < 0.22:
                    events.append(
                        _event(
                            user_id,
                            "recommendation_clicked",
                            "thread",
                            thread["thread_id"],
                            thread["thread_id"],
                            created_at + timedelta(seconds=15),
                            {
                                "model_version": "synthetic-v1",
                                "position": position,
                                "recommendation_source": "model",
                                "placement": "home_recommendations",
                            },
                        )
                    )
    while len(events) < scale.events_min - scale.posts_min - scale.comments_min - 1200:
        user = rng.choice(users)
        thread = rng.choice(threads)
        created_at = now - timedelta(days=rng.randint(0, 45), hours=rng.randint(0, 23))
        events.append(_event(user["user_id"], "thread_viewed", "thread", thread["thread_id"], thread["thread_id"], created_at, {"source": "top-up"}))
    return events


def _content_events(posts: list[dict[str, Any]], comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for post in posts:
        events.append(_event(post["user_id"], "post_created", "post", post["post_id"], post["thread_id"], post["created_at"], {"source": "editor"}))
    for comment in comments:
        events.append(
            _event(
                comment["user_id"],
                "comment_created",
                "comment",
                comment["comment_id"],
                comment["thread_id"],
                comment["created_at"],
                {"source": "comment_box"},
            )
        )
    return events


def _event(user_id: str, event_type: str, entity_type: str, entity_id: str, thread_id: str, created_at: datetime, metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "thread_id": thread_id,
        "metadata": json.dumps(metadata, sort_keys=True),
        "created_at": created_at,
    }


def _user_thread_daily(events: pl.DataFrame) -> pl.DataFrame:
    return (
        events.with_columns(pl.col("created_at").dt.date().alias("event_date"))
        .group_by(["event_date", "user_id", "thread_id", "event_type"])
        .agg(pl.len().cast(pl.Float64).alias("events_count"))
        .sort(["event_date", "user_id", "thread_id", "event_type"])
    )


def _recommendation_daily(events: list[dict[str, Any]]) -> pl.DataFrame:
    rows: dict[tuple[Any, ...], dict[str, Any]] = {}
    for event in events:
        if event["event_type"] not in {"recommendation_impression", "recommendation_clicked"}:
            continue
        metadata = json.loads(event["metadata"])
        key = (event["created_at"].date(), event["user_id"], event["thread_id"], metadata.get("model_version", "synthetic-v1"))
        row = rows.setdefault(
            key,
            {
                "event_date": key[0],
                "user_id": key[1],
                "thread_id": key[2],
                "model_version": key[3],
                "impressions": 0.0,
                "clicks": 0.0,
                "position_sum": 0.0,
            },
        )
        if event["event_type"] == "recommendation_impression":
            row["impressions"] += 1.0
            row["position_sum"] += float(metadata.get("position", 0))
        else:
            row["clicks"] += 1.0
    daily_rows = []
    for row in rows.values():
        impressions = max(row["impressions"], 1.0)
        daily_rows.append(
            {
                "event_date": row["event_date"],
                "user_id": row["user_id"],
                "thread_id": row["thread_id"],
                "model_version": row["model_version"],
                "impressions": row["impressions"],
                "clicks": row["clicks"],
                "ctr": row["clicks"] / impressions,
                "avg_position": row["position_sum"] / impressions,
            }
        )
    return pl.DataFrame(daily_rows)


def _build_report(
    business: BusinessData,
    behavior: BehaviorData,
    user_profiles: list[dict[str, Any]],
    thread_profiles: list[dict[str, Any]],
) -> dict[str, Any]:
    profile_counts = dict(sorted(_count_rows(user_profiles, "profile").items()))
    topic_counts = dict(sorted(_count_rows(thread_profiles, "topic").items()))
    event_counts = behavior.events.group_by("event_type").agg(pl.len().alias("count")).sort("event_type")
    real_threads = sum(1 for row in thread_profiles if row.get("source") != "synthetic-template")
    real_posts = _source_kind_count(business.posts, "stackexchange")
    real_comments = _source_kind_count(business.comments, "stackexchange")
    return {
        "users": business.users.height,
        "threads": business.threads.height,
        "posts": business.posts.height,
        "comments": business.comments.height,
        "likes": business.likes.height,
        "events": behavior.events.height,
        "profiles": profile_counts,
        "topics": topic_counts,
        "event_types": dict(event_counts.iter_rows()),
        "real_content": {
            "source": "Stack Exchange Data Dump",
            "threads": real_threads,
            "posts": real_posts,
            "comments": real_comments,
            "threads_with_full_text": business.threads.filter(pl.col("content").str.strip_chars() != "").height,
            "license": "CC BY-SA 4.0",
        },
    }


def _source_kind_count(frame: pl.DataFrame, source_kind: str) -> int:
    if "source_kind" not in frame.columns:
        return 0
    return frame.filter(pl.col("source_kind") == source_kind).height


def _count_rows(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row[key]] += 1
    return dict(counts)


def _scaled_counts(total: int, weights: list[int]) -> list[int]:
    raw = [total * weight / sum(weights) for weight in weights]
    counts = [int(value) for value in raw]
    for idx in sorted(range(len(raw)), key=lambda i: raw[i] - counts[i], reverse=True)[: total - sum(counts)]:
        counts[idx] += 1
    return counts


def _users_by_profile(user_profiles: list[dict[str, Any]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for row in user_profiles:
        result[row["profile"]].append(row["user_id"])
    return result


def _author_pool_for_topic(topic: str, users: list[dict[str, Any]], users_by_profile: dict[str, list[str]]) -> list[str]:
    if topic == "backend":
        return users_by_profile["backend-heavy"] + users_by_profile["mixed-fullstack"]
    if topic == "frontend":
        return users_by_profile["frontend-heavy"] + users_by_profile["mixed-fullstack"]
    if topic == "devops":
        return users_by_profile["devops-heavy"] + users_by_profile["mixed-fullstack"]
    return [row["user_id"] for row in users]


def _participant_pool_for_topic(topic: str, users: list[str], users_by_profile: dict[str, list[str]]) -> list[str]:
    if topic == "backend":
        return users_by_profile["backend-heavy"] + users_by_profile["mixed-fullstack"]
    if topic == "frontend":
        return users_by_profile["frontend-heavy"] + users_by_profile["mixed-fullstack"]
    if topic == "devops":
        return users_by_profile["devops-heavy"] + users_by_profile["mixed-fullstack"]
    if topic == "mixed":
        return users_by_profile["mixed-fullstack"] + users_by_profile["backend-heavy"] + users_by_profile["frontend-heavy"]
    return users


def _threads_by_topic(threads: list[dict[str, Any]], thread_profiles: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_id = {row["thread_id"]: row for row in threads}
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in thread_profiles:
        result[row["topic"]].append(by_id[row["thread_id"]])
    return result


def _fixture_by_topic(fixture: list[ThreadContentFixture]) -> dict[str, list[ThreadContentFixture]]:
    result: dict[str, list[ThreadContentFixture]] = defaultdict(list)
    for row in fixture:
        result[row.topic].append(row)
    return result


def _fixture_for_topic(
    topic: str,
    index: int,
    fixture_by_topic: dict[str, list[ThreadContentFixture]],
) -> ThreadContentFixture | None:
    rows = fixture_by_topic.get(topic) or fixture_by_topic.get("mixed") or []
    if not rows:
        return None
    return rows[index % len(rows)]


def _categories_from_fixture(topic: str, fixture_row: ThreadContentFixture | None) -> list[str]:
    if fixture_row is None:
        return THREAD_CATEGORIES[topic]
    tags = [tag.lower().replace(".", "").replace("js", "js") for tag in fixture_row.tags[:5]]
    categories = list(dict.fromkeys([*THREAD_CATEGORIES.get(topic, []), *tags]))
    return categories[:8]


def _thread_content(
    topic: str,
    title: str,
    categories: list[str],
    fixture_row: ThreadContentFixture | None,
    rng: random.Random,
) -> str:
    if fixture_row and fixture_row.content:
        parts = [fixture_row.content]
        answer_texts = [
            str(post.get("content", ""))
            for post in (fixture_row.posts or [])
            if post.get("role") != "question" and post.get("content")
        ][:3]
        comment_texts = [str(comment.get("content", "")) for comment in (fixture_row.comments or []) if comment.get("content")][:5]
        if answer_texts:
            parts.append("Answers: " + " ".join(answer_texts))
        if comment_texts:
            parts.append("Comments: " + " ".join(comment_texts))
        return "\n".join(parts)

    snippets = {
        "backend": ["database latency", "transaction boundaries", "query plan", "Go service", "API handler"],
        "frontend": ["component state", "client cache", "rendering behavior", "form validation", "Next.js route"],
        "devops": ["container logs", "deployment pipeline", "Linux service", "Docker network", "healthcheck"],
        "mixed": ["API contract", "auth flow", "integration boundary", "event stream", "architecture decision"],
        "noise": ["tool setup", "workflow note", "team discussion", "editor preference", "career question"],
    }
    source_bits = fixture_row.content if fixture_row else " ".join(categories)
    body = " ".join(rng.sample(snippets.get(topic, snippets["mixed"]), k=3))
    return f"{title}. Tags: {' '.join(categories)}. Context: {source_bits}. Discussion focuses on {body}."


def _fixture_posts(fixture_row: ThreadContentFixture | None) -> list[dict[str, Any]]:
    if fixture_row is None:
        return []
    posts = [post for post in (fixture_row.posts or []) if str(post.get("content", "")).strip()]
    if posts:
        return posts
    return [
        {
            "source_post_id": fixture_row.question_id,
            "role": "question",
            "owner_source_id": fixture_row.owner_source_id,
            "content": fixture_row.content,
            "created_at": fixture_row.created_at,
            "updated_at": fixture_row.updated_at,
            "source_url": fixture_row.source_url,
            "license": fixture_row.license,
            "attribution": fixture_row.attribution,
        }
    ] if fixture_row.content else []


def _fixture_comments_by_source_post(fixtures_by_thread: dict[str, ThreadContentFixture]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fixture_row in fixtures_by_thread.values():
        for comment in fixture_row.comments or []:
            source_post_id = str(comment.get("source_post_id", ""))
            if source_post_id:
                result[source_post_id].append(comment)
    return result


def _source_user_id(source_id: str, fallback_users: list[str]) -> str:
    if source_id and fallback_users:
        return fallback_users[sum(ord(char) for char in source_id) % len(fallback_users)]
    return fallback_users[0]


def _content_time(base: datetime, offset: int) -> datetime:
    return base + timedelta(hours=max(offset, 1))


def _synthetic_post_row(
    post_id: str,
    thread: dict[str, Any],
    topic: str,
    user_id: str,
    created_at: datetime,
    rng: random.Random,
) -> dict[str, Any]:
    return {
        "post_id": post_id,
        "thread_id": thread["thread_id"],
        "user_id": user_id,
        "content": _post_content(topic, thread["title"], thread["categories"], rng),
        "created_at": created_at,
        "updated_at": created_at + timedelta(hours=rng.randint(0, 72)),
        "source_kind": "synthetic-template",
        "source_post_id": "",
        "source_role": "generated",
        "source_created_at": "",
        "source_url": "",
        "license": "",
        "attribution": "",
    }


def _post_content(topic: str, title: str, categories: list[str], rng: random.Random) -> str:
    details = {
        "backend": ["indexes", "connection pooling", "migration order", "request timeout", "repository layer"],
        "frontend": ["hook dependencies", "server components", "query invalidation", "controlled inputs", "hydration"],
        "devops": ["compose service", "volume mount", "healthcheck", "shell logs", "network alias"],
        "mixed": ["contract version", "session state", "data ownership", "error shape", "release path"],
        "noise": ["local setup", "editor config", "team habit", "notes", "tool choice"],
    }
    return f"{title}: {rng.choice(details.get(topic, details['mixed']))} with {' '.join(categories[:3])}."


def _synthetic_comment_row(
    comment_id: str,
    post: dict[str, Any],
    topic: str,
    user_id: str,
    created_at: datetime,
    rng: random.Random,
) -> dict[str, Any]:
    return {
        "comment_id": comment_id,
        "post_id": post["post_id"],
        "thread_id": post["thread_id"],
        "user_id": user_id,
        "content": _comment_content(topic, rng),
        "created_at": created_at,
        "updated_at": created_at + timedelta(hours=rng.randint(0, 48)),
        "source_kind": "synthetic-template",
        "source_comment_id": "",
        "source_created_at": "",
        "source_url": "",
        "license": "",
        "attribution": "",
    }


def _comment_content(topic: str, rng: random.Random) -> str:
    phrases = {
        "backend": ["check the query plan", "pin the transaction scope", "measure with a smaller batch"],
        "frontend": ["verify the render path", "invalidate the client cache", "split the component state"],
        "devops": ["inspect container logs", "check service DNS", "limit the worker threads"],
        "mixed": ["write the contract first", "keep the boundary explicit", "trace the full request"],
        "noise": ["document the tradeoff", "keep the setup simple", "compare the workflow"],
    }
    return rng.choice(phrases.get(topic, phrases["mixed"]))


def _weighted_topic(weights: dict[str, float], rng: random.Random) -> str:
    topics = list(weights.keys())
    return rng.choices(topics, weights=[weights[topic] for topic in topics], k=1)[0]


def _posts_are_after_threads(posts: pl.DataFrame, threads: pl.DataFrame) -> bool:
    joined = posts.join(threads.select("thread_id", pl.col("created_at").alias("thread_created_at")), on="thread_id", how="left")
    return joined.filter(pl.col("created_at") < pl.col("thread_created_at")).is_empty()


def _posts_have_existing_threads(posts: pl.DataFrame, threads: pl.DataFrame) -> bool:
    return set(posts.get_column("thread_id").to_list()) <= set(threads.get_column("thread_id").to_list())


def _comments_are_after_posts(comments: pl.DataFrame, posts: pl.DataFrame) -> bool:
    joined = comments.join(posts.select("post_id", pl.col("created_at").alias("post_created_at")), on="post_id", how="left")
    return joined.filter(pl.col("created_at") < pl.col("post_created_at")).is_empty()


def _comments_have_existing_posts(comments: pl.DataFrame, posts: pl.DataFrame) -> bool:
    return set(comments.get_column("post_id").to_list()) <= set(posts.get_column("post_id").to_list())


if __name__ == "__main__":
    raise SystemExit(main())
