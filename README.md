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
git clone git@github.com:yarynas21/Savkiv_Yaryna_Thesis_2026.git
cd Savkiv_Yaryna_Thesis_2026
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

## Дані БД для запуску (без пушу в git)

> [!WARNING]
> Я не пушу `backend/db/seeds` у git.  
> Без цих даних проєкт може піднятись технічно (контейнери стартують), але
> **функціонально не працюватиме коректно**: агенти не зможуть будувати валідні
> маршрути, калькуляція буде неповною, а дефолтні акаунти можуть бути відсутні.

Я **не пушу дані з `backend/db/seeds` у git**, бо це операційні/внутрішні дані.
Але щоб у вас локально проєкт запустився коректно, ці seed-таблиці мають бути
заповнені.

Що саме потрібно імпортувати:

- `01_machines.sql` → `machines`  
  Довідник обладнання (друк, висічка, каширування, ламінація тощо) з технічними
  лімітами.
- `02_machine_constraints.sql` → `machine_constraints`  
  Глобальні виробничі обмеження (кліше/штампи, мінімальні тиражі, ліміти формату).
- `03_papers.sql` → `papers`  
  Канонічні типи паперу/картону/чіпборду, які використовує MAS при виборі
  маршруту.
- `04_stock_items.sql` → `stock_items`  
  Складські позиції з прив'язкою до `papers` (`paper_id`), щоб агент враховував
  реальні матеріали.
- `05_finishes.sql` → `finishes`  
  Типи оздоблення (matte/gloss/soft-touch/uv/foil/embossing) і сумісності.
- `06_adhesives.sql` → `adhesives`  
  Клеї та їхні сценарії застосування.
- `07_operations.sql` → `operations`  
  Повний каталог технологічних операцій з параметрами і межами застосування.
- `08_product_type_routes.sql` → `product_type_routes`  
  Базові послідовності операцій для типів продуктів (`rigid_box`, `card_deck`,
  `rulebook_*`, `game_board` тощо).
- `09_game_components.sql` → `game_components`  
  Закупні ігрові компоненти для розрахунку собівартості.
- `10_cost_rates.sql` → `cost_rates`  
  Тарифна сітка калькулятора (друк, ламінація, приладка, ручні роботи, папір).
- `11_users.sql` → `users`  
  Dev-користувачі для входу (`admin`, `operator`, `expert`), далі міграція
  переводить `operator` у `client`.

### Які колонки мають бути в seed-таблицях

Щоб уникнути помилок під час старту, структура має відповідати `backend/db/schema.sql`:

- `machines`  
  `id`, `name`, `type`, `operation`, `max_sheet_mm`, `min_sheet_mm`, `colors`, `min_run`, `max_run`, `max_stock_gsm`, `min_stock_gsm`, `max_pages`, `min_pages`, `supported_finishes`, `notes`.
- `machine_constraints`  
  `key`, `value`.
- `papers`  
  `id`, `name`, `type`, `weight_gsm`, `compatible_with`, `typical_use`, `thickness_mm`.
- `stock_items`  
  `stock_no`, `name`, `for_use`, `supply_form`, `notes`, `paper_id`.
- `finishes`  
  `id`, `name`, `applies_to`, `compatible_adhesives`, `notes`.
- `adhesives`  
  `id`, `name`, `compatible_materials`, `use_case`.
- `operations`  
  `id`, `name`, `step`, `description`, `required_for`, `compatible_materials`, `duration_config`, `output_text`, `min_run`, `max_run`.
- `product_type_routes`  
  `product_type`, `sort_order`, `operation_id`.
- `game_components`  
  `id`, `name`, `category`, `unit`, `price_uah`, `notes`.
- `cost_rates`  
  `category`, `rate_key`, `value_numeric`, `unit`, `notes`.
- `users`  
  `email`, `username`, `password_hash`, `role` (опційно: `is_active`, якщо додаєте вручну).

### Локальний запуск seed-даних

- Docker init підхоплює `schema.sql` + `seeds/*.sql` тільки на **новому volume**.
- Якщо seed-и змінились, перевідтворіть БД:

```bash
docker compose down -v
docker compose up --build
```

- Після підняття БД обов'язково застосуйте міграції:

```bash
cd backend
python -m db.migrate
```

Швидка перевірка після старту (опційно):

```sql
SELECT COUNT(*) FROM machines;
SELECT COUNT(*) FROM operations;
SELECT COUNT(*) FROM product_type_routes;
SELECT COUNT(*) FROM papers;
SELECT COUNT(*) FROM stock_items;
SELECT COUNT(*) FROM cost_rates;
SELECT COUNT(*) FROM users;
```

Мінімальні орієнтири (expected counts), щоб вважати seed-імпорт успішним:

- `machines` >= 30
- `machine_constraints` >= 10
- `papers` >= 20
- `stock_items` >= 90
- `finishes` >= 6
- `adhesives` >= 4
- `operations` >= 30
- `product_type_routes` >= 50
- `game_components` >= 10
- `cost_rates` >= 40
- `users` >= 3

### Як працювати, якщо `seeds/` не в git

Рекомендований підхід для команди:

1. Тримати `schema.sql` + порожні/прикладні seed-шаблони в репо.
2. Реальні seed-дані зберігати локально або в захищеному сховищі.
3. У `.env`/секретах передавати креденшіали і запускати імпорт локально перед стартом.

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
Savkiv_Yaryna_Thesis_2026/
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

