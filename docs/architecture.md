# Архитектура

Papaya организован как monorepo.

- `apps/backend` содержит Go API.
- `apps/frontend` содержит Next.js приложение.
- `apps/recommender` содержит Python-пайплайн обучения, генерации, отчетов и online-serving.
- Корневой `docker-compose.yml` поднимает полный локальный стек.

## Поток Данных Рекомендаций

Рекомендательная система разделяет операционные данные форума, поведенческую аналитику и online-выдачу.

PostgreSQL хранит только бизнес-данные форума: пользователей, роли, треды, посты, комментарии, лайки и вложения. Это источник истины для деталей тредов, авторов, прав доступа и данных, которые нужны для отображения форума. PostgreSQL не хранит историю рекомендаций, запуски модели и состояние serving-а.

ClickHouse хранит append-only поведенческие события, дневные агрегаты, историю выданных рекомендаций, `recommendation_runs` и метрики модели. Backend пишет события аналитики через отдельный сервис; если запись в ClickHouse не удалась, ошибка логируется, но пользовательская операция форума не падает. Сырые события ClickHouse имеют TTL: impressions хранятся 60 дней, клики по рекомендациям - 365 дней, просмотры тредов - 180 дней, сильные форумные события - 730 дней, неизвестные типы событий - 365 дней. Дневные агрегаты `user_id x thread_id x event_type` и метрики рекомендаций хранятся 2 года. Агрегаты являются основным источником для обучения модели, а сырые события используются для отладки и коротких аналитических окон. Для production-нагрузки сервис аналитики можно расширить durable buffer или очередью между handlers форума и ClickHouse.

Redis используется backend-ом для кэша форума, но не является serving-хранилищем рекомендаций. Online-выдача строится через FastAPI recommender service, а долговременная история и метрики модели находятся в ClickHouse.

Python recommender читает форумные сущности из PostgreSQL и поведенческие признаки из ClickHouse. Обучение записывает production-artifact CatBoostRanker. FastAPI service загружает этот artifact и по запросу генерирует ранжированный список `thread_id`. Предсказания CatBoost `YetiRank` публикуются как `score=-catboost_prediction`, поэтому большее публичное значение `score` всегда означает более высокий ранг. Request-time serving использует модель после того, как у пользователя накопилось минимум `RECOMMENDER_MIN_MODEL_INTERACTIONS` сильных сигналов, по умолчанию `20`; до этого возвращается явно помеченный fallback. Offline generation пишет историю рекомендаций, `recommendation_runs` и метрики запусков в ClickHouse.

Backend endpoint рекомендаций вызывает FastAPI recommender service, получает ранжированные `thread_id`, `score`, `recommendation_source`, `model_version`, `run_id`/`generation_id`, затем догружает детали тредов и авторов из PostgreSQL и возвращает ответ frontend-у. Текущий frontend показывает рекомендации только на главной странице (`placement=home_recommendations`); страницы тредов записывают `thread_viewed`, но не рендерят дополнительный блок рекомендаций.

## Модуль Recommender

`apps/recommender` - Python-модуль с пайплайном обучения, генерации и online-serving:

- `train_model.py` загружает пользователей, треды, посты, комментарии, лайки, события ClickHouse и дневные агрегаты; строит user/thread/pair признаки для CatBoostRanker; обучает одну модель `catboost_ranker` с ranking groups; сохраняет модель и feature schema.
- `generate_recommendations.py` загружает CatBoostRanker artifact, строит top-N рекомендации по текущему PostgreSQL-каталогу, исключает собственные и уже потребленные треды, применяет явно помеченные fallback baselines только для cold-start/sparse-history пользователей или пустого model output, затем сохраняет историю рекомендаций в ClickHouse.
- `api.py` предоставляет FastAPI request-time serving. Он загружает CatBoostRanker artifact, заново собирает актуальный поведенческий контекст из PostgreSQL и ClickHouse, скорит текущих кандидатов и возвращает `thread_id`, `score`, `recommendation_source`, `model_version`, `run_id`/`generation_id` и metadata для аналитики.

Сильные пользовательские сигналы для активации модели: просмотры тредов, лайки постов/комментариев, клики по рекомендациям, созданные посты и созданные комментарии. Recommendation impressions сохраняются для аналитики и CTR-метрик, но не считаются сигналами активации model-выдачи. Фильтр потребленных кандидатов исключает треды, которые пользователь создал, просмотрел, лайкнул или открыл из рекомендации.

Production model type зафиксирован как `catboost_ranker`. Matrix-only SVD, SGD, two-tower и код сравнения моделей являются историческими/offline-only частями и не используются в обычных train/generate/serve jobs. Baselines оставлены только для явного fallback: `popular_recent`, `category_popular`, `latest_active`. Offline-отчеты включают sampled-ranking Precision@K, Recall@K, NDCG@K, MAP@K, HitRate@K, full-catalog sanity metrics, coverage, diversity, novelty, personalization, score-distribution статистику, `pairwise_auc`, `catboost_ranker_score` и content-aware guardrails.

Content-aware retrieval layer строит embeddings из `title + categories + content`. Если установлены optional packages, используются `sentence-transformers` и FAISS; в CPU-only Docker demo включается fallback на sklearn hashing и numpy search. Embeddings кэшируются по `content_hash` и переиспользуются с диска, поэтому тяжелая работа с embeddings/index остается в offline recommender jobs и не попадает в backend request path.
