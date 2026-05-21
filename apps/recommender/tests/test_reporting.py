from recommender.reporting import render_markdown_report


def test_render_markdown_report_includes_metrics_charts_and_demo_users():
    report = {
        "seed": 9400,
        "scale": {
            "users": 50,
            "threads": 200,
            "posts": 1100,
            "comments": 4950,
            "likes": 1496,
            "events": 16312,
            "real_content": {
                "source": "Stack Exchange Data Dump",
                "threads": 200,
                "posts": 400,
                "comments": 120,
                "threads_with_full_text": 200,
                "license": "CC BY-SA 4.0",
            },
        },
        "profiles": {"backend-heavy": 12, "frontend-heavy": 12, "devops-heavy": 12, "mixed-fullstack": 10},
        "topics": {"backend": 55, "frontend": 55, "devops": 55, "mixed": 20, "noise": 15},
        "event_types": {"thread_viewed": 5663, "recommendation_clicked": 566},
        "split": {
            "split_strategy": "time-ordered holdout",
            "interactions": 1000,
            "train_interactions": 800,
            "test_interactions": 200,
            "test_users": 50,
            "test_threads": 120,
            "evaluates_future_events_only": True,
        },
        "evaluation": {
            "model_type": "catboost_ranker",
            "model_trained": True,
            "feature_schema_version": "catboost_ranker_features_v1",
            "model_selection_enabled": False,
            "normal_sources": ["model"],
            "hyperparameters": {"loss_function": "YetiRank", "iterations": 160},
            "metrics": {
                "precision_at_k": 0.2,
                "recall_at_k": 0.1,
                "hit_rate_at_k": 0.9,
                "ndcg_at_k": 0.3,
                "map_at_k": 0.1,
                "coverage": 0.4,
                "diversity": 0.5,
                "novelty": 7.0,
                "personalization": 0.8,
                "catboost_ranker_score": 0.19,
                "evaluation_users": 50.0,
                "evaluation_candidate_threads": 3000.0,
                "evaluation_positive_threads": 200.0,
                "evaluation_avg_candidates_per_user": 60.0,
                "evaluation_avg_positives_per_user": 4.0,
                "pairwise_auc": 0.71,
                "score_positive_mean": 1.4,
                "score_negative_mean": 0.3,
                "score_margin_mean": 1.1,
                "full_catalog_precision_at_k": 0.02,
                "full_catalog_recall_at_k": 0.01,
                "full_catalog_hit_rate_at_k": 0.1,
                "full_catalog_ndcg_at_k": 0.03,
                "full_catalog_map_at_k": 0.02,
                "full_catalog_coverage": 0.12,
                "full_catalog_diversity": 0.5,
                "full_catalog_novelty": 8.0,
                "full_catalog_personalization": 0.7,
            },
            "users": [
                {
                    "username": "backend_heavy_000",
                    "user_id": "user-000",
                    "profile": "backend-heavy",
                    "recommendations": [
                        {"rank": 1, "thread_id": "thread-001", "topic": "backend", "score": 10.0, "source": "model"}
                    ],
                    "excluded_threads": [{"thread_id": "thread-002", "reason": "already viewed or authored in train"}],
                },
                {
                    "username": "frontend_heavy_012",
                    "user_id": "user-012",
                    "profile": "frontend-heavy",
                    "recommendations": [
                        {"rank": 1, "thread_id": "thread-101", "topic": "frontend", "score": 9.0, "source": "model"}
                    ],
                    "excluded_threads": [],
                },
            ],
        },
    }

    markdown = render_markdown_report(report)

    assert "# Papaya Recommendation Quality Report" in markdown
    assert "| catboost_ranker | 0.2000 | 0.1000" in markdown
    assert "Production model: `catboost_ranker`." in markdown
    assert "Model-selection pipeline: `disabled`" in markdown
    assert "## Model Statistics" in markdown
    assert "| pairwise_auc | 0.7100 |" in markdown
    assert "## Full Catalog Check" in markdown
    assert "| precision_at_k | 0.0200 |" in markdown
    assert "## Model Candidates" not in markdown
    assert "Champion model" not in markdown
    assert "pie showData" in markdown
    assert "xychart-beta" in markdown
    assert "## Real Content Coverage" in markdown
    assert "| comments | 120 |" in markdown
    assert "### backend-user" in markdown
    assert "### frontend-user" in markdown
    assert "already viewed or authored in train" in markdown
