"""DeepEval dataset for LLM-as-Judge evaluation of the conversational agent.

Unlike the exact-match dataset (dataset.py), these scenarios evaluate *qualitative*
aspects that a rule-based checker cannot assess:
  - Quality and relevance of follow-up questions
  - Guardrail behaviour as natural language
  - Multi-turn conversation coherence
  - Absence of hallucination in agent replies

Each DeepEvalScenario maps directly to a DeepEval LLMTestCase or
ConversationalTestCase (see test_deepeval.py).

Fields:
    id          — unique slug
    description — what quality aspect is tested
    category    — "followup" | "guardrail" | "hallucination" | "convo"
    input       — the human message sent to the agent
    context     — rules / KB facts the agent should follow (for faithfulness checks)
    expected_output — ideal behaviour description used by GEval judge
    history     — list of (human, assistant) prior turns for multi-turn cases
    accumulated — already-collected requirements/components dict
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeepEvalScenario:
    id: str
    description: str
    category: str
    input: str
    expected_output: str
    context: list[str] = field(default_factory=list)
    history: list[tuple[str, str]] = field(default_factory=list)
    accumulated: dict[str, Any] = field(default_factory=dict)
    ui_role: str = "client"  # "client" | "expert" — визначає context промпту
    threshold: float | None = None  # якщо None — використовується глобальний поріг тесту


# ---------------------------------------------------------------------------
# FOLLOW-UP QUESTION QUALITY
# The agent must ask targeted, non-repetitive, Ukrainian-language follow-ups.
# ---------------------------------------------------------------------------

FOLLOWUP_SCENARIOS: list[DeepEvalScenario] = [
    DeepEvalScenario(
        id="fq_first_message_general_fields",
        description="Перше повідомлення: агент має задати всі загальні поля одним блоком",
        category="followup",
        input="Потрібна коробка для настільної гри, тираж 1000, з колодою 110 карт і правилами.",
        expected_output=(
            "Відповідь має містити запит на: назву гри, ім'я клієнта, дедлайн, "
            "наявність комплектуючих, наявність додаткових елементів. "
            "Запитання мають бути в одному блоці, без повторення вже відомих даних (тираж 1000 не питається знову). "
            "Мова — українська, дружній тон."
        ),
        context=[
            "Агент збирає: назву гри, ім'я клієнта, тираж, дедлайн, комплектуючі, додаткові елементи.",
            "Тираж 1000 вже відомий — не питати знову.",
            "Питання мають бути у форматі маркованого списку Markdown.",
        ],
    ),
    DeepEvalScenario(
        id="fq_box_details_block",
        description="Загальний блок завершено — агент питає деталі коробки одним блоком",
        category="followup",
        input="Розмір коробки 300×200×60 мм.",
        history=[
            ("Потрібна коробка для гри «Феникс», тираж 500, правила.", "Назва гри, ім'я, дедлайн, комплектуючі?"),
            ("Назва «Феникс», я Максим, дедлайн 30 днів, без комплектуючих, без додаткових елементів.", "Дякую! Деталі коробки?"),
        ],
        accumulated={
            "requirements": {
                "quantity": 500,
                "product_name": "Феникс",
                "client_name": "Максим",
                "deadline_days": 30,
                "has_game_components": False,
                "has_additional_elements": False,
            },
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Феникс коробка", "size_mm": [300, 200, 60]},
                {"id": "rulebook", "type": "rulebook_thin", "name": "Правила гри"},
            ],
        },
        expected_output=(
            "Відповідь має запитати деталі коробки одним блоком: "
            "конструктив (кришка/дно, дно і рукав, самозбірна), "
            "друк (зовні чи також всередині), матеріал основи (гофра чи палітурний картон), "
            "товщину картону, ламінацію, УФ-лак, термопакування. "
            "Розмір коробки 300×200×60 НЕ питається — вже відомий."
        ),
        context=[
            "Загальний блок повністю заповнений: product_name, client_name, deadline_days, has_game_components=false, has_additional_elements=false.",
            "Розмір коробки 300×200×60 мм щойно вказав клієнт — не питати знову.",
            "Агент переходить до блоку деталей коробки: construction, print_sides, material, board_thickness_mm, lamination, uv_varnish, shrink_wrap.",
        ],
    ),
    DeepEvalScenario(
        id="fq_rulebook_details",
        description="Блок коробки і карт завершено — агент питає деталі правил",
        category="followup",
        input="Так, є правила гри.",
        history=[
            ("Гра «Місія», тираж 600, коробка 300×200×60, карти 80 шт., правила. Без комплектуючих і додаткових.", "Деталі коробки?"),
            ("Кришка і дно, мат, палітурний 1.75 мм.", "Деталі карт?"),
            ("63×88, 300 gsm, 4+4, матова ламінація.", "Чи є правила?"),
        ],
        accumulated={
            "requirements": {
                "quantity": 600,
                "product_name": "Місія",
                "client_name": "Ольга",
                "deadline_days": 21,
                "has_game_components": False,
                "has_additional_elements": False,
            },
            "components": [
                {
                    "id": "rigid_box", "type": "rigid_box", "name": "Місія коробка",
                    "size_mm": [300, 200, 60], "construction": "lid_and_base",
                    "material": "bookbinding_board", "board_thickness_mm": 1.75, "lamination": "matte",
                },
                {
                    "id": "card_deck", "type": "card_deck", "name": "Місія карти",
                    "card_count": 80, "card_size_mm": [63, 88], "gsm": 300,
                    "print_colors": "4+4", "front_finish": "matte_lamination", "back_finish": "matte_lamination",
                },
                {"id": "rulebook", "type": "rulebook_thin", "name": "Правила гри"},
            ],
        },
        expected_output=(
            "Відповідь має запитати три поля правил одним блоком: "
            "розмір (формат A5/A4/інший у мм), кількість сторінок, тип кріплення (на скобу / фальцювання). "
            "НЕ питає деталі коробки чи карт — вони вже заповнені."
        ),
        context=[
            "Загальний блок: заповнений. Блок коробки: заповнений. Блок карт: заповнений.",
            "Rulebook потребує: size_mm, pages, binding. Це наступний блок.",
            "Формати: A5=148×210, A4=210×297. Кріплення: saddle_stitch або folding.",
        ],
    ),
    DeepEvalScenario(
        id="fq_no_repeat_question",
        description="Агент НЕ повторює питань які вже відповіли — перебуває у блоці карт",
        category="followup",
        input="Карти 63×88 мм, 300 gsm, матова ламінація з обох сторін.",
        history=[
            ("Гра «Буря», тираж 800, карти 90 шт., коробка. Без комплектуючих.", "Деталі коробки?"),
            ("Коробка 320×220×65, кришка і дно, мат, 1.75 мм, без УФ, без термо.", "Деталі карт?"),
        ],
        accumulated={
            "requirements": {
                "quantity": 800,
                "product_name": "Буря",
                "client_name": "Іван",
                "deadline_days": 14,
                "has_game_components": False,
                "has_additional_elements": False,
            },
            "components": [
                {
                    "id": "rigid_box", "type": "rigid_box", "name": "Буря коробка",
                    "size_mm": [320, 220, 65], "construction": "lid_and_base",
                    "material": "bookbinding_board", "board_thickness_mm": 1.75,
                    "lamination": "matte", "uv_varnish": False, "shrink_wrap": False,
                },
                {"id": "card_deck", "type": "card_deck", "name": "Буря карти", "card_count": 90},
            ],
        },
        expected_output=(
            "Відповідь НЕ питає про розмір карт (63×88 щойно отримано), gsm (300 відомо), "
            "ламінацію (матова відома). "
            "Запитує тільки те що ще невідомо: print_colors та/або термопакування. "
            "Не дублює щойно надану інформацію."
        ),
        context=[
            "Щойно отримано: card_size_mm=[63,88], gsm=300, front_finish=matte_lamination, back_finish=matte_lamination.",
            "Ще не відомо для card_deck: print_colors, shrink_wrap.",
            "Загальний блок і блок коробки — вже заповнені.",
        ],
    ),
    DeepEvalScenario(
        id="fq_game_components_catalog_hint",
        description="У загальному блоці клієнт підтверджує кубики — агент фіксує і НЕ переходить до коробки",
        category="followup",
        input="Так, нам потрібні кубики.",
        history=[
            ("Гра «Острів», тираж 500, коробка, карти 60 шт.", "Назва «Острів», як звертатись, дедлайн, комплектуючі, додаткові?"),
            ("Я Тетяна, дедлайн 20 днів, є кубики.", "Чи купуєте самі чи підберемо з нашого каталогу?"),
        ],
        accumulated={
            "requirements": {
                "quantity": 500,
                "product_name": "Острів",
                "client_name": "Тетяна",
                "deadline_days": 20,
                "has_game_components": True,
                "has_additional_elements": False,
                "customer_provides_components": False,
            },
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Острів коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Острів карти", "card_count": 60},
            ],
        },
        expected_output=(
            "Агент фіксує has_game_components=true та game_components_notes='кубики'. "
            "Відповідь запитує уточнення: які саме позиції і в якій кількості потрібні "
            "(наприклад кубики D6 — скільки штук), або повідомляє що каталог буде надано. "
            "НЕ переходить до деталей коробки поки не вирішено питання комплектуючих. "
            "Тон — дружній. Каталог показує бекенд, а не LLM напряму — це нормально."
        ),
        context=[
            "Загальний блок: майже завершений. has_game_components=true вже відомо.",
            "Агент фіксує has_game_components=true і game_components_notes з назвою категорії.",
            "Каталог комплектуючих показує серверний крок після відповіді LLM — LLM не зобов'язаний перелічувати його вміст.",
            "Спершу треба вирішити питання комплектуючих, потім переходити до блоку коробки.",
        ],
        threshold=0.55,
    ),
    DeepEvalScenario(
        id="fq_progress_confirmation",
        description="Загальний блок: клієнт відповів на has_game_components і has_additional_elements — агент підтверджує і переходить до коробки",
        category="followup",
        input="Комплектуючих не треба, додаткових елементів також немає.",
        history=[
            ("Гра «Аура», тираж 700, коробка, карти 80 шт.", "Назва гри, ім'я, дедлайн, комплектуючі, додаткові елементи?"),
            ("Гра «Аура», я Богдан, дедлайн 25 днів.", "Чи є комплектуючі та додаткові елементи?"),
        ],
        accumulated={
            "requirements": {
                "quantity": 700,
                "product_name": "Аура",
                "client_name": "Богдан",
                "deadline_days": 25,
                "has_game_components": False,
                "has_additional_elements": False,
            },
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Аура коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Аура карти", "card_count": 80},
            ],
        },
        expected_output=(
            "Відповідь коротко підтверджує: 'Зафіксував: без комплектуючих, без додаткових елементів.' "
            "і одразу переходить до блоку деталей коробки. "
            "НЕ повторює питань про тираж, назву гри, ім'я чи дедлайн — вони вже відомі."
        ),
        context=[
            "Загальний блок щойно завершився: quantity=700, product_name='Аура', client_name='Богдан', deadline_days=25, has_game_components=false, has_additional_elements=false.",
            "Наступний блок — деталі коробки.",
            "Агент підтверджує і переходить до наступного блоку без зайвих питань.",
        ],
    ),
]

# ---------------------------------------------------------------------------
# GUARDRAIL BEHAVIOUR (qualitative — not just substring check)
# ---------------------------------------------------------------------------

GUARDRAIL_SCENARIOS: list[DeepEvalScenario] = [
    DeepEvalScenario(
        id="gr_off_topic_polite_redirect",
        description="Агент ввічливо пояснює профіль і запрошує до правильної теми",
        category="guardrail",
        input="Хочу замовити 500 рекламних банерів для виставки.",
        expected_output=(
            "Відповідь має: (1) ввічливо пояснити що Dyz-Art спеціалізується на преміум-упаковці "
            "для настільних ігор (коробки, карти, правила, поля, листівки); "
            "(2) запропонувати обговорити замовлення в цьому напрямку; "
            "(3) НЕ обіцяти виконати замовлення банерів; "
            "(4) НЕ бути грубим або зневажливим."
        ),
        context=[
            "Dyz-Art спеціалізується виключно на: коробках, картах, правилах, полях, листівках для настільних ігор.",
            "Банери, футболки, рекламна поліграфія — не в профілі компанії.",
        ],
    ),
    DeepEvalScenario(
        id="gr_mixed_request_game_plus_off",
        description="Змішаний запит: частково в профілі, частково ні — агент обробляє тільки ігрову частину",
        category="guardrail",
        input="Потрібна коробка для гри і ще буклет для офісу.",
        expected_output=(
            "Відповідь має: (1) прийняти замовлення на коробку для гри; "
            "(2) пояснити що буклет для офісу не входить в профіль; "
            "(3) продовжити збір даних саме про коробку для гри."
        ),
        context=[
            "Коробки для настільних ігор — в профілі.",
            "Офісні буклети — не в профілі.",
        ],
    ),
    DeepEvalScenario(
        id="gr_maintains_scope_after_redirect",
        description="Після відмови від off-topic агент повертається до збору вимог",
        category="guardrail",
        input="Зрозуміло, тоді замовимо коробку для гри «Вогонь», тираж 400.",
        history=[
            ("Хочу замовити принти на футболках.", "Dyz-Art спеціалізується на упаковці для настільних ігор..."),
        ],
        accumulated={},
        expected_output=(
            "Агент приймає нове замовлення на коробку і починає збір даних: "
            "запитує загальні поля (назва гри вже є — «Вогонь», тираж 400 вже є). "
            "Не повертається до теми футболок."
        ),
        context=[
            "Клієнт переорієнтувався на коробку для гри «Вогонь», тираж 400.",
            "Футболки більше не актуальні — не згадувати.",
        ],
    ),
]

# ---------------------------------------------------------------------------
# HALLUCINATION CHECKS
# Agent must NOT invent field values not mentioned in the conversation.
# ---------------------------------------------------------------------------

HALLUCINATION_SCENARIOS: list[DeepEvalScenario] = [
    DeepEvalScenario(
        id="hal_no_size_invented",
        description="Агент не вигадує size_mm якщо клієнт не назвав розмір",
        category="hallucination",
        input="Потрібна коробка для гри «Легіон», тираж 600.",
        expected_output=(
            "JSON відповідь НЕ має містити size_mm для коробки — клієнт не назвав розмір. "
            "Поле size_mm має бути null або відсутнє. "
            "Агент має запитати розмір у follow-up питанні."
        ),
        context=[
            "Агент витягує лише ті дані які клієнт явно надав.",
            "Розмір коробки НЕ можна вигадувати або брати 'за замовчуванням' без підтвердження клієнта.",
        ],
    ),
    DeepEvalScenario(
        id="hal_no_lamination_invented",
        description="Агент записує lamination='matte' за замовчуванням (правило промпту)",
        category="hallucination",
        input="Коробка 300×200×60 мм, кришка і дно.",
        expected_output=(
            "Агент записує lamination='matte' у JSON — це коректна поведінка за правилом промпту. "
            "У follow_up пропонує матову і підтверджує: 'Типово обираємо матову ламінацію — підтверджуєте?'. "
            "НЕ допускається: lamination='soft_touch', 'gloss' або інше довільне значення без підстави клієнта."
        ),
        context=[
            "Правило промпту: якщо клієнт не вказав ламінацію — запропонуй матову І запиши 'matte'.",
            "lamination=null є помилкою — промпт вимагає завжди записувати 'matte' як дефолт.",
            "Недопустимо: вигадати 'soft_touch' або будь-яке інше нестандартне значення без підстави.",
        ],
        threshold=0.60,
    ),
    DeepEvalScenario(
        id="hal_no_pages_invented",
        description="Агент не вигадує кількість сторінок правил",
        category="hallucination",
        input="Є правила A5.",
        expected_output=(
            "JSON не має містити pages з конкретним числом — клієнт сказав лише формат A5. "
            "size_mm=[148,210] може бути витягнуто. pages = null. binding = null. "
            "Агент питає кількість сторінок і кріплення."
        ),
        context=[
            "A5 → size_mm=[148,210] — коректно витягувати.",
            "Кількість сторінок і тип кріплення не були згадані — не вигадувати.",
        ],
    ),
    DeepEvalScenario(
        id="hal_no_extra_components",
        description="Агент не додає card_deck якщо клієнт замовив лише коробку",
        category="hallucination",
        input="Потрібна лише коробка для гри «Форт», 350×250×80 мм, тираж 200.",
        expected_output=(
            "product_components містить лише rigid_box. "
            "card_deck і rulebook відсутні — клієнт сказав 'лише коробка'. "
            "Агент НЕ додає компоненти яких не було в запиті."
        ),
        context=[
            "Клієнт явно сказав 'лише коробка' — інших компонентів не замовляв.",
            "Додавати card_deck або rulebook без підтвердження = hallucination.",
        ],
    ),
    DeepEvalScenario(
        id="hal_standalone_game_board_no_box",
        description="Standalone game_board: rigid_box НЕ додається автоматично",
        category="hallucination",
        input="Потрібне лише ігрове поле 840×594 мм, матова ламінація, тираж 300.",
        expected_output=(
            "product_components містить лише game_board з size_mm=[840,594] та lamination=matte. "
            "rigid_box відсутній — клієнт не замовляв коробку. "
            "Агент не вигадує компоненти."
        ),
        context=[
            "Клієнт замовив лише ігрове поле без коробки.",
            "rigid_box не слід додавати якщо клієнт його не згадував.",
        ],
    ),
]

# ---------------------------------------------------------------------------
# MULTI-TURN CONVERSATION QUALITY (ConversationalTestCase)
# ---------------------------------------------------------------------------

CONVO_SCENARIOS: list[DeepEvalScenario] = [
    DeepEvalScenario(
        id="cv_full_box_card_flow",
        description="Повна розмова коробка + карти: агент збирає дані послідовно",
        category="convo",
        input="Правила A5, 8 сторінок, на скобу.",
        history=[
            ("Гра «Нова Ера», тираж 800, коробка 300×200×60, карти 90 шт., правила.", "Деталі коробки?"),
            ("Кришка і дно, матова, 1.75 мм.", "Деталі карт?"),
            ("63×88 мм, 300 gsm, 4+4, матова ламінація.", "Деталі правил?"),
        ],
        accumulated={
            "requirements": {"quantity": 800, "product_name": "Нова Ера"},
            "components": [
                {
                    "id": "rigid_box", "type": "rigid_box", "name": "Нова Ера коробка",
                    "size_mm": [300, 200, 60], "construction": "lid_and_base",
                    "lamination": "matte", "board_thickness_mm": 1.75,
                },
                {
                    "id": "card_deck", "type": "card_deck", "name": "Нова Ера карти",
                    "card_count": 90, "card_size_mm": [63, 88],
                    "gsm": 300, "print_colors": "4+4", "front_finish": "matte_lamination",
                    "back_finish": "matte_lamination", "shrink_wrap": False,
                },
                {"id": "rulebook", "type": "rulebook_thin", "name": "Правила гри"},
            ],
        },
        expected_output=(
            "На фінальний turn («Правила A5, 8 сторінок, на скобу») агент має: "
            "(1) витягти size_mm=[148,210], pages=8, binding=saddle_stitch; "
            "(2) перевірити чи всі поля зібрані; "
            "(3) якщо так — повідомити що вимоги зафіксовано і передати технологу. "
            "Тон: підтверджувальний, лаконічний."
        ),
        context=[
            "Розмова майже завершена. Лишилось витягти деталі правил.",
            "A5 = size_mm=[148,210]. 'На скобу' = binding=saddle_stitch.",
            "Після заповнення всіх полів статус = complete.",
        ],
        threshold=0.5,
    ),
    DeepEvalScenario(
        id="cv_expert_phone_flow",
        description="Експерт заповнює за клієнта — розмова від імені клієнта по телефону",
        category="convo",
        ui_role="expert",
        input="Контрагент ТОВ «Фенікс», гра «Дракон», тираж 1000, коробка 300×200×60, карти 80 шт.",
        history=[],
        accumulated={},
        expected_output=(
            "Агент витягує: client_name='ТОВ «Фенікс»' або 'Фенікс' (контрагент), product_name='Дракон', "
            "quantity=1000, rigid_box з size_mm=[300,200,60], card_deck з card_count=80. "
            "Запитує загальні поля яких ще немає: дедлайн, комплектуючі, додаткові елементи, деталі коробки."
        ),
        context=[
            "Роль: expert → client_name означає контрагент/компанію (ТОВ, ФОП, назва фірми).",
            "Вже відомо: product_name='Дракон', quantity=1000, rigid_box size_mm=[300,200,60], card_count=80.",
        ],
        threshold=0.5,
    ),
    DeepEvalScenario(
        id="cv_correction_mid_conversation",
        description="Клієнт виправляє тираж — агент приймає виправлення без конфлікту",
        category="convo",
        input="Вибачте, тираж 800, а не 500.",
        history=[
            ("Гра «Зірка», тираж 500, коробка і карти 60 шт.", "Зафіксував тираж 500. Деталі коробки?"),
        ],
        accumulated={
            "requirements": {"quantity": 500, "product_name": "Зірка"},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Зірка коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Зірка карти", "card_count": 60},
            ],
        },
        expected_output=(
            "Агент приймає виправлення: оновлює quantity з 500 на 800. "
            "Підтверджує: 'Зафіксував тираж 800.' "
            "Продовжує збір даних з того ж місця (деталі коробки). "
            "НЕ починає розмову спочатку."
        ),
        context=[
            "Клієнт виправляє кількість з 500 на 800 — приймаємо нове значення.",
            "Всі інші дані (product_name, card_count) залишаються без змін.",
        ],
        threshold=0.5,
    ),
    DeepEvalScenario(
        id="cv_catalog_then_selection",
        description="Після показу каталогу клієнт вибирає — агент фіксує правильно",
        category="convo",
        input="Беру кубики D6 пластикові — 500 штук.",
        history=[
            ("Гра «Вогонь», тираж 600, є кубики.", "Ось каталог: кубики D6 — 6 грн/шт, ..."),
        ],
        accumulated={
            "requirements": {
                "quantity": 600,
                "product_name": "Вогонь",
                "has_game_components": True,
                "customer_provides_components": False,
            },
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Вогонь коробка"},
            ],
        },
        expected_output=(
            "Агент фіксує вибір: game_components_notes містить 'кубики D6 пластикові — 500 шт'. "
            "НЕ показує каталог повторно. "
            "Переходить до наступних питань (деталі коробки або дедлайн)."
        ),
        context=[
            "Каталог вже був показаний у попередньому turn.",
            "Клієнт вибрав: кубики D6 пластикові, 500 штук.",
            "game_components_notes має зафіксувати цей вибір дослівно.",
        ],
        threshold=0.5,
    ),
]

# ---------------------------------------------------------------------------
# FOLLOW-UP QUALITY — extended batch
# ---------------------------------------------------------------------------

FOLLOWUP2_SCENARIOS: list[DeepEvalScenario] = [
    DeepEvalScenario(
        id="fq2_game_board_details_block",
        description="Деталі ігрового поля — агент запитує всі поля одним блоком",
        category="followup",
        input="Так, є ігрове поле.",
        history=[
            ("Гра «Горизонт», тираж 500, коробка, карти 70 шт.", "Чи є ігрове поле або листівка?"),
        ],
        accumulated={
            "requirements": {"quantity": 500, "product_name": "Горизонт", "has_additional_elements": True},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Горизонт коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Горизонт карти", "card_count": 70},
                {"id": "game_board", "type": "game_board", "name": "Ігрове поле"},
            ],
        },
        expected_output=(
            "Відповідь має запитати деталі ігрового поля одним блоком: "
            "розмір у розгорнутому вигляді (мм), спосіб складання (скільки згинів), "
            "товщину палітурного картону, чи друк лише з лиця чи також із звороту, "
            "обклейка торців чи кашероване, ламінація (глянець/мат). "
            "Всі поля в одному питанні — не розбивати на окремі повідомлення."
        ),
        context=[
            "game_board потребує: size_mm, fold_description, board_thickness_mm, print_sides, edge_finish, lamination.",
            "Типово пропонуємо 1.75 мм якщо клієнт не знає.",
        ],
    ),
    DeepEvalScenario(
        id="fq2_leaflet_details_block",
        description="Деталі листівки — агент запитує розмір, друк, біговку",
        category="followup",
        input="Так, є інформаційна листівка.",
        history=[
            ("Гра «Азимут», тираж 600, коробка, карти 60 шт.", "Чи є листівка або ігрове поле?"),
        ],
        accumulated={
            "requirements": {"quantity": 600, "product_name": "Азимут", "has_additional_elements": True},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Азимут коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Азимут карти", "card_count": 60},
                {"id": "info_leaflet", "type": "info_leaflet", "name": "Інформаційна листівка"},
            ],
        },
        expected_output=(
            "Відповідь має запитати три поля листівки одним блоком: "
            "розмір (мм), колірність друку з двох сторін (наприклад 4+4), "
            "чи є біговка (так/ні). "
            "Тон — чіткий і конкретний."
        ),
        context=[
            "info_leaflet потребує: size_mm, print_colors, has_crease.",
            "Ці три поля запитуються разом, одним блоком.",
        ],
    ),
    DeepEvalScenario(
        id="fq2_default_thickness_proposal",
        description="Клієнт не знає товщину — агент пропонує стандарт 1.75 мм",
        category="followup",
        input="Не знаю яка товщина картону зазвичай.",
        history=[
            ("Гра «Ескіз», тираж 800, коробка 300×200×60, кришка і дно.", "Яка товщина палітурного картону?"),
        ],
        accumulated={
            "requirements": {"quantity": 800, "product_name": "Ескіз"},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Ескіз коробка",
                 "size_mm": [300, 200, 60], "construction": "lid_and_base"},
            ],
        },
        expected_output=(
            "Агент пропонує стандарт 1.75 мм і просить підтвердити: "
            "'Зазвичай обираємо 1.75 мм — підходить?' "
            "НЕ записує 1.75 без підтвердження клієнта. "
            "Тон — інформативний, пропонує а не нав'язує."
        ),
        context=[
            "Стандартна товщина у Dyz-Art: 1.75 мм.",
            "Якщо клієнт не знає — пропонуємо 1.75 і чекаємо підтвердження.",
        ],
    ),
    DeepEvalScenario(
        id="fq2_matte_lamination_proposal",
        description="Ламінація не вказана — агент пропонує матову і записує matte (правило промпту)",
        category="followup",
        input="Коробка 300×200×60, кришка і дно, палітурний картон 1.75 мм.",
        expected_output=(
            "Агент витягує деталі коробки (size_mm, construction, material, board_thickness_mm) "
            "і записує lamination='matte' у JSON (правило: якщо ламінація не вказана — пиши matte). "
            "У follow_up запитує загальні поля яких ще немає (назва гри, ім'я/контрагент, тираж, "
            "дедлайн, комплектуючі, додаткові елементи) — це перший блок. "
            "У тексті follow_up може бути примітка що для коробки застосовано матову ламінацію. "
            "НЕ вигадує 'gloss' або 'soft_touch' без підстави клієнта."
        ),
        context=[
            "Це перше повідомлення: загальні поля ще не зібрані (ім'я, тираж, дедлайн, комплектуючі).",
            "Правило розмови: спочатку загальні питання, потім деталі компонентів.",
            "Правило промпту: якщо ламінація не вказана — запропонуй матову і запиши 'matte'.",
            "Запис lamination='matte' без явного підтвердження — коректна поведінка агента.",
        ],
    ),
    DeepEvalScenario(
        id="fq2_one_block_at_a_time",
        description="Агент не змішує питання різних блоків (коробка + карти в одному питанні)",
        category="followup",
        input="Потрібна коробка і карти 80 штук, тираж 700.",
        expected_output=(
            "Відповідь має запитати спочатку загальні поля (назва гри, ім'я, дедлайн, комплектуючі, додаткові елементи). "
            "НЕ запитує деталі коробки і деталі карт одночасно в одному повідомленні. "
            "Один блок за раз."
        ),
        context=[
            "Порядок: загальні → коробка → карти → правила → ігрове поле → листівка.",
            "Кожен блок питається окремо, не змішувати.",
        ],
    ),
    DeepEvalScenario(
        id="fq2_cards_print_colors_followup",
        description="Агент запитує колірність друку карт правильно",
        category="followup",
        input="Карти 63×88 мм, 100 штук, 300 gsm.",
        history=[
            ("Гра «Кит», тираж 500, коробка 300×200×60, карти 100 шт.", "Деталі карт?"),
        ],
        accumulated={
            "requirements": {"quantity": 500, "product_name": "Кит"},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Кит коробка", "size_mm": [300, 200, 60]},
                {"id": "card_deck", "type": "card_deck", "name": "Кит карти", "card_count": 100},
            ],
        },
        expected_output=(
            "Агент витягує card_size_mm=[63,88], gsm=300, card_count=100 і НЕ перепитує їх. "
            "У follow_up одним блоком запитує відсутні поля карт: "
            "колірність друку (наприклад 4+4, 4+0), "
            "покриття лицьової сторони (ламінація матова/глянцева або УФ-лак), "
            "покриття зворотньої сторони (чи те саме покриття). "
            "Термопакування карт також може бути запитане. "
            "Загальні поля (назва, тираж, дедлайн) вже відомі — НЕ перепитуються."
        ),
        context=[
            "Вже відомо: card_size_mm=[63,88], card_count=100, gsm=300.",
            "Вже відомо: product_name='Кит', quantity=500.",
            "Ще не відомо: print_colors, front_finish, back_finish, shrink_wrap.",
            "Агент повинен питати тільки відсутні поля карт одним блоком.",
        ],
    ),
    DeepEvalScenario(
        id="fq2_greeting_welcoming",
        description="На привітання — тепла відповідь без зайвих питань",
        category="followup",
        input="Добрий день!",
        expected_output=(
            "Відповідь: коротке привітання (1-2 речення), представлення компанії Dyz-Art "
            "як спеціаліста з преміум-упаковки для настільних ігор, "
            "запрошення описати замовлення. "
            "НЕ питає відразу про тираж чи розміри — лише вітається і запрошує."
        ),
        context=[
            "Dyz-Art — поліграфічна компанія, преміум-упаковка для настільних ігор.",
            "На привітання — відповідь коротка і дружня.",
        ],
    ),
    DeepEvalScenario(
        id="fq2_completion_announcement",
        description="Коли всі поля заповнені — агент оголошує завершення а не питає ще",
        category="followup",
        input="Так, без термопакування.",
        history=[
            ("Гра «Рій», тираж 400, коробка 280×190×55, кришка і дно, мат, 1.75 мм.", "Деталі карт?"),
            ("Карт немає. Правила A5, 8 стор., скоба.", "УФ-лак та термопакування?"),
        ],
        accumulated={
            "requirements": {
                "quantity": 400, "product_name": "Рій",
                "has_game_components": False, "has_additional_elements": False,
                "client_name": "Олена", "deadline_days": 21,
            },
            "components": [
                {
                    "id": "rigid_box", "type": "rigid_box", "name": "Рій коробка",
                    "size_mm": [280, 190, 55], "construction": "lid_and_base",
                    "material": "bookbinding_board", "board_thickness_mm": 1.75,
                    "lamination": "matte", "print_sides": "outside_only", "uv_varnish": False,
                },
                {
                    "id": "rulebook", "type": "rulebook_thin", "name": "Правила гри",
                    "size_mm": [148, 210], "pages": 8, "binding": "saddle_stitch",
                },
            ],
        },
        expected_output=(
            "Агент оголошує що всі вимоги зафіксовані і передає технологу для формування маршруту. "
            "НЕ задає нових питань. "
            "Підтверджує основні параметри замовлення коротко."
        ),
        context=[
            "Всі поля заповнені: quantity, product_name, client_name, deadline_days, rigid_box (всі поля), rulebook.",
            "has_game_components=false, has_additional_elements=false.",
            "shrink_wrap=false — щойно підтвердив клієнт.",
        ],
    ),
]

# ---------------------------------------------------------------------------
# GUARDRAIL QUALITY — extended batch
# ---------------------------------------------------------------------------

GUARDRAIL2_SCENARIOS: list[DeepEvalScenario] = [
    DeepEvalScenario(
        id="gr2_tsyshky_refuse",
        description="Ручки з логотипом — ввічлива відмова + редирект",
        category="guardrail",
        input="Хочу замовити 500 ручок з логотипом.",
        expected_output=(
            "Агент ввічливо пояснює що ручки не в профілі Dyz-Art. "
            "Пропонує обговорити упаковку для настільної гри. "
            "Тон — неагресивний, без глузування."
        ),
        context=[
            "Ручки, сувеніри, промо-продукція — не в профілі Dyz-Art.",
            "Профіль: коробки, карти, правила, поля, листівки для настільних ігор.",
        ],
    ),
    DeepEvalScenario(
        id="gr2_no_promise_fulfillment",
        description="Агент НЕ обіцяє виконати off-topic навіть якщо клієнт наполягає",
        category="guardrail",
        input="Але ви ж поліграфія, значить можете надрукувати журнал?",
        history=[
            ("Хочу замовити журнал 50 сторінок.", "Dyz-Art спеціалізується на упаковці для ігор..."),
        ],
        accumulated={},
        expected_output=(
            "Агент НЕ погоджується на журнал навіть після наполягання. "
            "Повторно пояснює спеціалізацію. "
            "Пропонує альтернативу в межах профілю або рекомендує звернутись до іншої компанії. "
            "НЕ каже 'можемо спробувати' або 'уточнимо у керівництва'."
        ),
        context=[
            "Журнали, книги, загальна поліграфія — поза профілем. Цю позицію не змінювати навіть під тиском.",
            "Агент може порадити звернутись до іншої компанії для off-topic запитів.",
        ],
    ),
    DeepEvalScenario(
        id="gr2_packaging_but_not_game",
        description="«Упаковка для ліків» — відмова хоч і слово 'упаковка' є",
        category="guardrail",
        input="Потрібна упаковка для таблеток, 500 штук маленьких коробочок.",
        expected_output=(
            "Агент розуміє що це медична упаковка, не ігрова. "
            "Пояснює що спеціалізується на упаковці для настільних ігор. "
            "Не приймає замовлення. Тон ввічливий."
        ),
        context=[
            "Медична упаковка, фармацевтичні коробки — не в профілі.",
            "Профіль строго: настільні ігри та їх компоненти.",
        ],
    ),
    DeepEvalScenario(
        id="gr2_game_request_accepted",
        description="Запит про гру — агент одразу починає збір вимог",
        category="guardrail",
        input="Мені потрібна коробка та карти для нової настільної гри.",
        expected_output=(
            "Агент одразу приймає замовлення і починає збір загальних даних: "
            "запитує назву гри, ім'я клієнта, тираж, дедлайн, комплектуючі, додаткові елементи. "
            "НЕ відмовляє, не питає 'чи точно це гра'. "
            "Тон — доброзичливий і ділової."
        ),
        context=[
            "Коробки і карти для настільних ігор — чітко в профілі Dyz-Art.",
            "Агент без зайвих питань починає збір даних.",
        ],
    ),
    DeepEvalScenario(
        id="gr2_partial_off_topic_only_game_processed",
        description="50%+50% запит: частина в профілі, частина ні — обробляємо тільки ігрову",
        category="guardrail",
        input="Потрібна коробка для гри і ще 200 рекламних листівок для офісу.",
        expected_output=(
            "Агент: (1) підтверджує коробку для гри і починає збір даних по ній; "
            "(2) пояснює що рекламні листівки для офісу — не в профілі Dyz-Art; "
            "(3) НЕ відмовляє від коробки для гри через наявність off-topic частини."
        ),
        context=[
            "Коробка для гри — в профілі. Рекламні офісні листівки — не в профілі.",
            "Обробляємо тільки ту частину замовлення що відповідає профілю.",
        ],
    ),
]

# ---------------------------------------------------------------------------
# HALLUCINATION — extended batch
# ---------------------------------------------------------------------------

HALLUCINATION2_SCENARIOS: list[DeepEvalScenario] = [
    DeepEvalScenario(
        id="hal2_no_binding_invented",
        description="Агент не вигадує тип кріплення правил якщо не вказано",
        category="hallucination",
        input="Правила 8 сторінок, A5.",
        expected_output=(
            "JSON містить rulebook.pages=8 і rulebook.size_mm=[148,210]. "
            "rulebook.binding = null — клієнт не сказав 'на скобу' чи 'фальцювання'. "
            "Агент запитує тип кріплення."
        ),
        context=[
            "binding не вказано — не вигадувати.",
            "A5=148×210 мм — коректно витягнути. pages=8 — коректно. binding=null.",
        ],
    ),
    DeepEvalScenario(
        id="hal2_no_construction_invented",
        description="Агент не вигадує конструктив коробки",
        category="hallucination",
        input="Коробка 300×200×60 мм, тираж 500.",
        expected_output=(
            "JSON містить rigid_box.size_mm=[300,200,60] і quantity=500. "
            "rigid_box.construction = null — клієнт не сказав 'кришка і дно' чи інше. "
            "Агент запитує конструктив."
        ),
        context=[
            "Конструктив коробки (lid_and_base / base_and_sleeve / self_assembly) не вказано.",
            "Не встановлювати значення без підтвердження клієнта.",
        ],
    ),
    DeepEvalScenario(
        id="hal2_no_print_colors_invented",
        description="Агент не вигадує print_colors для карт",
        category="hallucination",
        input="Карти 63×88 мм, 300 gsm, матова ламінація.",
        expected_output=(
            "JSON містить card_deck.card_size_mm=[63,88], gsm=300, front_finish=matte_lamination. "
            "card_deck.print_colors = null — клієнт не назвав кількість фарб. "
            "Агент запитує колірність."
        ),
        context=[
            "print_colors не вказано (4+4, 4+0 тощо).",
            "Не записувати '4+4' за замовчуванням без підтвердження клієнта.",
            "print_colors є обов'язковим полем — агент МУСИТЬ запитати його у follow_up.",
        ],
        threshold=0.70,
    ),
    DeepEvalScenario(
        id="hal2_no_edge_finish_invented",
        description="Агент не вигадує edge_finish для ігрового поля",
        category="hallucination",
        input="Ігрове поле 420×297 мм, матова ламінація.",
        expected_output=(
            "JSON містить game_board.size_mm=[420,297] і lamination=matte. "
            "game_board.edge_finish = null — клієнт не сказав 'обклейка торців' чи 'кашероване'. "
            "Агент запитує тип торців."
        ),
        context=[
            "edge_finish: wrapped_edges (обклейка) або visible_board_edge (кашероване).",
            "Клієнт не вказав — запитати.",
        ],
    ),
    DeepEvalScenario(
        id="hal2_quantity_not_from_card_count",
        description="quantity береться з тиражу а не з кількості карт",
        category="hallucination",
        input="Тираж 500, колода 110 карт.",
        expected_output=(
            "client_requirements.quantity = 500 (тираж). "
            "card_deck.card_count = 110 (карт у колоді). "
            "quantity НЕ дорівнює 110 — це різні поля."
        ),
        context=[
            "quantity = кількість наборів/екземплярів гри = тираж.",
            "card_count = кількість карт в одній колоді.",
            "Ці числа не можна плутати.",
        ],
    ),
    DeepEvalScenario(
        id="hal2_no_uv_invented",
        description="Агент не додає uv_varnish=True якщо клієнт не згадував УФ",
        category="hallucination",
        input="Коробка 300×200×60, матова ламінація, тираж 700.",
        expected_output=(
            "JSON містить lamination=matte, size_mm=[300,200,60], quantity=700. "
            "uv_varnish = null або False — клієнт не згадував УФ-лак. "
            "НЕ встановлювати uv_varnish=True без підстав."
        ),
        context=[
            "УФ-лак (uv_varnish) — опційний спецефект.",
            "Якщо не згадано — null або запитати.",
        ],
    ),
    DeepEvalScenario(
        id="hal2_no_deadline_invented",
        description="Агент не вигадує дедлайн якщо клієнт не вказав",
        category="hallucination",
        input="Коробка для гри «Факел», тираж 1000, коробка і карти 80 шт.",
        expected_output=(
            "deadline_days = null — клієнт не вказував дедлайн. "
            "Агент запитує дедлайн у follow-up питанні."
        ),
        context=[
            "Дедлайн не вказано — не вигадувати конкретне число днів.",
            "Агент має запитати дедлайн серед загальних полів.",
        ],
    ),
]

# ---------------------------------------------------------------------------
# MULTI-TURN CONVERSATION QUALITY — extended batch
# ---------------------------------------------------------------------------

CONVO2_SCENARIOS: list[DeepEvalScenario] = [
    DeepEvalScenario(
        id="cv2_quantity_preserved_all_turns",
        description="Тираж зберігається протягом усієї розмови",
        category="convo",
        input="Карти 63×88 мм, 300 gsm, 4+4, матова ламінація.",
        history=[
            ("Гра «Прометей», тираж 1200, коробка, карти 90 шт.", "Деталі коробки?"),
            ("Коробка 350×250×70, кришка і дно, матова, 1.75 мм.", "Деталі карт?"),
        ],
        accumulated={
            "requirements": {"quantity": 1200, "product_name": "Прометей"},
            "components": [
                {
                    "id": "rigid_box", "type": "rigid_box", "name": "Прометей коробка",
                    "size_mm": [350, 250, 70], "construction": "lid_and_base",
                    "lamination": "matte", "board_thickness_mm": 1.75,
                },
                {"id": "card_deck", "type": "card_deck", "name": "Прометей карти", "card_count": 90},
            ],
        },
        expected_output=(
            "JSON зберігає quantity=1200 (з першого turn). "
            "card_deck оновлюється: card_size_mm=[63,88], gsm=300, print_colors=4+4, front_finish=matte_lamination. "
            "card_count=90 зберігається з попередніх turns. "
            "rigid_box поля не втрачаються."
        ),
        context=[
            "quantity=1200 встановлено в першому turn — зберегти.",
            "card_count=90 відомо з першого turn — не губити.",
        ],
        threshold=0.5,
    ),
    DeepEvalScenario(
        id="cv2_client_confirms_standard",
        description="Клієнт підтверджує запропонований стандарт — агент фіксує і рухається далі",
        category="convo",
        input="Так, 1.75 підходить.",
        history=[
            ("Коробка 300×200×60, кришка і дно.", "Яка товщина? Зазвичай 1.75 мм — підходить?"),
        ],
        accumulated={
            "requirements": {},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "коробка",
                 "size_mm": [300, 200, 60], "construction": "lid_and_base"},
            ],
        },
        expected_output=(
            "Агент фіксує board_thickness_mm=1.75 і рухається до наступного поля. "
            "Коротко підтверджує: 'Чудово, 1.75 мм зафіксовано.' "
            "Запитує наступне невідоме поле (ламінація, УФ, друк тощо)."
        ),
        context=[
            "Клієнт погодився на 1.75 мм.",
            "board_thickness_mm=1.75 фіксується. Далі — ламінація.",
        ],
        threshold=0.5,
    ),
    DeepEvalScenario(
        id="cv2_expert_fills_client_name_as_company",
        description="Експерт вводить назву компанії — client_name = контрагент",
        category="convo",
        ui_role="expert",
        input="Замовник — ТОВ «Ігроленд», гра «Простір», тираж 800.",
        history=[],
        accumulated={},
        expected_output=(
            "client_name = 'ТОВ «Ігроленд»' або 'Ігроленд' (назва компанії, не ім'я людини). "
            "product_name = 'Простір'. quantity = 800. "
            "Follow-up запитує: дедлайн, комплектуючі, додаткові елементи, деталі коробки."
        ),
        context=[
            "Роль: expert → поле client_name = контрагент (назва компанії або ФОП).",
            "Агент питає 'Контрагент (замовник)?' а не 'Як до вас звертатись?'.",
        ],
        threshold=0.5,
    ),
    DeepEvalScenario(
        id="cv2_no_re_ask_after_confirmation",
        description="Після підтвердження ламінації — агент не перепитує її знову",
        category="convo",
        input="Деталі правил: A5, 8 сторінок, на скобу.",
        history=[
            ("Гра «Пульс», тираж 500, коробка, карти 70 шт., правила.", "Загальні питання..."),
            ("Коробка 300×200×60, матова ламінація, 1.75 мм.", "Деталі карт?"),
            ("Карти 63×88, 300 gsm, 4+4, матова ламінація.", "Деталі правил?"),
        ],
        accumulated={
            "requirements": {"quantity": 500, "product_name": "Пульс"},
            "components": [
                {
                    "id": "rigid_box", "type": "rigid_box", "name": "Пульс коробка",
                    "size_mm": [300, 200, 60], "lamination": "matte", "board_thickness_mm": 1.75,
                },
                {
                    "id": "card_deck", "type": "card_deck", "name": "Пульс карти",
                    "card_count": 70, "card_size_mm": [63, 88], "gsm": 300,
                    "print_colors": "4+4", "front_finish": "matte_lamination",
                    "back_finish": "matte_lamination", "shrink_wrap": False,
                },
                {"id": "rulebook", "type": "rulebook_thin", "name": "Правила гри"},
            ],
        },
        expected_output=(
            "Агент витягує: rulebook.size_mm=[148,210], rulebook.pages=8, rulebook.binding=saddle_stitch. "
            "НЕ перепитує ламінацію коробки чи карт. "
            "НЕ перепитує тираж. "
            "Перевіряє чи всі поля заповнені і якщо так — оголошує завершення."
        ),
        context=[
            "Вже відомо: rigid_box (size, lamination, thickness), card_deck (всі деталі).",
            "Лишилось: rulebook деталі. Після їх отримання — завершення.",
        ],
        threshold=0.5,
    ),
    DeepEvalScenario(
        id="cv2_handles_ambiguous_game_component_choice",
        description="Клієнт відповідає двозначно на каталог — агент уточнює конкретну позицію",
        category="convo",
        input="Жетони.",
        history=[
            ("Гра «Форпост», тираж 400, є комплектуючі.", "Ось каталог: ... Жетони картонні — 28 грн/набір, Монети пластикові — 24 грн/набір..."),
        ],
        accumulated={
            "requirements": {
                "quantity": 400, "has_game_components": True, "customer_provides_components": False,
            },
            "components": [{"id": "rigid_box", "type": "rigid_box", "name": "Форпост коробка"}],
        },
        expected_output=(
            "Агент НЕ фіксує вибір як завершений — 'жетони' може означати і 'жетони картонні' і 'монети пластикові'. "
            "Перелічує обидві позиції з повними назвами з каталогу і просить уточнити: "
            "'Маєте на увазі «Жетони картонні» чи «Монети пластикові»? Вкажіть назву і кількість.'"
        ),
        context=[
            "Каталог містить: 'Жетони картонні' і 'Монети пластикові' — різні позиції.",
            "Відповідь 'жетони' — двозначна. Потрібне уточнення.",
        ],
        threshold=0.5,
    ),
    DeepEvalScenario(
        id="cv2_game_board_standalone_no_box_question",
        description="Якщо замовлено лише поле — агент не питає про коробку",
        category="convo",
        input="Деталі: поле 594×420 мм, один згин, матова, кашероване.",
        history=[
            ("Потрібне лише ігрове поле для гри «Планета», тираж 300.", "Деталі поля?"),
        ],
        accumulated={
            "requirements": {"quantity": 300, "product_name": "Планета"},
            "components": [
                {"id": "game_board", "type": "game_board", "name": "Ігрове поле"},
            ],
        },
        expected_output=(
            "Агент витягує деталі поля: size_mm=[594,420], lamination=matte, edge_finish=visible_board_edge. "
            "НЕ питає 'А чи є коробка?' або 'Чи є карти?' — клієнт сказав 'лише поле'. "
            "Запитує лише відсутні поля game_board (board_thickness_mm, print_sides, fold_description якщо не зрозуміло)."
        ),
        context=[
            "Клієнт замовив лише ігрове поле. rigid_box не потрібна.",
            "Не питати про компоненти яких клієнт не згадував.",
        ],
        threshold=0.5,
    ),
]

# ---------------------------------------------------------------------------
# ALL DeepEval scenarios
# ---------------------------------------------------------------------------

ALL_DEEPEVAL_SCENARIOS: list[DeepEvalScenario] = (
    FOLLOWUP_SCENARIOS
    + FOLLOWUP2_SCENARIOS
    + GUARDRAIL_SCENARIOS
    + GUARDRAIL2_SCENARIOS
    + HALLUCINATION_SCENARIOS
    + HALLUCINATION2_SCENARIOS
    + CONVO_SCENARIOS
    + CONVO2_SCENARIOS
)

DEEPEVAL_SCENARIO_IDS = [s.id for s in ALL_DEEPEVAL_SCENARIOS]
