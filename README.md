# 🖨️ Dyz-Art MAS | Multi-Agent System для Виробничого Планування

**Multi-Agent System для автоматичної генерації технологічних маршрутів у поліграфічній індустрії**

---

## 📋 Опис проекту

Цей проект реалізує Multi-Agent System (MAS) для компанії Dyz-Art, яка спеціалізується на виробництві преміум-упаковки, коробок для настільних ігор, колод карт та правил гри. Система автоматично перетворює неструктуровані запити клієнтів у детальні технологічні маршрути виробництва та Технічні Завдання (Excel).

### Основні можливості

- 🤖 **4 спеціалізовані агенти** працюють послідовно для обробки замовлення
- 💬 **Інтерактивний діалог** з клієнтом для витягування вимог
- 🔧 **Автоматична генерація маршрутів** на основі бази знань
- 👤 **Human-in-the-Loop** механізм для вирішення неоднозначностей
- 📊 **Генерація Excel Work Order** з детальними технологічними маршрутами
- 💰 **Калькуляція вартості** для різних тиражних рівнів
- 🔒 **JWT-автентифікація** — безпечний вхід для кожного користувача

---

## 🏗️ Архітектура

Система розділена на три Docker-сервіси:

```
┌─────────────────────┐     HTTP/JSON     ┌────────────────────────────────┐
│  frontend/app.py    │ ────────────────► │  backend/main.py (FastAPI)     │
│  Streamlit UI       │                   │                                │
│  port 8501          │ ◄──────────────── │  POST  /auth/register          │
└─────────────────────┘   SessionState    │  POST  /auth/token             │
                                          │  GET   /auth/me                │
                                          │                                │
                                          │  POST  /api/sessions           │
                                          │  POST  /api/sessions/{id}/...  │
                                          │  GET   /api/sessions/{id}/excel│
                                          │  port 8000                     │
                                          └──────────────┬─────────────────┘
                                                         │ SQLAlchemy
                                                         ▼
                                          ┌──────────────────────────────┐
                                          │  PostgreSQL 16               │
                                          │  база знань + users          │
                                          │  port 5432                   │
                                          └──────────────────────────────┘
```

### Агенти

1. **Client Interface Agent** — веде діалог, витягує вимоги
2. **Technologist Agent** — будує маршрут із бази знань PostgreSQL
3. **Validation Agent** — перевіряє повноту, запускає Human-in-the-Loop
4. **Generation Agent** — генерує Excel Work Order і калькуляцію

---

## 🚀 Швидкий старт (Docker Compose)

### 1. Клонування

```bash
git clone git@github.com:yarynas21/Savkiv_Yaryna_Thesis_2025.git
cd Savkiv_Yaryna_Thesis_2025
```

### 2. Налаштування `.env`

```bash
cp env.example .env
```

Відкрийте `.env` і заповніть:

```env
# LLM (оберіть один провайдер)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
# або
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
# або
# LLM_PROVIDER=google
# GOOGLE_API_KEY=...

# JWT (згенеруйте новий ключ для продакшену!)
JWT_SECRET_KEY=5035067f3fe79f75af76cd0670abcfbff9ad1dad4d4767ae076c000d5bbb765a
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# PostgreSQL (див. env.example — паролі тільки в .env, не в git)
POSTGRES_DB=dyzart
POSTGRES_USER=dyzart_app
POSTGRES_PASSWORD=...
POSTGRES_READONLY_USER=dyzart_ro
POSTGRES_READONLY_PASSWORD=...
```

> ⚠️ **`API_BASE_URL`** у Docker підставляється автоматично. **`DATABASE_URL`** для бекенда в контейнері збирається з `POSTGRES_*` у `.env`. Для **Rocket Admin / DBeaver** використовуй ті самі `POSTGRES_*` (або read-only користувача) — повна інструкція: [`backend/db/README.md`](backend/db/README.md).

Перед першим запуском (якщо використовуєш read-only роль): `chmod +x backend/db/004_readonly_role.sh`.

### 3. Запуск

```bash
docker compose up --build
```

| Сервіс    | URL                       |
|-----------|---------------------------|
| Streamlit | http://localhost:8501     |
| FastAPI   | http://localhost:8000     |
| Swagger   | http://localhost:8000/docs|

---

## 🔐 Автентифікація

### Вхід через веб-інтерфейс

Відкрийте http://localhost:8501 — з'явиться форма входу.

**Дефолтні акаунти** (готові після першого запуску):

| Логін      | Пароль        | Роль     |
|------------|---------------|----------|
| `admin`    | `admin123`    | admin    |
| `operator` | `operator123` | operator |
| `expert`   | `expert123`   | expert   |

> ⚠️ Змініть паролі перед деплоєм у продакшен!

### Реєстрація нового користувача

- Через інтерфейс: вкладка **"Реєстрація"** на сторінці входу
- Через API: `POST /auth/register`

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
# → {"access_token": "eyJ...", "token_type": "bearer"}
```

### Захищені ендпоінти

Всі `/api/*` ендпоінти потребують заголовка:

```
Authorization: Bearer <access_token>
```

---

## 📖 Використання

### Процес роботи

1. Увійдіть або зареєструйтесь
2. Введіть замовлення у чаті, наприклад:
   > *"Потрібна преміальна коробка для настільної гри тираж 1000 шт., колода 110 карт, правила. Дедлайн 30 днів"*
3. Система задасть уточнюючі питання
4. Агенти сформують маршрути і Work Order
5. Завантажте Excel через кнопку **"Завантажити Технічне Завдання"**

---

## 📁 Структура проекту

```
Savkiv_Yaryna_Thesis_2025/
├── backend/                          # FastAPI-сервер (порт 8000)
│   ├── main.py                       # FastAPI app + CORS + lifespan
│   ├── entrypoint.sh                 # Docker entrypoint
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── api/
│   │   ├── routes.py                 # REST-ендпоінти (захищені JWT)
│   │   └── schemas.py                # Pydantic-моделі
│   ├── auth/
│   │   ├── routes.py                 # /auth/register, /auth/token, /auth/me
│   │   ├── schemas.py                # UserCreate, Token, UserOut
│   │   ├── utils.py                  # bcrypt + JWT (python-jose)
│   │   └── dependencies.py          # get_current_user, require_role
│   ├── db/
│   │   ├── 001_schema.sql            # DDL: всі таблиці
│   │   ├── 002_seed.sql              # Seed: база знань (матеріали, операції, машини)
│   │   ├── 003_users.sql             # DDL users + дефолтні акаунти
│   │   ├── connection.py             # SQLAlchemy engine
│   │   ├── models.py                 # Table-об'єкти
│   │   └── repository.py            # get_kb_machines / materials / operations
│   ├── agents/
│   │   ├── llm_factory.py
│   │   ├── client_interface.py
│   │   ├── technologist.py
│   │   ├── validation.py
│   │   └── generation.py
│   ├── graph/
│   │   ├── state.py
│   │   └── workflow.py
│   ├── tools/
│   │   ├── excel_generator.py
│   │   └── cost_calculator.py
│   └── utils/
│       └── logger.py
├── frontend/                         # Streamlit UI (порт 8501)
│   ├── app.py                        # UI + логін/реєстрація + httpx → FastAPI
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml                # PostgreSQL + backend + frontend
├── .env                              # Конфігурація (не комітити!)
├── env.example                       # Шаблон
└── README.md
```

---

## 🛠️ Технологічний стек

| Шар | Технологія |
|-----|-----------|
| **Backend API** | FastAPI + Uvicorn |
| **Workflow / Agents** | LangChain + LangGraph |
| **Frontend UI** | Streamlit |
| **База даних** | PostgreSQL 16 |
| **ORM / SQL** | SQLAlchemy Core |
| **Автентифікація** | JWT (python-jose) + bcrypt (passlib) |
| **HTTP клієнт** | httpx |
| **Excel генерація** | openpyxl |
| **Контейнеризація** | Docker + Docker Compose |
| **Мова** | Python 3.11 |

### LLM провайдери

- OpenAI GPT-4o
- Anthropic Claude 3.5 Sonnet
- Google Gemini 1.5 Pro

---

## 🔧 Розробка

### Зупинка і перезапуск

```bash
docker compose down          # зупинити
docker compose up --build    # зібрати і запустити знову
docker compose logs -f backend  # переглядати логи бекенду
```

### Скидання бази даних

```bash
docker compose down -v       # видаляє також postgres_data volume
docker compose up --build    # PostgreSQL ініціалізується наново
```

### Зміна пароля користувача через API

```bash
# 1. Отримайте токен адміна
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. Використовуйте токен для захищених запитів
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/auth/me
```

### Додавання матеріалів / операцій

Відредагуйте `backend/db/002_seed.sql` і перезапустіть зі скиданням volume:

```bash
docker compose down -v && docker compose up --build
```

### Тестування з різними LLM

Змініть у `.env`:

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

Потім:

```bash
docker compose down && docker compose up
```

### Візуалізація LangGraph workflow

```bash
cd backend
python ../visualize_graph.py
# → workflow_graph.png
```

---

## 📊 Приклади вихідних даних

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
    {"step": 2, "operation_id": "offset_printing", "operation_name": "Офсетний друк",       "machine": "heidelberg_sm74"}
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

---

## 🎓 Академічний контекст

**Тема:** Development of a Multi-Agent System for Production Workflow Generation in the Printing Industry

**Мета:** Автоматизувати процес генерації технологічних маршрутів та Технічних Завдань для поліграфічного підприємства Dyz-Art.

---

## 📝 Ліцензія

MIT License — див. файл [LICENSE](LICENSE)

---

## 👤 Автор

**Yaryna Savkiv**  
GitHub: [@yarynas21](https://github.com/yarynas21)

---

## 🙏 Подяки

- Компанія **Dyz-Art** за надання доступу до виробничих процесів
- **LangChain** / **LangGraph** команда за потужний фреймворк
