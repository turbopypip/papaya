from datetime import datetime, timezone

import polars as pl

from recommender.data import BehaviorData, BusinessData, empty_frame, EMPTY_EVENTS
from recommender.etl import build_interactions


def test_build_interactions_combines_business_and_behavior_events():
    now = datetime(2026, 5, 19, tzinfo=timezone.utc)
    business = BusinessData(
        users=pl.DataFrame({"user_id": ["user-1"], "username": ["alice"], "created_at": [now]}),
        threads=pl.DataFrame(
            {
                "thread_id": ["thread-1"],
                "title": ["Go tips"],
                "categories": [["go"]],
                "content": ["Go backend discussion"],
                "author_user_id": ["user-2"],
                "created_at": [now],
                "updated_at": [now],
            }
        ),
        posts=pl.DataFrame(
            {
                "post_id": ["post-1"],
                "thread_id": ["thread-1"],
                "user_id": ["user-1"],
                "content": ["post"],
                "created_at": [now],
                "updated_at": [now],
            }
        ),
        comments=pl.DataFrame(
            {
                "comment_id": ["comment-1"],
                "post_id": ["post-1"],
                "thread_id": ["thread-1"],
                "user_id": ["user-1"],
                "content": ["comment"],
                "created_at": [now],
                "updated_at": [now],
            }
        ),
        likes=pl.DataFrame(
            {
                "like_id": ["like-1"],
                "user_id": ["user-1"],
                "likable_id": ["post-1"],
                "likable_type": ["post"],
                "thread_id": ["thread-1"],
                "created_at": [now],
            }
        ),
    )
    behavior = BehaviorData(
        events=empty_frame(EMPTY_EVENTS),
        user_thread_daily=pl.DataFrame(
            {
                "event_date": [now.date(), now.date()],
                "user_id": ["user-1", "user-1"],
                "thread_id": ["thread-1", "thread-1"],
                "event_type": ["thread_viewed", "post_created"],
                "events_count": [2.0, 1.0],
            }
        ),
        recommendation_daily=pl.DataFrame(),
    )

    interactions = build_interactions(business, behavior, half_life_days=21.0, now=now)

    assert interactions.height == 2
    user_score = interactions.filter((pl.col("user_id") == "user-1") & (pl.col("thread_id") == "thread-1")).item(0, "score")
    assert 11.0 < user_score < 12.0
