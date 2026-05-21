from datetime import datetime, timezone

from recommender.content import (
    build_or_load_content_index,
    content_recommendations_for_user,
    import_stackexchange_posts_xml,
    load_stackexchange_fixture,
)
from recommender.etl import prepare_data
from recommender.synthetic import SyntheticScale, generate_synthetic_forum_dataset


def test_stackexchange_fixture_has_real_content_rows():
    rows = load_stackexchange_fixture()

    assert len(rows) >= 1000
    assert {row.topic for row in rows} >= {"backend", "frontend", "devops"}
    assert all(row.license.startswith("CC BY-SA") for row in rows[:25])


def test_stackexchange_import_keeps_question_answers_comments_and_attribution(tmp_path):
    posts_xml = tmp_path / "Posts.xml"
    comments_xml = tmp_path / "Comments.xml"
    output = tmp_path / "fixture.jsonl"
    posts_xml.write_text(
        """<posts>
  <row Id="101" PostTypeId="1" CreationDate="2024-01-01T00:00:00" LastActivityDate="2024-01-02T00:00:00" Score="7" OwnerUserId="10" Title="How do I tune PostgreSQL indexes from Go?" Tags="&lt;postgresql&gt;&lt;go&gt;" Body="&lt;p&gt;Real question body with query plan details.&lt;/p&gt;" />
  <row Id="102" PostTypeId="2" ParentId="101" CreationDate="2024-01-01T01:00:00" LastActivityDate="2024-01-01T01:00:00" Score="3" OwnerUserId="11" Body="&lt;p&gt;Real answer body: use EXPLAIN ANALYZE and partial indexes.&lt;/p&gt;" />
</posts>""",
        encoding="utf-8",
    )
    comments_xml.write_text(
        """<comments>
  <row Id="201" PostId="102" CreationDate="2024-01-01T02:00:00" Score="1" UserId="12" Text="Real comment: check table statistics too." />
</comments>""",
        encoding="utf-8",
    )

    written = import_stackexchange_posts_xml(posts_xml, output, limit=10, comments_xml=comments_xml)
    rows = load_stackexchange_fixture(output)

    assert written == 1
    assert rows[0].content == "Real question body with query plan details."
    assert rows[0].source_url == "https://stackoverflow.com/questions/101"
    assert rows[0].license == "CC BY-SA 4.0"
    assert rows[0].attribution == "Stack Overflow question 101"
    assert [post["role"] for post in rows[0].posts] == ["question", "answer"]
    assert rows[0].posts[1]["content"] == "Real answer body: use EXPLAIN ANALYZE and partial indexes."
    assert rows[0].comments[0]["content"] == "Real comment: check table statistics too."


def test_content_index_supports_user_recommendations(tmp_path):
    now = datetime(2026, 5, 19, 12, tzinfo=timezone.utc)
    dataset = generate_synthetic_forum_dataset(scale=SyntheticScale.smoke(), seed=42, now=now)
    prepared = prepare_data(dataset.business, dataset.behavior, half_life_days=21.0, now=now)
    index = build_or_load_content_index(dataset.business.threads, artifacts_dir=tmp_path)

    user_id = dataset.business.users.item(0, "user_id")
    recommendations = content_recommendations_for_user(user_id, prepared.train_interactions, index, limit=10)

    assert index.metadata["threads"] == dataset.business.threads.height
    assert index.backend in {"sentence_transformers", "sklearn_hashing"}
    assert index.search_backend in {"faiss", "numpy"}
    assert len(recommendations) == 10
