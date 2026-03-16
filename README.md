# 🖨️ Dyz-Art MAS | Multi-Agent System для Виробничого Планування

**Multi-Agent System для автоматичної генерації технологічних маршрутів у поліграфічній індустрії**

---

## 📋 Опис проекту

Цей проект реалізує Multi-Agent System (MAS) для компанії Dyz-Art, яка спеціалізується на виробництві преміум-упаковки, коробок для настільних ігор, колод карт та правил гри. Система автоматично перетворює неструктуровані запити клієнтів у детальні технологічні маршрути виробництва та Технічні Завдання (Excel).

### Основні можливості

- 🤖 **4 спеціалізовані агенти** працюють послідовно для обробки замовлення
- 💬 **Інтерактивний діалог** з клієнтом для витягування вимог
- 🔧 **Автоматична генерація маршрутів** на основі бази знань матеріалів, операцій та обладнання
- 👤 **Human-in-the-Loop** механізм для вирішення неоднозначностей
- 📊 **Генерація Excel Work Order** з детальними технологічними маршрутами
- 💰 **Калькуляція вартості** для різних тиражних рівнів

---

## 🏗️ Архітектура

### Агенти

1. **Client Interface Agent** (`agents/client_interface.py`)
   - Ведеть діалог з клієнтом
   - Витягує структуровані вимоги з природньої мови
   - Ідентифікує компоненти продукту (коробка, карти, правила тощо)

2. **Technologist Agent** (`agents/technologist.py`)
   - Підбирає сумісні матеріали з бази знань
   - Будує технологічний маршрут для кожного компонента
   - Враховує обмеження обладнання та тираж

3. **Validation Agent** (`agents/validation.py`)
   - Перевіряє повноту та технічну можливість маршрутів
   - Виявляє неоднозначності (відсутній клей, несумісні матеріали)
   - Запускає Human-in-the-Loop при потребі

4. **Generation Agent** (`agents/generation.py`)
   - Генерує Технічне Завдання (Excel)
   - Розраховує орієнтовну вартість для різних тиражів
   - Формує фінальні документи для виробництва

### LangGraph Workflow

```
START
  └─► client_interface ──► technologist ──► validation
                                          │
                           ┌─ needs_human ─┘
                           │       ▲
                           ▼       │
                       human_review ─┘
                           │
                validated  └─► generation ──► END
```

### База знань

- `knowledge_base/materials.json` — матеріали (папір, картон, клеї, оздоблення)
- `knowledge_base/operations.json` — виробничі операції та типові маршрути
- `knowledge_base/machines.json` — обладнання та технічні обмеження

---

## 🚀 Швидкий старт

### 1. Клонування репозиторію

```bash
git clone git@github.com:yarynas21/Savkiv_Yaryna_Thesis_2025.git
cd Savkiv_Yaryna_Thesis_2025
```

### 2. Створення віртуального середовища

```bash
python -m venv venv

# Активація (macOS/Linux)
source venv/bin/activate

# Активація (Windows)
venv\Scripts\activate
```

### 3. Встановлення залежностей

```bash
pip install -r requirements.txt
```

### 4. Налаштування API ключів

Створіть файл `.env` на основі `env.example`:

```bash
cp env.example .env
```

Відредагуйте `.env` та додайте ваш API ключ:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
```

**Підтримувані провайдери:**
- `openai` — GPT-4o (за замовчуванням)
- `anthropic` — Claude 3.5 Sonnet
- `google` — Gemini 1.5 Pro

### 5. Запуск Streamlit додатку

```bash
streamlit run app.py
```

Відкрийте браузер за адресою `http://localhost:8501`

---

## 📖 Використання

### Приклад замовлення

Введіть у чат:

> *"Мені потрібна преміальна коробка для колекційної настільної гри тираж 1000 шт., з колодою 110 карт і правилами. Дедлайн — 30 днів"*

### Процес обробки

1. **Client Interface Agent** задає уточнюючі питання (якщо потрібно)
2. **Technologist Agent** формує технологічні маршрути для кожного компонента
3. **Validation Agent** перевіряє маршрути на повноту
4. Якщо є неоднозначності → система запитує відповідь технолога-експерта
5. **Generation Agent** генерує Excel Work Order та калькуляцію вартості
6. Завантажте готовий файл через кнопку "Завантажити Технічне Завдання"

### Структура Excel Work Order

- **Лист 1: Технічне Завдання** — метадані замовлення
- **Лист 2: Маршрути виробництва** — детальні операції для кожного компонента
- **Лист 3: Калькуляція** — орієнтовна вартість по тиражних рівнях

---

## 🛠️ Технологічний стек

- **LangChain** / **LangGraph** — оркестрація агентів та workflow
- **Streamlit** — веб-інтерфейс
- **openpyxl** — генерація Excel документів
- **Python 3.10+** — мова програмування

### LLM провайдери

- OpenAI GPT-4o
- Anthropic Claude 3.5 Sonnet
- Google Gemini 1.5 Pro

---

## 📁 Структура проекту

```
Savkiv_Yaryna_Thesis_2025/
├── app.py                        # Streamlit UI
├── graph/
│   ├── state.py                  # ProductionState (TypedDict)
│   └── workflow.py               # LangGraph StateGraph
├── agents/
│   ├── llm_factory.py             # Фабрика LLM (підтримка 3 провайдерів)
│   ├── client_interface.py        # Client Interface Agent
│   ├── technologist.py           # Technologist Agent
│   ├── validation.py             # Validation Agent
│   └── generation.py             # Generation Agent
├── knowledge_base/
│   ├── materials.json            # База матеріалів
│   ├── operations.json           # База операцій
│   └── machines.json             # База обладнання
├── tools/
│   ├── excel_generator.py        # Генератор Excel Work Order
│   └── cost_calculator.py        # Калькулятор вартості
├── requirements.txt
├── env.example                   # Шаблон конфігурації
└── README.md
```

---

## 🔧 Розробка

### Додавання нових матеріалів

Відредагуйте `knowledge_base/materials.json`:

```json
{
  "papers": [
    {
      "id": "new_material_id",
      "name": "Назва матеріалу",
      "type": "cardboard",
      "weight_gsm": 300,
      "compatible_with": ["offset_printing", "lamination"],
      "typical_use": ["rigid_box_cover"]
    }
  ]
}
```

### Додавання нових операцій

Додайте запис у `knowledge_base/operations.json` та оновіть `product_type_routes` для відповідних типів продуктів.

### Тестування з різними LLM

Змініть `LLM_PROVIDER` у `.env`:

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
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
    {
      "step": 1,
      "operation_id": "prepress",
      "operation_name": "Допечатна підготовка",
      "machine": null
    },
    {
      "step": 2,
      "operation_id": "offset_printing",
      "operation_name": "Офсетний друк",
      "machine": "heidelberg_sm74"
    }
  ]
}
```

### Калькуляція вартості

```json
{
  "base_quantity": 1000,
  "variable_cost_per_1k": 8500.0,
  "setup_costs": 3500.0,
  "tiers": {
    "500 шт.": 7750.0,
    "1,000 шт.": 12300.0,
    "2,500 шт.": 25562.5,
    "5,000 шт.": 43125.0
  }
}
```

---

## 📊 Візуалізація графа

Для візуалізації структури LangGraph workflow:

```bash
# Встановити graphviz (якщо ще не встановлено)
pip install graphviz

# macOS
brew install graphviz

# Ubuntu/Debian
sudo apt-get install graphviz

# Windows: завантажити з https://graphviz.org/download/

# Генерувати візуалізацію
python visualize_graph.py

# Або з параметрами
python visualize_graph.py --format svg --output my_workflow
```

Скрипт створить файли:
- `workflow_graph.png` (або інший формат) — візуалізація
- `workflow_graph.dot` — вихідний код графа (можна редагувати)

---

## 🎓 Академічний контекст

Цей проект є частиною бакалаврської дипломної роботи:

**Тема:** Development of a Multi-Agent System for Production Workflow Generation in the Printing Industry

**Мета:** Автоматизувати процес генерації технологічних маршрутів та Технічних Завдань для поліграфічного підприємства Dyz-Art, зменшивши залежність від ручної роботи технологів та підвищивши швидкість обробки замовлень.

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
- **LangChain** / **LangGraph** команда за потужний фреймворк для побудови агентів
