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

Ограничения MVP:

- максимальный размер файла: 10 MB;
- максимальное количество файлов на одну сущность: 5;
- разрешенные типы: JPEG, PNG, GIF, WebP, PDF, TXT, IPYNB, DOC/DOCX, XLS/XLSX, PPT/PPTX, ZIP.

Файлы сохраняются на backend в директорию `UPLOADS_PATH` с физическими именами на основе UUID. Публичные файлы отдаются через `/uploads/:path*`; frontend rewrite проксирует этот путь на backend внутри Docker.

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

## Чтение metadata

Metadata вложений возвращается в:

- `GET /thread/:id` как `thread.attachments`;
- `GET /thread/all?page=1&limit=100` как `threads[].attachments`;
- `GET /post?thread_id=<uuid>&page=1&limit=100` как `posts[].attachments`;
- `GET /comment?post_id=<uuid>&page=1&limit=100` как `comments[].attachments`.

Списковые endpoints загружают вложения батчем по `owner_type + owner_id`, чтобы избежать N+1 запросов.

## Ручной smoke-тест

1. Создать тред с одним файлом и проверить, что ответ содержит `thread.attachments[0].url`.
2. Открыть страницу треда и проверить, что квадрат вложения ведет на `/uploads/<storage-key>`.
3. Создать пост с одним файлом и проверить, что вложение отображается под постом.
4. Создать комментарий с одним файлом и проверить, что вложение отображается под комментарием.
5. В Docker проверить, что `./apps/backend/uploads` смонтирован в `/uploads`, а `/uploads/<storage-key>` отдается через frontend rewrite.

## События для рекомендаций

Backend собирает поведенческие события в ClickHouse для будущего обучения рекомендательной модели. Форумные операции не зависят от успешной записи аналитики: если ClickHouse временно недоступен, ошибка логируется, а пользовательский сценарий продолжается.

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

Просмотр треда записывается отдельным endpoint:

```http
POST /api/v1/analytics/thread/:id/view
```

Endpoint требует авторизацию и права чтения тредов. Остальные события пишутся backend автоматически после успешного создания треда, поста, комментария или лайка.
