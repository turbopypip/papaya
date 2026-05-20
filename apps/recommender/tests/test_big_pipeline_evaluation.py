from datetime import datetime, timezone

import polars as pl

from recommender.content import build_or_load_content_index
from recommender.evaluation import baseline_recommendation_sets, big_test_user_examples, evaluate_recommendation_sets, popularity_by_thread
from recommender.etl import prepare_data
from recommender.matrix import build_interaction_matrix
from recommender.champion import evaluate_and_select_champion
from recommender.recommendations import generate_for_users
from recommender.serving import thread_categories
from recommender.synthetic import SyntheticScale, generate_synthetic_forum_dataset


def test_big_synthetic_pipeline_generates_personalized_recommendations_and_metrics(tmp_path):
    now = datetime(2026, 5, 19, 12, tzinfo=timezone.utc)
    dataset = generate_synthetic_forum_dataset(scale=SyntheticScale.smoke(), seed=9400, now=now)
    prepared = prepare_data(dataset.business, dataset.behavior, half_life_days=21.0, now=now)
    matrix = build_interaction_matrix(prepared.train_interactions)
    selection = evaluate_and_select_champion(
        matrix,
        dataset.business.users,
        dataset.business.threads,
        prepared.train_interactions,
        prepared.test_interactions,
        prepared.interactions,
        top_n=10,
        candidate_pool_size=50,
        random_state=42,
        k=10,
        candidate_model_types=("entity_feature", "learning_to_rank", "factorization_machine", "two_tower"),
    )
    model = selection.model_result
    content_index = build_or_load_content_index(dataset.business.threads, artifacts_dir=tmp_path)
    user_ids = dataset.business.users.get_column("user_id").to_list()

    generated = generate_for_users(
        user_ids,
        dataset.business.threads,
        prepared.train_interactions,
        matrix,
        model,
        top_n=10,
        candidate_pool_size=50,
        min_model_interactions=20,
        content_index=content_index,
    )
    model_recommendations = {
        user_id: [thread_id for thread_id, _score, _source in items]
        for user_id, items in generated.items()
    }
    baselines = baseline_recommendation_sets(user_ids, dataset.business.threads, prepared.train_interactions, top_n=10)
    metrics = evaluate_recommendation_sets(
        {selection.model_type: model_recommendations, **baselines},
        prepared.test_interactions,
        set(dataset.business.threads.get_column("thread_id").to_list()),
        thread_categories(dataset.business.threads),
        popularity_by_thread(prepared.interactions),
        k=10,
    )

    assert all(len(items) == 10 for items in generated.values())
    assert metrics[selection.model_type]["personalization"] > 0.1
    assert set(metrics) == {selection.model_type, "popular_recent", "category_popular", "latest_active"}
    assert all(source == "model" for items in generated.values() for _thread_id, _score, source in items)
    assert all(0.0 <= report["precision_at_k"] <= 1.0 for report in metrics.values())
    assert all(0.0 <= report["recall_at_k"] <= 1.0 for report in metrics.values())

    examples = big_test_user_examples(generated, dataset.user_profiles, dataset.thread_profiles, limit_users=3)
    assert len(examples) == 3
    assert all(example["recommendations"] for example in examples)
    topics_by_profile = (
        pl.DataFrame(
            {
                "profile": [example["profile"] for example in examples],
                "first_topic": [example["recommendations"][0]["topic"] for example in examples],
            }
        )
        .group_by("profile")
        .agg(pl.col("first_topic").n_unique().alias("topics"))
    )
    assert topics_by_profile.height > 0
