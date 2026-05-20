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
            "model_type": "entity_feature_sgd",
            "final_pipeline_uses_winner": True,
            "normal_sources": ["model"],
            "champion": {
                "champion_model_type": "entity_feature_sgd",
                "champion_status": "champion",
                "champion_reason": "best NDCG@K with passing guardrails",
                "ml_candidates": [
                    {
                        "model_type": "entity_feature_sgd",
                        "trained": True,
                        "hyperparameters": {"factors": 32},
                        "metrics": {"ndcg_at_k": 0.3, "recall_at_k": 0.2, "map_at_k": 0.1},
                        "champion_score": 0.25,
                        "training_seconds": 1.2,
                        "generation_seconds": 0.2,
                    }
                ],
            },
            "baseline_comparison": {
                "entity_feature_sgd": {
                    "precision_at_k": 0.2,
                    "recall_at_k": 0.1,
                    "hit_rate_at_k": 0.9,
                    "ndcg_at_k": 0.3,
                    "map_at_k": 0.1,
                    "coverage": 0.4,
                    "diversity": 0.5,
                    "novelty": 7.0,
                    "personalization": 0.8,
                }
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
    assert "| entity_feature_sgd | 0.2000 | 0.1000" in markdown
    assert "Final train/generate pipeline uses winner only: `True`." in markdown
    assert "pie showData" in markdown
    assert "xychart-beta" in markdown
    assert "## Real Content Coverage" in markdown
    assert "| comments | 120 |" in markdown
    assert "### backend-user" in markdown
    assert "### frontend-user" in markdown
    assert "already viewed or authored in train" in markdown
