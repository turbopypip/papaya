from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from recommender.synthetic import BIG_TEST_SEED, build_synthetic_big_test_report, generate_synthetic_forum_dataset
from recommender.synthetic_loader import DEMO_USERS_BY_PROFILE


METRIC_COLUMNS = [
    "precision_at_k",
    "recall_at_k",
    "hit_rate_at_k",
    "ndcg_at_k",
    "map_at_k",
    "coverage",
    "diversity",
    "novelty",
    "personalization",
]

MODEL_STAT_COLUMNS = [
    "catboost_ranker_score",
    "evaluation_users",
    "evaluation_candidate_threads",
    "evaluation_positive_threads",
    "evaluation_avg_candidates_per_user",
    "evaluation_avg_positives_per_user",
    "pairwise_auc",
    "score_positive_mean",
    "score_negative_mean",
    "score_margin_mean",
]

FULL_CATALOG_COLUMNS = [
    "full_catalog_precision_at_k",
    "full_catalog_recall_at_k",
    "full_catalog_hit_rate_at_k",
    "full_catalog_ndcg_at_k",
    "full_catalog_map_at_k",
    "full_catalog_coverage",
    "full_catalog_diversity",
    "full_catalog_novelty",
    "full_catalog_personalization",
]


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_markdown_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(report), encoding="utf-8")


def render_markdown_report(report: dict[str, Any]) -> str:
    evaluation = report.get("evaluation", {})
    scale = report.get("scale", {})
    split = report.get("split", {})
    model_type = str(evaluation.get("model_type") or "catboost_ranker")
    metrics = evaluation.get("metrics", {})
    content_guardrails = evaluation.get("content_guardrails", {})
    users = evaluation.get("users", [])
    event_types = report.get("event_types", {})
    profiles = report.get("profiles", {})
    topics = report.get("topics", {})
    real_content = scale.get("real_content", {})

    lines = [
        "# Papaya Recommendation Quality Report",
        "",
        "## Summary",
        "",
        f"- Seed: `{report.get('seed', 'unknown')}`.",
        f"- Users: {_fmt_int(scale.get('users'))}; threads: {_fmt_int(scale.get('threads'))}; posts: {_fmt_int(scale.get('posts'))}; comments: {_fmt_int(scale.get('comments'))}; events: {_fmt_int(scale.get('events'))}.",
        f"- Production model: `{model_type}`.",
        f"- Model trained: `{evaluation.get('model_trained', 'unknown')}`.",
        f"- Feature schema: `{evaluation.get('feature_schema_version', 'not recorded')}`.",
        "- Model-selection pipeline: `disabled`; normal training, generation, and serving use only the production CatBoostRanker artifact.",
        f"- Normal recommendation sources: `{', '.join(evaluation.get('normal_sources', [])) or 'not recorded'}`.",
        f"- Content backend: `{content_guardrails.get('embedding_backend', 'not recorded')}`; search: `{content_guardrails.get('search_backend', 'not recorded')}`.",
        "",
        "## Dataset Scale",
        "",
        "| object | count |",
        "| --- | ---: |",
        f"| users | {_fmt_int(scale.get('users'))} |",
        f"| threads | {_fmt_int(scale.get('threads'))} |",
        f"| posts | {_fmt_int(scale.get('posts'))} |",
        f"| comments | {_fmt_int(scale.get('comments'))} |",
        f"| likes | {_fmt_int(scale.get('likes'))} |",
        f"| behavioral events | {_fmt_int(scale.get('events'))} |",
        "",
        "## Real Content Coverage",
        "",
        _real_content_table(real_content),
        "",
        "## Sampled Ranking Metrics",
        "",
        _metrics_table(model_type, metrics),
        "",
        "## Model Statistics",
        "",
        _stats_table(metrics),
        "",
        "## Full Catalog Check",
        "",
        _full_catalog_table(metrics),
        "",
        "## Content-Aware Layer",
        "",
        _content_guardrails(content_guardrails),
        "",
        "## Attribution",
        "",
        "The local content fixture uses Stack Overflow questions, answers, tags, source URLs, and attribution metadata from the Stack Exchange Data Dump. Stack Overflow content is licensed under CC BY-SA; imported rows keep `source_url`, `license`, and `attribution` metadata.",
        "",
        "## Event Distribution",
        "",
        _distribution_table(event_types, "event_type"),
        "",
        _mermaid_pie("Events by Type", event_types),
        "",
        "## User Profiles",
        "",
        _distribution_table(profiles, "profile"),
        "",
        _mermaid_pie("Users by Profile", profiles),
        "",
        "## Thread Topics",
        "",
        _distribution_table(topics, "topic"),
        "",
        _mermaid_pie("Threads by Topic", topics),
        "",
        "## Train/Test Split",
        "",
        f"- Strategy: {split.get('split_strategy', 'unknown')}.",
        f"- Interactions: {_fmt_int(split.get('interactions'))}.",
        f"- Train interactions: {_fmt_int(split.get('train_interactions'))}.",
        f"- Test interactions: {_fmt_int(split.get('test_interactions'))}.",
        f"- Test users: {_fmt_int(split.get('test_users'))}; test threads: {_fmt_int(split.get('test_threads'))}.",
        f"- Future-only evaluation: `{split.get('evaluates_future_events_only', False)}`.",
        "",
        _mermaid_bar("Train/Test Interactions", {"train": split.get("train_interactions", 0), "test": split.get("test_interactions", 0)}),
        "",
        "## Demo Recommendations",
        "",
        "These rows show why the recommendations are personal: each demo profile receives a different top-N list.",
        "",
        _demo_user_sections(users),
        "",
        "## Hyperparameters",
        "",
        _hyperparameters(evaluation.get("hyperparameters", {})),
        "",
        "## Exclusions",
        "",
        "The model excludes threads that should not be recommended, including already viewed or authored threads.",
        "",
        _exclusion_examples(users),
    ]
    return "\n".join(lines).rstrip() + "\n"


def _metrics_table(model_type: str, metrics: dict[str, Any]) -> str:
    if not metrics:
        return "No metrics recorded."
    lines = [
        "| model | " + " | ".join(METRIC_COLUMNS) + " |",
        "| --- |" + " ---: |" * len(METRIC_COLUMNS),
    ]
    values = [_fmt_float(metrics.get(column)) for column in METRIC_COLUMNS]
    lines.append(f"| {model_type} | " + " | ".join(values) + " |")
    return "\n".join(lines)


def _stats_table(metrics: dict[str, Any]) -> str:
    values = [(name, metrics.get(name)) for name in MODEL_STAT_COLUMNS if name in metrics]
    if not values:
        return "No model statistics recorded."
    lines = ["| statistic | value |", "| --- | ---: |"]
    for name, value in values:
        lines.append(f"| {name} | {_fmt_float(value)} |")
    return "\n".join(lines)


def _full_catalog_table(metrics: dict[str, Any]) -> str:
    values = [(name.removeprefix("full_catalog_"), metrics.get(name)) for name in FULL_CATALOG_COLUMNS if name in metrics]
    if not values:
        return "No full-catalog metrics recorded."
    lines = ["| metric | value |", "| --- | ---: |"]
    for name, value in values:
        lines.append(f"| {name} | {_fmt_float(value)} |")
    return "\n".join(lines)


def _real_content_table(real_content: dict[str, Any]) -> str:
    if not real_content:
        return "No real-content coverage recorded."
    rows = [
        ("source", real_content.get("source")),
        ("threads", real_content.get("threads")),
        ("posts", real_content.get("posts")),
        ("comments", real_content.get("comments")),
        ("threads_with_full_text", real_content.get("threads_with_full_text")),
        ("license", real_content.get("license")),
    ]
    lines = ["| field | value |", "| --- | ---: |"]
    for name, value in rows:
        lines.append(f"| {name} | {value} |")
    return "\n".join(lines)


def _content_guardrails(guardrails: dict[str, Any]) -> str:
    if not guardrails:
        return "No content-aware guardrails recorded."
    rows = [
        ("passed", guardrails.get("passed")),
        ("embedding_backend", guardrails.get("embedding_backend")),
        ("search_backend", guardrails.get("search_backend")),
        ("embedding_dimension", guardrails.get("embedding_dimension")),
        ("index_memory_mb", guardrails.get("index_memory_mb")),
        ("content_index_build_seconds", guardrails.get("content_index_build_seconds")),
        ("generation_seconds", guardrails.get("generation_seconds")),
        ("failures", ", ".join(guardrails.get("failures", [])) if isinstance(guardrails.get("failures"), list) else guardrails.get("failures")),
    ]
    lines = ["| guardrail | value |", "| --- | ---: |"]
    for name, value in rows:
        lines.append(f"| {name} | {value} |")
    return "\n".join(lines)


def _distribution_table(values: dict[str, Any], label: str) -> str:
    if not values:
        return f"No {label} distribution recorded."
    lines = [f"| {label} | count |", "| --- | ---: |"]
    for name, count in sorted(values.items()):
        lines.append(f"| {name} | {_fmt_int(count)} |")
    return "\n".join(lines)


def _mermaid_pie(title: str, values: dict[str, Any]) -> str:
    if not values:
        return ""
    lines = ["```mermaid", "pie showData", f'    title {title}']
    for name, count in sorted(values.items()):
        lines.append(f'    "{name}" : {int(float(count or 0))}')
    lines.append("```")
    return "\n".join(lines)


def _mermaid_bar(title: str, values: dict[str, Any]) -> str:
    labels = list(values)
    counts = [int(float(values[label] or 0)) for label in labels]
    return "\n".join(
        [
            "```mermaid",
            "xychart-beta",
            f'    title "{title}"',
            "    x-axis [" + ", ".join(labels) + "]",
            '    y-axis "interactions" 0 --> ' + str(max(counts + [1])),
            "    bar [" + ", ".join(str(count) for count in counts) + "]",
            "```",
        ]
    )


def _demo_user_sections(users: list[dict[str, Any]]) -> str:
    if not users:
        return "No recommendation examples recorded."
    selected = _select_demo_users(users)
    sections: list[str] = []
    for user in selected:
        alias = DEMO_USERS_BY_PROFILE.get(user.get("profile", ""), user.get("username", user.get("user_id", "unknown")))
        sections.extend(
            [
                f"### {alias}",
                "",
                f"- Synthetic source user: `{user.get('username', user.get('user_id', 'unknown'))}`.",
                f"- Interest profile: `{user.get('profile', 'unknown')}`.",
                "",
                "| rank | thread | topic | score | source |",
                "| ---: | --- | --- | ---: | --- |",
            ]
        )
        for item in user.get("recommendations", [])[:10]:
            sections.append(
                "| {rank} | `{thread}` | {topic} | {score} | {source} |".format(
                    rank=item.get("rank", ""),
                    thread=item.get("thread_id", ""),
                    topic=item.get("topic", "unknown"),
                    score=_fmt_float(item.get("score")),
                    source=item.get("source", "unknown"),
                )
            )
        sections.append("")
    return "\n".join(sections).rstrip()


def _select_demo_users(users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_profiles: set[str] = set()
    for user in users:
        profile = user.get("profile")
        if profile in DEMO_USERS_BY_PROFILE and profile not in seen_profiles:
            selected.append(user)
            seen_profiles.add(profile)
    return selected


def _hyperparameters(params: dict[str, Any]) -> str:
    if not params:
        return "No hyperparameters recorded."
    return "`" + json.dumps(params, sort_keys=True) + "`"


def _exclusion_examples(users: list[dict[str, Any]]) -> str:
    selected = _select_demo_users(users)
    if not selected:
        return "No exclusion examples recorded."
    lines = ["| demo user | excluded thread | reason |", "| --- | --- | --- |"]
    for user in selected:
        alias = DEMO_USERS_BY_PROFILE.get(user.get("profile", ""), user.get("username", user.get("user_id", "unknown")))
        for item in user.get("excluded_threads", [])[:5]:
            lines.append(f"| {alias} | `{item.get('thread_id', '')}` | {item.get('reason', 'unknown')} |")
    return "\n".join(lines)


def _fmt_float(value: Any) -> str:
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return "-"


def _fmt_int(value: Any) -> str:
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return "-"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a human-readable Papaya recommendation quality report")
    parser.add_argument("--input", type=Path, default=None, help="Existing JSON report to render")
    parser.add_argument("--output", type=Path, default=Path("../../recommendation-model-report.md"))
    parser.add_argument("--seed", type=int, default=BIG_TEST_SEED)
    parser.add_argument("--half-life-days", type=float, default=21.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.input:
        report = load_report(args.input)
    else:
        dataset = generate_synthetic_forum_dataset(seed=args.seed)
        report = build_synthetic_big_test_report(
            dataset,
            seed=args.seed,
            half_life_days=args.half_life_days,
            include_evaluation=True,
        )
    write_markdown_report(args.output, report)
    print(f"Wrote recommendation report to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
