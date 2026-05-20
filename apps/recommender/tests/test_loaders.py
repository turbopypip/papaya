from recommender.loaders import load_behavior_data


class EmptyQueryResult:
    result_rows = []
    column_names = []


class RecordingClickHouse:
    def __init__(self):
        self.queries = []

    def query(self, sql):
        self.queries.append(sql)
        return EmptyQueryResult()


def test_behavior_loader_limits_raw_and_daily_sources_by_events_days():
    client = RecordingClickHouse()

    behavior = load_behavior_data(client, days=7)

    assert behavior.events.is_empty()
    assert behavior.user_thread_daily.is_empty()
    assert behavior.recommendation_daily.is_empty()
    assert len(client.queries) == 3
    assert all("INTERVAL 7 DAY" in query for query in client.queries)
