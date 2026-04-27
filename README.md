# Dyz-Art MAS — Multi-Agent System для Виробничого Планування

**Multi-Agent System для автоматичної генерації технологічних маршрутів у поліграфічній індустрії**

## Опис проекту

Цей проект реалізує Multi-Agent System (MAS) для компанії Dyz-Art, яка спеціалізується на виробництві преміум-упаковки, коробок для настільних ігор, колод карт та правил гри. Система автоматично перетворює неструктуровані запити клієнтів у детальні технологічні маршрути виробництва та Технічні Завдання (Excel).

### Основні можливості

- 4 LLM-агенти + Human-in-the-Loop вузол у LangGraph workflow
- Інтерактивний діалог з клієнтом для витягування вимог
- Автоматична генерація маршрутів на основі бази знань PostgreSQL
- Human-in-the-Loop механізм для вирішення технічних неоднозначностей
- Генерація Excel Work Order з детальними технологічними маршрутами
- Калькуляція вартості для різних тиражних рівнів
- JWT-автентифікація з рольовим доступом (admin / expert / client)

## Архітектура

Система складається з трьох Docker-сервісів:

```
┌─────────────────────┐     HTTP/JSON     ┌──────────────────────────────────┐
│  frontend/app.py    │ ────────────────► │  backend/main.py (FastAPI)       │
│  Streamlit UI       │                   │                                  │
│  port 8501          │ ◄──────────────── │  POST  /auth/register            │
└─────────────────────┘   SessionState    │  POST  /auth/token               │
                                          │  GET   /auth/me                  │
                                          │                                  │
                                          │  POST  /api/sessions             │
                                          │  POST  /api/sessions/{id}/...    │
                                          │  GET   /api/sessions/{id}/excel  │
                                          │  GET   /api/sessions/{id}/metrics│
                                          │  GET   /api/metrics/overview     │
                                          │                                  │
                                          │  POST  /api/interviews           │
                                          │  GET   /api/interviews/me        │
                                          │  POST  /api/interviews/{id}/...  │
                                          │                                  │
                                          │  GET   /api/inbox                │
                                          │  POST  /api/inbox/{id}/launch    │
                                          │  GET   /api/inbox/{id}/excel     │
                                          │                                  │
                                          │  GET   /api/admin/...            │
                                          │  port 8000                       │
                                          └──────────────┬───────────────────┘
                                                         │ SQLAlchemy
                                                         ▼
                                          ┌──────────────────────────────┐
                                          │  PostgreSQL 16               │
                                          │  база знань + users          │
                                          │  port 5432                   │
                                          └──────────────────────────────┘
```

### Агенти

1. **Conversational Agent** — веде діалог, витягує та структурує вимоги
2. **Technologist Agent** — будує маршрут із бази знань PostgreSQL
3. **Validation Agent** — перевіряє повноту, за потреби запускає Human-in-the-Loop
4. **Generation Agent** — генерує Excel Work Order і калькуляцію
5. **Human Review (pause node)** — точка втручання експерта у графі

### Типи графів

| Граф | Призначення |
|------|-------------|
| `interview_graph` | Клієнт самостійно заповнює вимоги через чат |
| `production_graph` | Технолог/Admin запускає повний пайплайн з уже зібраних даних |
| `full_graph` | Повний пайплайн від збору вимог до генерації ТЗ (для expert) |

## Швидкий старт (Docker Compose)

### 1. Клонування

```bash
git clone git@github.com:yarynas21/Savkiv_Yaryna_Thesis_2025.git
cd Savkiv_Yaryna_Thesis_2025
```

### 2. Налаштування `.env`

```bash
cp .env.example .env
```

Відкрийте `.env` і заповніть:

```env
# LLM Provider (оберіть один)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here

# JWT (згенеруйте новий ключ!)
JWT_SECRET_KEY=change-me-generate-with-secrets-token-hex-32

# PostgreSQL
POSTGRES_DB=dyzart
POSTGRES_USER=dyzart_app
POSTGRES_PASSWORD=change-me-StrongDbPass-1
DATABASE_URL=postgresql://dyzart_app:change-me-StrongDbPass-1@localhost:5432/dyzart
```

> ⚠️ У Docker `API_BASE_URL` для frontend підставляється автоматично (`http://backend:8000`).

### 3. Запуск

```bash
docker compose up --build
```

| Сервіс    | URL                        |
|-----------|----------------------------|
| Streamlit | http://localhost:8501      |
| FastAPI   | http://localhost:8000      |
| Swagger   | http://localhost:8000/docs |

## Автентифікація

### Вхід через веб-інтерфейс

Відкрийте http://localhost:8501 — з'явиться форма входу.

**Дефолтні акаунти** (після першого запуску + міграцій):

| Логін      | Пароль        | Роль   |
|------------|---------------|--------|
| `admin`    | `admin123`    | admin  |
| `client`   | `operator123` | client |
| `expert`   | `expert123`   | expert |

> ⚠️ Змініть паролі перед деплоєм у продакшен!

Міграція `001_rename_operator_to_client.sql` перейменовує роль `operator` → `client` та оновлює CHECK-обмеження.

### Реєстрація нового користувача

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"new@example.com","username":"newuser","password":"Secure123"}'
```

### Вхід через API (отримання токена)

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
# → {"access_token":"eyJ...","token_type":"bearer","expires_in":3600}
```

Всі `/api/*` ендпоінти потребують заголовка `Authorization: Bearer <access_token>`.

## Використання

### Процес роботи (client)

1. Увійдіть або зареєструйтесь
2. Введіть замовлення у чаті, наприклад:
   > *"Потрібна преміальна коробка для настільної гри тираж 1000 шт., колода 110 карт, правила. Дедлайн 30 днів"*
3. Система задасть уточнюючі питання
4. Після заповнення всіх полів — інтерв'ю потрапляє до inbox експерта

### Процес роботи (expert)

1. Відкрийте вкладку Inbox — видно завершені клієнтські інтерв'ю
2. Натисніть "Launch" — система запускає production_graph і формує маршрути
3. За потреби — надайте відповідь на питання валідатора (Human-in-the-Loop)
4. Завантажте Excel через кнопку "Завантажити Технічне Завдання"

## Структура проекту

```
Savkiv_Yaryna_Thesis_2025/
├── backend/                          # FastAPI-сервер (порт 8000)
│   ├── main.py                       # FastAPI app + CORS + lifespan
│   ├── entrypoint.sh                 # Docker entrypoint
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── api/
│   │   ├── routes.py                 # Legacy монолітний роутер (не активний)
│   │   ├── schemas.py                # Legacy Pydantic-схеми
│   │   ├── deps.py                   # Shared dependencies
│   │   ├── routers/                  # Активні роутери (по ролях / домену)
│   │   │   ├── sessions.py           # /api/sessions  (expert, admin)
│   │   │   ├── interviews_client.py  # /api/interviews (client)
│   │   │   ├── interviews_expert.py  # /api/inbox (expert, admin)
│   │   │   ├── metrics.py            # /api/metrics/*
│   │   │   ├── admin_users.py        # /api/admin/users
│   │   │   ├── admin_papers.py       # /api/admin/papers
│   │   │   ├── admin_components.py   # /api/admin/components
│   │   │   ├── admin_cost_rates.py   # /api/admin/cost-rates
│   │   │   └── admin_llm.py          # /api/admin/llm
│   │   └── schemas/                  # Pydantic-схеми по домену
│   │       ├── sessions.py
│   │       ├── interviews.py
│   │       └── admin.py
│   ├── auth/
│   │   ├── routes.py                 # /auth/register, /auth/token, /auth/me
│   │   ├── schemas.py
│   │   ├── utils.py                  # bcrypt + JWT
│   │   └── dependencies.py          # get_current_user, require_role
│   ├── db/
│   │   ├── migrate.py                # Lightweight migration runner
│   │   ├── migrations/               # SQL-міграції (виконуються у порядку)
│   │   │   ├── 001_rename_operator_to_client.sql
│   │   │   ├── 002_interview_sessions.sql
│   │   │   ├── 003_llm_runtime_settings.sql
│   │   │   └── 004_session_metrics_snapshots.sql
│   │   ├── seeds/                    # Початкові дані (01–11)
│   │   ├── connection.py             # SQLAlchemy engine
│   │   ├── models.py                 # Legacy table-об'єкти
│   │   ├── models/                   # Сучасні table-об'єкти по домену
│   │   ├── repositories/             # DB-функції по домену
│   │   └── repository.py             # get_kb_machines / materials / operations
│   ├── agents/
│   │   ├── registry.py               # Константи вузлів і ролей LLM
│   │   ├── llm_factory.py            # Фабрика чат-моделей (openai/anthropic)
│   │   ├── json_parser.py            # RobustJsonOutputParser
│   │   ├── conversational/           # ConversationalAgent
│   │   ├── technologist/             # TechnologistAgent
│   │   ├── validation/               # ValidationAgent
│   │   └── generation/               # GenerationAgent
│   ├── graph/
│   │   ├── state.py                  # ProductionState TypedDict
│   │   ├── workflow.py               # Складання StateGraph
│   │   ├── agent_subgraphs.py        # Підграфи кожного агента
│   │   ├── human_review.py           # HumanReview pause-node
│   │   └── registry.py               # Singleton-реєстр скомпільованих графів
│   ├── services/
│   │   ├── interview_service.py      # Логіка client-flow
│   │   ├── production_service.py     # Логіка expert/admin-flow
│   │   ├── metrics_service.py        # Агрегація LLM-метрик
│   │   └── admin_service.py          # CRUD для адмін-панелі
│   ├── tools/
│   │   ├── excel_generator.py        # openpyxl Work Order
│   │   ├── cost_calculator.py        # Калькуляція вартості
│   │   ├── knife_calculator.py       # Розрахунок висічних форм
│   │   └── llm_eval_metrics.py       # Latency/cost метрики
│   └── utils/
│       └── logger.py
├── frontend/                         # Streamlit UI (порт 8501)
│   ├── app.py
│   ├── api_client.py                 # HTTP-клієнт → FastAPI
│   ├── common/                       # Спільні компоненти
│   ├── views/                        # Окремі сторінки (client, expert, admin, auth)
│   ├── requirements.txt
│   └── Dockerfile
├── tests/
│   └── eval/                         # DeepEval + benchmark LLM-тести
├── docker-compose.yml
├── .env                              # Конфігурація (не комітити!)
├── .env.example                      # Шаблон
└── README.md
```

## Технологічний стек

| Шар | Технологія |
|-----|-----------|
| **Backend API** | FastAPI + Uvicorn |
| **Workflow / Agents** | LangChain + LangGraph |
| **Frontend UI** | Streamlit |
| **База даних** | PostgreSQL 16 |
| **ORM / SQL** | SQLAlchemy Core |
| **Автентифікація** | JWT (python-jose) + passlib[bcrypt] |
| **HTTP клієнт** | httpx |
| **Excel генерація** | openpyxl |
| **Контейнеризація** | Docker + Docker Compose |
| **Мова** | Python 3.11 |

### LLM провайдери

- OpenAI GPT-4o
- Anthropic Claude 3.5 Sonnet

## Розробка

### Зупинка і перезапуск

```bash
docker compose down             # зупинити
docker compose up --build       # зібрати і запустити знову
docker compose logs -f backend  # переглядати логи бекенду
```

### Скидання бази даних

```bash
docker compose down -v          # видаляє також postgres_data volume
docker compose up --build       # PostgreSQL ініціалізується наново
```

### Запуск міграцій вручну

```bash
cd backend
python -m db.migrate
```

### Зміна пароля користувача через API

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/auth/me
```

### Тестування з різними LLM

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

```bash
docker compose down && docker compose up
```

### LLM метрики (оцінка latency/cost)

- `GET /api/sessions/{thread_id}/metrics` — метрики поточної сесії
- `GET /api/metrics/overview` — агреговані метрики по всіх відомих сесіях

### Візуалізація LangGraph workflow

```bash
python visualize_graph.py
# → pipeline_graph.png
```

## Приклади вихідних даних

### Технологічний маршрут (JSON)

```json
{
  "component_id": "rigid_box",
  "component_name": "Жорстка коробка",
  "material": {
    "cover": "coated_350",
    "base": "grey_chipboard_2000",
    "adhesive": "hot_melt_EVA"
  },
  "operations": [
    {"step": 1, "operation_id": "prepress",        "operation_name": "Допечатна підготовка"},
    {"step": 2, "operation_id": "offset_printing", "operation_name": "Офсетний друк", "machine": "heidelberg_sm74"}
  ]
}
```

### Калькуляція вартості

```json
{
  "base_quantity": 1000,
  "tiers": {
    "500 шт.":   7750.0,
    "1,000 шт.": 12300.0,
    "2,500 шт.": 25562.5,
    "5,000 шт.": 43125.0
  }
}
```

## Академічний контекст

**Тема:** Development of a Multi-Agent System for Production Workflow Generation in the Printing Industry

**Мета:** Автоматизувати процес генерації технологічних маршрутів та Технічних Завдань для поліграфічного підприємства Dyz-Art.

## Ліцензія

MIT License — див. файл [LICENSE](LICENSE)

## Автор

**Yaryna Savkiv**  
GitHub: [@yarynas21](https://github.com/yarynas21)

## Подяки

- Компанія **Dyz-Art** за надання доступу до виробничих процесів
- **LangChain** / **LangGraph** команда за потужний фреймворк
