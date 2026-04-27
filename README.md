# Dyz-Art MAS — Multi-Agent System для Виробничого Планування

Multi-Agent System для автоматичної генерації технологічних маршрутів у поліграфічній індустрії.

## Про проект

Система реалізована для компанії Dyz-Art, яка виробляє преміум-упаковку, коробки для настільних ігор, колоди карт та правила гри. MAS автоматично перетворює запити клієнтів у детальні технологічні маршрути та Технічні Завдання (Excel).

Основне:

- 4 LLM-агенти + Human-in-the-Loop вузол у LangGraph workflow
- Діалог з клієнтом для збору вимог
- Генерація маршрутів на основі бази знань PostgreSQL
- Human-in-the-Loop для вирішення технічних неоднозначностей
- Генерація Excel Work Order з деталями маршруту та калькуляцією
- JWT-автентифікація, ролі: admin / expert / client

## Архітектура

```
┌─────────────────────┐     HTTP/JSON     ┌──────────────────────────────────┐
│  frontend/app.py    │ ────────────────► │  backend/main.py (FastAPI)       │
│  Streamlit UI       │                   │                                  │
│  port 8501          │ ◄──────────────── │  POST  /auth/register            │
└─────────────────────┘                   │  POST  /auth/token               │
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
                                          │  GET   /api/admin/users          │
                                          │  GET   /api/admin/papers         │
                                          │  GET   /api/admin/game_components│
                                          │  GET   /api/admin/cost_rates     │
                                          │  GET   /api/admin/llm            │
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
| `interview_graph` | Клієнт заповнює вимоги через чат |
| `production_graph` | Технолог/Admin запускає повний пайплайн із зібраних даних |
| `full_graph` | Повний пайплайн від збору вимог до генерації ТЗ (для expert) |

## Швидкий старт

### 1. Клонування

```bash
git clone git@github.com:yarynas21/Savkiv_Yaryna_Thesis_2025.git
cd Savkiv_Yaryna_Thesis_2025
```

### 2. Налаштування `.env`

```bash
cp .env.example .env
```

Заповніть `.env`:

```env
# LLM (оберіть один)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here

# JWT
JWT_SECRET_KEY=change-me-generate-with-secrets-token-hex-32

# PostgreSQL
POSTGRES_DB=dyzart
POSTGRES_USER=dyzart_app
POSTGRES_PASSWORD=change-me-StrongDbPass-1
DATABASE_URL=postgresql://dyzart_app:change-me-StrongDbPass-1@localhost:5432/dyzart
```

> У Docker `API_BASE_URL` для frontend підставляється автоматично (`http://backend:8000`).

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

Відкрийте http://localhost:8501 — з'явиться форма входу.

**Дефолтні акаунти** (створюються автоматично при першому запуску через `docker-entrypoint-initdb.d`):

| Логін      | Пароль        | Роль   |
|------------|---------------|--------|
| `admin`    | `admin123`    | admin  |
| `operator` | `operator123` | client |
| `expert`   | `expert123`   | expert |

> Змініть паролі перед деплоєм у продакшен!

Міграція `001_rename_operator_to_client.sql` змінює роль `operator` → `client` (username залишається `operator`). Міграції запускаються окремо від seeds — потрібно викликати вручну:

```bash
cd backend
python -m db.migrate
```

### Реєстрація нового користувача

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"new@example.com","username":"newuser","password":"Secure123"}'
```

### Отримання токена

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
# → {"access_token":"eyJ...","token_type":"bearer","expires_in":3600}
```

Всі `/api/*` ендпоінти потребують заголовка `Authorization: Bearer <access_token>`.

## Використання

### Клієнт

1. Увійдіть або зареєструйтесь
2. Введіть замовлення у чаті, наприклад:
   > *"Потрібна преміальна коробка для настільної гри тираж 1000 шт., колода 110 карт, правила. Дедлайн 30 днів"*
3. Система задасть уточнюючі питання
4. Після заповнення — інтерв'ю потрапляє до inbox експерта

### Експерт

1. Відкрийте вкладку Inbox — видно завершені клієнтські інтерв'ю
2. Натисніть "Launch" — система запускає production_graph
3. За потреби — надайте відповідь на питання валідатора (Human-in-the-Loop)
4. Завантажте Excel через кнопку "Завантажити Технічне Завдання"

## Структура проекту

```
Savkiv_Yaryna_Thesis_2025/
├── backend/
│   ├── main.py
│   ├── api/
│   │   ├── deps.py
│   │   ├── routers/
│   │   │   ├── sessions.py           # /api/sessions
│   │   │   ├── interviews_client.py  # /api/interviews
│   │   │   ├── interviews_expert.py  # /api/inbox
│   │   │   ├── metrics.py            # /api/metrics
│   │   │   ├── admin_users.py        # /api/admin/users
│   │   │   ├── admin_papers.py       # /api/admin/papers
│   │   │   ├── admin_components.py   # /api/admin/game_components
│   │   │   ├── admin_cost_rates.py   # /api/admin/cost_rates
│   │   │   └── admin_llm.py          # /api/admin/llm
│   │   └── schemas/
│   ├── auth/
│   ├── db/
│   │   ├── migrate.py
│   │   ├── migrations/
│   │   ├── seeds/
│   │   └── repositories/
│   ├── agents/
│   │   ├── registry.py
│   │   ├── llm_factory.py
│   │   ├── conversational/
│   │   ├── technologist/
│   │   ├── validation/
│   │   └── generation/
│   ├── graph/
│   │   ├── state.py
│   │   ├── workflow.py
│   │   ├── human_review.py
│   │   └── registry.py
│   ├── services/
│   ├── tools/
│   │   ├── excel_generator.py
│   │   ├── cost_calculator.py
│   │   └── knife_calculator.py
│   └── utils/
├── frontend/
│   ├── app.py
│   ├── api_client.py
│   ├── common/
│   └── views/
├── tests/
│   └── eval/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Стек

| Шар | Технологія |
|-----|-----------|
| Backend API | FastAPI + Uvicorn |
| Workflow / Agents | LangChain + LangGraph |
| Frontend UI | Streamlit |
| База даних | PostgreSQL 16 |
| ORM / SQL | SQLAlchemy Core |
| Автентифікація | JWT (python-jose) + passlib[bcrypt] |
| HTTP клієнт | httpx |
| Excel генерація | openpyxl |
| Контейнеризація | Docker + Docker Compose |
| Мова | Python 3.11 |

LLM провайдери: OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet.

## Розробка

```bash
docker compose down             # зупинити
docker compose up --build       # запустити знову
docker compose logs -f backend  # логи бекенду
docker compose down -v          # скинути postgres volume
```

### Тестування з різними LLM

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### LLM метрики

- `GET /api/sessions/{thread_id}/metrics` — метрики сесії
- `GET /api/metrics/overview` — агреговані метрики

## Академічний контекст

**Тема:** Development of a Multi-Agent System for Production Workflow Generation in the Printing Industry

**Мета:** Автоматизувати генерацію технологічних маршрутів та Технічних Завдань для поліграфічного підприємства Dyz-Art.

## Автор

**Yaryna Savkiv**  
GitHub: [@yarynas21](https://github.com/yarynas21)

## Ліцензія

MIT License — див. файл [LICENSE](LICENSE)
