from recommender.metrics import hit_rate_at_k, map_at_k, ndcg_at_k, personalization_score, precision_at_k, ranking_report, recall_at_k


def test_ranking_metrics_reward_hits_near_top():
    recommendations = ["thread-a", "thread-b", "thread-c"]
    relevant = {"thread-b", "thread-x"}

    assert precision_at_k(recommendations, relevant, 2) == 0.5
    assert recall_at_k(recommendations, relevant, 2) == 0.5
    assert hit_rate_at_k(recommendations, relevant, 2) == 1.0
    assert 0.0 < ndcg_at_k(recommendations, relevant, 3) < 1.0
    assert map_at_k(recommendations, relevant, 3) == 0.25


def test_ranking_report_includes_coverage_novelty_diversity_and_personalization():
    recommendations = {
        "backend-user": ["go-new", "pg-new", "react-new"],
        "frontend-user": ["react-new", "next-new", "go-new"],
    }
    relevant = {
        "backend-user": {"go-new", "pg-new"},
        "frontend-user": {"react-new"},
    }
    categories = {
        "go-new": {"go", "backend"},
        "pg-new": {"postgresql", "backend"},
        "react-new": {"react", "frontend"},
        "next-new": {"nextjs", "frontend"},
    }
    popularity = {"go-new": 10.0, "pg-new": 2.0, "react-new": 5.0, "next-new": 1.0}

    report = ranking_report(recommendations, relevant, set(categories), categories, popularity, k=3)

    assert report["precision_at_k"] > 0.0
    assert report["recall_at_k"] > 0.0
    assert report["coverage"] == 1.0
    assert report["diversity"] > 0.0
    assert report["novelty"] > 0.0
    assert report["personalization"] == personalization_score(recommendations, k=3)
