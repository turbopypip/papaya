# API

Текущая точка входа backend: `apps/backend`.

Базовый URL API: `/api/v1`.

## Вложения

Вложения используют единый контракт владельца:

```json
{
  "ID": "uuid",
  "url": "/uploads/<storage-key>",
  "file_name": "report.pdf",
  "content_type": "application/pdf",
  "size": 12345,
  "owner_type": "thread",
  "owner_id": "uuid",
  "CreatedAt": "2026-05-11T12:00:00Z"
}
```

`owner_type` может быть одним из значений: `thread`, `post`, `comment`.

Ограничения минимальной версии:

- максимальный размер файла: 10 MB;
- максимальное количество файлов на одну сущность: 5;
- разрешенные типы: JPEG, PNG, GIF, WebP, PDF, TXT, IPYNB, DOC/DOCX, XLS/XLSX, PPT/PPTX, ZIP.

Файлы сохраняются на backend в директорию `UPLOADS_PATH` с физическими именами на основе UUID. Публичные файлы отдаются через `/uploads/:path*`; правило rewrite на frontend проксирует этот путь на backend внутри Docker.

## Создание треда

`POST /thread`

Если файлов нет, поддерживается прежний JSON-контракт:

```json
{
  "title": "Название треда",
  "categories": ["go", "frontend"]
}
```

Для загрузки файлов нужно отправлять `multipart/form-data`:

- `title`: строка;
- `categories`: повторяемое строковое поле;
- `attachments`: повторяемое файловое поле.

Ответ:

```json
{
  "message": "created thread",
  "thread": {
    "ID": "uuid",
    "title": "Название треда",
    "categories": ["go"],
    "attachments": []
  }
}
```

## Создание поста

`POST /post`

JSON без файлов:

```json
{
  "content": "Текст поста",
  "thread_id": "uuid"
}
```

Multipart с файлами:

- `content`: строка;
- `thread_id`: UUID;
- `attachments`: повторяемое файловое поле.

Ответ содержит созданный пост вместе с массивом `post.attachments`.

## Создание комментария

`POST /comment`

JSON без файлов:

```json
{
  "content": "Текст комментария",
  "post_id": "uuid"
}
```

Multipart с файлами:

- `content`: строка;
- `post_id`: UUID;
- `attachments`: повторяемое файловое поле.

Ответ содержит созданный комментарий вместе с массивом `comment.attachments`.

## Чтение Метаданных

Metadata вложений возвращается в:

- `GET /thread/:id` как `thread.attachments`;
- `GET /thread/all?page=1&limit=100` как `threads[].attachments`;
- `GET /post?thread_id=<uuid>&page=1&limit=100` как `posts[].attachments`;
- `GET /comment?post_id=<uuid>&page=1&limit=100` как `comments[].attachments`.

Списковые endpoints загружают вложения пачкой по `owner_type + owner_id`, чтобы избежать N+1 запросов.

## Ручная Проверка

1. Создать тред с одним файлом и проверить, что ответ содержит `thread.attachments[0].url`.
2. Открыть страницу треда и проверить, что квадрат вложения ведет на `/uploads/<storage-key>`.
3. Создать пост с одним файлом и проверить, что вложение отображается под постом.
4. Создать комментарий с одним файлом и проверить, что вложение отображается под комментарием.
5. В Docker проверить, что `./apps/backend/uploads` смонтирован в `/uploads`, а `/uploads/<storage-key>` отдается через frontend rewrite.

## События для рекомендаций

Backend собирает поведенческие события в ClickHouse для обучения, offline-метрик и online-serving рекомендательной модели. Форумные операции не зависят от успешной записи аналитики: если ClickHouse временно недоступен, ошибка логируется, а пользовательский сценарий продолжается.

Таблица событий: `papaya_analytics.user_events`.

Поля события:

- `user_id` - пользователь, совершивший действие;
- `event_type` - тип события;
- `entity_type` - тип сущности;
- `entity_id` - идентификатор сущности;
- `thread_id` - тред, к которому относится действие;
- `metadata` - JSON-строка с дополнительными данными;
- `created_at` - время события.

Типы событий:

- `thread_viewed`;
- `thread_created`;
- `post_created`;
- `comment_created`;
- `post_liked`;
- `comment_liked`.

События обратной связи по рекомендациям:

- `recommendation_impression`;
- `recommendation_clicked`.

Просмотр треда записывается отдельным endpoint:

```http
POST /api/v1/analytics/thread/:id/view
```

Эндпоинт требует авторизацию и права чтения тредов. Остальные события backend пишет автоматически после успешного создания треда, поста, комментария или лайка.

Срок хранения сырых событий задается ClickHouse TTL в миграциях:

- `recommendation_impression` - 60 дней;
- `recommendation_clicked` - 365 дней;
- `thread_viewed` - 180 дней;
- `thread_created`, `post_created`, `comment_created`, `post_liked`, `comment_liked` - 730 дней;
- неизвестные типы событий - 365 дней.

Дневные агрегаты автоматически строятся через materialized views:

- `papaya_analytics.user_thread_event_daily` - `user_id x thread_id x event_type`;
- `papaya_analytics.recommendation_event_daily` - impressions, clicks и позиции по `model_version`;
- `papaya_analytics.recommendation_event_daily_stats` - view с CTR и средней позицией.

Агрегаты хранятся 2 года и являются основным источником для обучения модели. Сырые события используются для отладки и коротких аналитических окон.

## Хранилища И Выдача Рекомендаций

Актуальная online-выдача не хранится в Redis. Backend вызывает FastAPI recommender service, сервис загружает CatBoostRanker artifact и генерирует выдачу моделью на request path по актуальным PostgreSQL/ClickHouse признакам. Публичное поле `score` уже нормализовано для сортировки по убыванию: внутри artifact зафиксировано `score_direction=negated_catboost_prediction`.

ClickHouse хранит историю и статусы запусков:

- `papaya_analytics.recommendation_history` - snapshot выданных рекомендаций с `user_id`, `thread_id`, `score`, `model_version`, `run_id`, `generated_at`, `rank`, `source`;
- `papaya_analytics.recommendation_runs` - статус обучения/генерации, счетчики, метрики и ошибки.

PostgreSQL не используется как serving-хранилище рекомендаций и остается источником бизнес-данных форума.

## Получение рекомендаций

```http
GET /api/v1/recommendations/threads?limit=10
```

Эндпоинт требует авторизацию. Backend отправляет id авторизованного пользователя и `limit` в FastAPI recommender service, получает ранжированные thread ids и metadata, затем подгружает треды и авторов из PostgreSQL и отбрасывает отсутствующие или удаленные треды.

Текущий frontend показывает рекомендации только на главной странице. Страница треда пишет `thread_viewed`, но не рендерит блок похожих тредов. Поэтому штатный `placement` для UI-событий рекомендаций - `home_recommendations`.

Ответ с готовой выдачей:

```json
{
  "status": "ready",
  "model_version": "catboost-ranker-v1",
  "generated_at": "2026-05-19T12:00:00Z",
  "run_id": "uuid",
  "generation_id": "uuid",
  "recommendations": [
    {
      "thread": {"ID": "uuid", "title": "Go profiling #1"},
      "score": 113.6,
      "recommendation_source": "model",
      "model_version": "catboost-ranker-v1",
      "generated_at": "2026-05-19T12:00:00Z",
      "run_id": "uuid",
      "generation_id": "uuid"
    }
  ]
}
```

Если CatBoostRanker artifact еще не обучен или сервис недоступен, endpoint возвращает `200` с пустым списком и статусом `model_not_ready`; если model path не нашел кандидатов, возвращается `no_recommendations`. Неавторизованный запрос получает `401`.

`recommendation_source=model` появляется после накопления достаточной истории пользователя. Порог задается `RECOMMENDER_MIN_MODEL_INTERACTIONS`, по умолчанию `20`. В порог входят `thread_viewed`, `post_liked`, `comment_liked`, `recommendation_clicked`, `post_created` и `comment_created`. `recommendation_impression` пишется для аналитики, но не считается сильным сигналом для перехода из fallback в model.

Из выдачи исключаются собственные и уже потребленные треды пользователя: просмотренные, лайкнутые или открытые кликом из рекомендаций. Если пользователь уже пролайкал все треды выбранной категории, recommender будет ранжировать оставшиеся кандидаты, пока в каталоге не появятся новые непотребленные треды этой категории.

События аналитики рекомендаций пишутся через:

```http
POST /api/v1/analytics/recommendations/event
```

Тело запроса разделяет причину выдачи и место показа:

```json
{
  "event_type": "recommendation_impression",
  "thread_id": "uuid",
  "model_version": "catboost-ranker-v1",
  "position": 1,
  "recommendation_source": "model",
  "placement": "home_recommendations",
  "run_id": "uuid",
  "generation_id": "uuid"
}
```

## Большой тест рекомендаций

Синтетический fixture запускается командой:

```bash
cd apps/recommender
uv run python -m recommender.synthetic \
  --seed 9400 \
  --include-evaluation \
  --output ../../docs/recommendation-big-test-report.json
```

JSON содержит seed, параметры датасета, объемы PostgreSQL/ClickHouse-like данных, train/test split без утечки будущих событий в train, sampled-ranking метрики единственной production-модели `CatBoostRanker` (`precision@k`, `recall@k`, `hit rate@k`, `NDCG@k`, `MAP@k`, coverage, diversity, novelty, personalization), full-catalog sanity metrics, score-distribution статистику, `pairwise_auc`, feature schema, hyperparameters, `score_direction` и top-N рекомендации по тестовым пользователям. Единый человекочитаемый отчет для защиты хранится в корне проекта: `recommendation-model-report.md`.
