# Papaya

Papaya - fullstack-проект форума с backend на Go и frontend на Next.js.

## Структура

```text
papaya/
├── apps/
│   ├── backend/
│   ├── frontend/
│   └── recommender/
├── infra/
│   └── docker/
├── docs/
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
└── README.md
```

## Приложения

- `apps/backend` - Go API.
- `apps/frontend` - Next.js приложение.
- `apps/recommender` - Python pipeline обучения и генерации рекомендаций.

## Локальный запуск

Создайте локальный файл окружения:

```bash
cp .env.example .env
```

Запустите весь проект:

```bash
docker compose up --build
```

Запуск с dev-настройками:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

## Переменные окружения

Шаблон переменных лежит в `.env.example`. Реальный `.env` не коммитится.

Основные группы переменных:

- `POSTGRES_*` - подключение к PostgreSQL.
- `REDIS_*` - подключение к Redis.
- `CLICKHOUSE_*` - подключение к ClickHouse для поведенческих событий рекомендаций.
- `LOCAL_CONFIG_PATH` - путь к YAML-конфигу backend внутри контейнера.
- `SECRET` - секрет для JWT.
- `UPLOADS_PATH` - путь для файловых вложений.
- `DEV_USER_ROLE` - роль dev-пользователя в dev-режиме: `admin` по умолчанию или `user`.
- `AUTH_COOKIE_*` - настройки JWT cookie: domain, secure и sameSite.
- `SERVER_API_URL` - внутренний URL backend для Next.js proxy внутри Docker-сети.
- `NEXT_PUBLIC_API_URL` - публичный URL backend для frontend; по умолчанию пустой, чтобы браузер ходил через Next.js proxy `/api/v1`.

## ClickHouse и миграции аналитики

Рекомендательная система собирает append-only события в ClickHouse. Docker Compose поднимает сервис `clickhouse` и одноразовый job `clickhouse-migrate`, который применяет миграции из `apps/backend/app/migrations/clickhouse`.

База аналитики фиксирована в миграциях как `papaya_analytics`; через окружение настраиваются адрес ClickHouse, пользователь и пароль.

Сырые события в `papaya_analytics.user_events` не хранятся бессрочно. Retention задается ClickHouse TTL в миграциях:

- `recommendation_impression` - 60 дней;
- `recommendation_clicked` - 365 дней;
- `thread_viewed` - 180 дней;
- `thread_created`, `post_created`, `comment_created`, `post_liked`, `comment_liked` - 730 дней;
- неизвестные типы событий - 365 дней.

Для обучения и аналитики ClickHouse также хранит дневные агрегаты дольше сырых событий:

- `papaya_analytics.user_thread_event_daily` - матрица `user_id x thread_id x event_type`;
- `papaya_analytics.recommendation_event_daily` - дневные impressions, clicks и суммы позиций по `model_version`;
- `papaya_analytics.recommendation_event_daily_stats` - view с CTR и средней позицией;
- срок хранения агрегатов - 2 года.

Основной источник для обучения модели - агрегированные таблицы; `user_events` используется для отладки и коротких окон.

Запустить миграции вручную можно так:

```bash
docker compose run --rm clickhouse-migrate
```

Проверочные SQL-запросы лежат в `apps/backend/app/migrations/clickhouse/check_events.sql`.

## Рекомендательная модель

Python recommender читает бизнес-данные из PostgreSQL, поведенческие события и агрегаты из ClickHouse, выбирает winner model из четырех кандидатов 9.2 и сохраняет артефакты в `apps/recommender/artifacts`. FastAPI recommender service загружает winner artifact и генерирует выдачу по запросу пользователя; backend запрашивает у него `thread_id`, `score`, `recommendation_source`, `model_version`, `run_id`/`generation_id`, а детали тредов и авторов по-прежнему берет из PostgreSQL. ClickHouse остается хранилищем событий, истории выдачи, статусов запусков и метрик.

Локальный запуск:

```bash
cd apps/recommender
uv sync
uv run python -m recommender.train_model --env-file ../../.env
uv run python -m recommender.generate_recommendations --env-file ../../.env
uv run python -m recommender.api --env-file ../../.env --host 0.0.0.0 --port 8000
```

Docker one-off jobs:

```bash
docker compose run --rm recommender-train
docker compose run --rm recommender-generate
```

`recommender-generate` больше не является serving-хранилищем: он сохраняет snapshots в ClickHouse `recommendation_history` и статусы в `recommendation_runs`. Online-выдача строится FastAPI service на request path через winner model. Fallback источники помечаются как `fallback_*`; UI-точка показа передается отдельно как `placement`.

## Синтетический большой тест рекомендаций

Для задачи `9.4. Большие тесты` добавлен генератор синтетического пользовательского опыта: `apps/recommender/recommender/synthetic.py`.

Цель генератора - проверить рекомендательную модель не на случайном наборе строк, а на правдоподобной имитации жизни форума. Генератор создает пользователей, треды, посты, комментарии, лайки, просмотры, показы рекомендаций и клики по рекомендациям. Данные возвращаются в тех же структурах, которые уже использует recommender pipeline: `BusinessData` для PostgreSQL-данных и `BehaviorData` для ClickHouse-событий и агрегатов.

Текущий реализованный масштаб smoke synthetic-теста:

- 50 тестовых пользователей;
- 200 тестовых тредов;
- 1000-1200 постов;
- 4000-6000 комментариев;
- 12000-18000 поведенческих событий;
- минимум 30-40 взаимодействий на пользователя.

Текущий реализованный масштаб content-aware большого теста:

- 1000 реальных технических тредов из Stack Exchange/Stack Overflow fixture с question bodies, answer bodies, comments when available и CC BY-SA attribution;
- около 1000 synthetic-тредов, разложенных по тематикам backend, frontend, devops, mixed и noise;
- для каждого треда 5-50 Papaya-постов: реальные Stack Overflow question/answer posts плюс synthetic top-up для масштаба;
- для каждого поста 1-5 Papaya-комментариев: реальные Stack Overflow comments where available плюс synthetic top-up для шума;
- целевые объемы событий пересчитаны под новый масштаб так, чтобы у пользователей оставалось достаточно train/test взаимодействий;
- `title + categories + content` содержит тематический сигнал для `sentence-transformers`/FAISS content layer и CPU fallback.

Fixture лежит в `apps/recommender/fixtures/stackexchange_titles.jsonl` и хранит `source_url`, `license`, `attribution`, даты источника, тексты вопросов/ответов и комментарии. Его можно пересобрать из Stack Exchange Data Dump:

```bash
cd apps/recommender
uv run recommender-import-stackexchange /path/to/Posts.xml \
  --comments-xml /path/to/Comments.xml \
  --limit 1000
```

Генератор делит пользователей на скрытые профили интересов: `backend-heavy`, `frontend-heavy`, `devops-heavy`, `mixed-fullstack`, `noisy/low-signal`. Эти профили не передаются модели и не являются обучающими признаками. Они нужны только генератору, чтобы создать правдоподобное поведение: backend-пользователь чаще читает Go/PostgreSQL/backend-треды, frontend-пользователь чаще читает React/Next.js/frontend-треды, mixed-пользователь ходит по нескольким темам, а noisy-пользователь дает слабый и грязный сигнал.

Модель видит только итоговые события вида `user_id -> thread_id -> event_type -> created_at`. Задача модели - по этим действиям восстановить интерес пользователя и рекомендовать треды, которые он еще не видел. Поэтому профили в генераторе выступают как скрытая "правда мира", а не как подсказка модели.

Логика генерации:

1. Создаются пользователи с датой регистрации и скрытым профилем интересов.
2. Создаются тематические треды: backend, frontend, devops, mixed и noise.
3. Создаются посты и комментарии с корректной временной последовательностью: тред раньше поста, пост раньше комментария.
4. Авторы постов и комментариев чаще выбираются из пользователей, которым близка тема треда, но часть действий остается шумовой.
5. Для каждого пользователя генерируются повторные сессии: просмотр нескольких тематически близких тредов, иногда переход в соседнюю или нерелевантную тему, показ рекомендации и иногда клик по ней.
6. События создания постов, комментариев и лайков добавляются в общий поток ClickHouse-like событий.
7. Из raw events строятся дневные агрегаты `user_thread_daily` и `recommendation_daily`.
8. `validate_synthetic_forum_dataset` проверяет объемы, наличие всех типов событий, временную консистентность, feedback loop рекомендаций и минимальный объем сигналов по каждому пользователю.

Проверить генератор можно так:

```bash
cd apps/recommender
uv run pytest tests/test_synthetic.py
```

Полный набор recommender-тестов:

```bash
cd apps/recommender
uv run pytest
```

Сгенерировать машинный JSON большого теста:

```bash
cd apps/recommender
uv run python -m recommender.synthetic \
  --seed 9400 \
  --include-evaluation \
  --output ../../docs/recommendation-big-test-report.json
```

Собрать человекочитаемый Markdown-отчет с таблицами метрик, Mermaid-графиками и top-N выдачей demo-пользователей:

```bash
cd apps/recommender
uv run python -m recommender.reporting \
  --output ../../recommendation-model-report.md
```

Загрузить тот же fixture в тестовые PostgreSQL и ClickHouse из `.env`:

```bash
cd apps/recommender
uv run python -m recommender.synthetic_loader \
  --env-file ../../.env \
  --dataset-id synthetic-big-test \
  --run-id synthetic-loader-run \
  --validate
```

Поднять полное demo-приложение с большим синтетическим датасетом, обучением модели и готовыми рекомендациями:

```bash
docker compose -f docker-compose.yml -f docker-compose.recommender-demo.yml up --build
```

Demo-сценарий поднимает PostgreSQL, ClickHouse, Redis для backend-кэша, FastAPI recommender service, backend, frontend, миграции, seed job, обучение, генерацию ClickHouse history и обновляет единый Markdown-отчет в корне проекта: `recommendation-model-report.md`. Seed job создает большой датасет 9.4 и демо-пользователей:

В demo и в запуске на заранее сгенерированном Stack Exchange fixture используется `RECOMMENDER_MODEL_TYPE=winner`: первый запуск выбирает winner-а, последующие запуски переобучают и генерируют выдачу только этим типом модели.

- `backend-user@papaya.demo`;
- `frontend-user@papaya.demo`;
- `devops-user@papaya.demo`;
- `mixed-user@papaya.demo`.

Пароль для всех demo-пользователей: `PapayaDemo1!`. После старта frontend доступен на `http://localhost:3000`; можно войти под любым demo-пользователем и увидеть персональный блок рекомендаций.

Dev-пользователь backend-а создается в dev-режиме:

- `dev@papaya.local`;
- пароль: `papaya-dev-password`;
- роль по умолчанию: `admin`, можно заменить через `DEV_USER_ROLE=user`.

### Финальное состояние рекомендаций

Текущий конечный вариант логики рекомендаций:

1. Backend и frontend работают как основной продуктовый путь: пользователь заходит на `http://localhost:3000`, frontend ходит в backend, backend запрашивает персональные рекомендации у FastAPI recommender service.
2. Recommender обучается на бизнес-данных из PostgreSQL и поведенческих событиях из ClickHouse: просмотры тредов, созданные посты и комментарии, лайки, показы рекомендаций и клики.
3. В demo-сценарии seed job загружает 1000 технических тредов на базе Stack Exchange/Stack Overflow fixture, 27314 постов, 81460 комментариев, 1500 лайков и 159074 событий.
4. Train job сравнивает кандидатов, выбирает champion model и сохраняет `model.joblib`, `metadata.json` и content index в `apps/recommender/artifacts`.
5. Generate job пишет snapshots в ClickHouse `recommendation_history` и статусы запусков в `recommendation_runs`.
6. Online-выдача строится request-time через FastAPI recommender service, поэтому backend получает `thread_id`, `score`, `recommendation_source`, `model_version`, `run_id` и `generation_id`, а детали тредов догружает из PostgreSQL.
7. Нормальная выдача помечается `recommendation_source=model`; fallback используется только для новых или sparse-history пользователей и помечается как `fallback_*`.
8. Для большого demo-набора backend и recommender используют 30-секундные timeouts, потому что первый request path может читать артефакты и агрегаты дольше короткого HTTP timeout.

Текущий проверенный serving-срез:

| поле | значение |
| --- | --- |
| model_version | `demo-synthetic-v1` |
| serving model | `factorization_machine_svd` |
| recommendation source | `model` |
| recommendation runs в ClickHouse | `4` |
| recommendation history rows | `1020` |
| frontend | `http://localhost:3000` |
| backend | `http://localhost:8888` |
| recommender service | `http://localhost:8000` |

Проверенные demo-аккаунты:

| профиль | email | пароль | ожидаемый смысл выдачи |
| --- | --- | --- | --- |
| backend | `backend-user@papaya.demo` | `PapayaDemo1!` | PostgreSQL, backend, API |
| frontend | `frontend-user@papaya.demo` | `PapayaDemo1!` | React, Next.js, frontend |
| devops | `devops-user@papaya.demo` | `PapayaDemo1!` | Docker, shell, deployment |
| mixed | `mixed-user@papaya.demo` | `PapayaDemo1!` | смешанная fullstack-выдача |
| dev admin | `dev@papaya.local` | `papaya-dev-password` | административный dev-пользователь |

Текущие метрики serving-модели:

| метрика | значение | что означает |
| --- | ---: | --- |
| `NDCG@10` | 0.9065 | Насколько хорошо отсортирован top-10: релевантные треды стоят выше. Чем ближе к 1, тем лучше порядок выдачи. |
| `Precision@10` | 0.8941 | Какая доля top-10 рекомендаций оказалась релевантной пользователю. 0.8941 значит примерно 9 из 10 рекомендаций попадают в интерес. |
| `Recall@10` | 0.0601 | Какую долю всех будущих релевантных тредов пользователя удалось поймать в top-10. Низкое значение нормально, когда релевантных тредов много, а показываем только 10. |
| `MAP@10` | 0.8738 | Средняя точность с учетом позиций релевантных тредов в top-10. Высокое значение значит, что хорошие рекомендации появляются рано. |
| `Hit rate@10` | 0.9804 | Доля пользователей, у которых в top-10 есть хотя бы одна релевантная рекомендация. |
| `Coverage` | 0.2690 | Доля каталога тредов, которую модель вообще использует в рекомендациях. Это защита от выдачи одних и тех же популярных тредов всем. |
| `Personalization` | 0.9475 | Насколько выдачи разных пользователей отличаются друг от друга. Чем выше, тем меньше одинаковых списков для всех. |
| `CTR` | 21.7% | Доля кликов по recommendation impressions в сгенерированном behavioral feedback loop. |

После ручных просмотров, лайков, комментариев и кликов по рекомендациям можно быстро пересчитать выдачу:

```bash
docker compose -f docker-compose.yml -f docker-compose.recommender-demo.yml --profile demo-tools run --rm recommender-demo-refresh
```

Отчет можно повторно собрать вручную:

```bash
docker compose -f docker-compose.yml -f docker-compose.recommender-demo.yml run --rm recommender-demo-report
```

Отчет появится в `recommendation-model-report.md`.

Очистить demo-данные, историю рекомендаций и Redis-выдачу по `dataset_id`:

```bash
docker compose -f docker-compose.yml -f docker-compose.recommender-demo.yml --profile demo-tools run --rm recommender-demo-clean
```

Единый человекочитаемый отчет для защиты находится в `recommendation-model-report.md`. Машинный JSON последнего большого теста можно пересобрать в `docs/recommendation-big-test-report.json`.

Что уже сделано по большому синтетическому тесту:

- добавлен генератор `generate_synthetic_forum_dataset`;
- добавлен масштабируемый конфиг `SyntheticScale`;
- добавлены скрытые профили пользователей и тематические профили тредов;
- добавлен feedback loop рекомендаций через `recommendation_impression` и `recommendation_clicked`;
- добавлены daily aggregates для текущего pipeline;
- добавлен validation helper;
- добавлены smoke tests генератора и проверки, что датасет проходит `prepare_data` с train/test split;
- добавлен CLI `python3 -m recommender.synthetic` с фиксированным seed `9400` и edge-case seeds;
- добавлен отчет train/test split, который проверяет, что evaluation идет по будущим событиям без пересечения user/thread pairs с train;
- добавлен загрузчик synthetic fixture в PostgreSQL и ClickHouse: `recommender.synthetic_loader`;
- добавлены recommender tests для подготовки данных, модели, метрик, baseline comparison, storage loader и большого pipeline smoke;
- добавлены backend controller tests для endpoint рекомендаций;
- добавлен сохраненный пример большого отчета с top-N рекомендациями, метриками, baseline comparison и excluded threads.

## Документация

- [API](docs/api.md)
- [Архитектура](docs/architecture.md)
- [Деплой](docs/deployment.md)
