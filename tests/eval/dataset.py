"""Evaluation dataset for the conversational requirements-extraction agent.

Each ``Scenario`` represents one evaluation unit:
- ``id``          — unique slug used in pytest parametrize / reports
- ``description`` — what aspect is being tested (shown in failure messages)
- ``history``     — list of (human_text, assistant_text) turns that happened
                    *before* the turn under test; simulates accumulated state
- ``accumulated`` — {requirements, components} already stored in ProductionState
                    after the history turns (mirrors what _merge_partial_data built)
- ``input``       — the current human message being evaluated
- ``expected``    — dict with any subset of fields to assert:
                      • ``requirements``  – flat dict checked against client_requirements
                      • ``components``    – {component_id: {field: value}} dict
                      • ``status``        – "complete" | "incomplete"
                      • ``no_hallucination`` – list of field keys that must NOT be set
                      • ``follow_up_contains`` – substring that follow_up_question must contain

Categories (prefixed in ``id``):
  ext_   – basic field extraction (single message)
  conf_  – confusion tests (numbers / units that look similar)
  multi_ – multi-turn conversation (accumulated state matters)
  guard_ – guardrail / off-topic handling
  edge_  – edge cases (ambiguous phrasing, typos, missing info)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Scenario:
    id: str
    description: str
    input: str
    expected: dict[str, Any]
    history: list[tuple[str, str]] = field(default_factory=list)
    accumulated: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# A – BASIC EXTRACTION (single message, no history)
# ---------------------------------------------------------------------------

EXT_SCENARIOS: list[Scenario] = [
    # --- quantity vs card_count confusion (main concern) ---
    Scenario(
        id="ext_quantity_cards_1000_110",
        description="тираж 1000, 110 карт — не плутати quantity з card_count",
        input="Потрібна преміальна коробка для настільної гри, тираж 1000 шт., з колодою 110 карт і правилами.",
        expected={
            "requirements": {"quantity": 1000},
            "components": {"card_deck": {"card_count": 110}},
            "no_hallucination": [],
        },
    ),
    Scenario(
        id="ext_quantity_cards_500_54",
        description="тираж 500, колода 54 карти",
        input="Замовлення: 500 коробок для гри «Піраміда», колода 54 карти, правила.",
        expected={
            "requirements": {"quantity": 500},
            "components": {"card_deck": {"card_count": 54}},
        },
    ),
    Scenario(
        id="ext_quantity_cards_2000_78",
        description="тираж 2000, 78 карт у колоді",
        input="замовлення на 2000 екземплярів, 78 карт у колоді та правила гри.",
        expected={
            "requirements": {"quantity": 2000},
            "components": {"card_deck": {"card_count": 78}},
        },
    ),
    Scenario(
        id="ext_quantity_cards_300_110",
        description="тираж 300 + «карти 110 штук» — ambiguous «штук»",
        input="тираж 300, карти 110 штук і правила.",
        expected={
            "requirements": {"quantity": 300},
            "components": {"card_deck": {"card_count": 110}},
        },
    ),
    Scenario(
        id="ext_quantity_cards_750_36",
        description="тираж 750, 36 карт (маленька колода)",
        input="потрібно 750 наборів гри, колода 36 карт, коробка і правила.",
        expected={
            "requirements": {"quantity": 750},
            "components": {"card_deck": {"card_count": 36}},
        },
    ),
    Scenario(
        id="ext_quantity_cards_1500_200",
        description="тираж 1500, велика колода 200 карт",
        input="тираж 1500 шт., велика колода 200 карт і коробка.",
        expected={
            "requirements": {"quantity": 1500},
            "components": {"card_deck": {"card_count": 200}},
        },
    ),
    # --- product name extraction ---
    Scenario(
        id="ext_product_name",
        description="назва гри витягується з першого повідомлення",
        input="Хочу замовити коробку та карти для гри «Замок Дракона», тираж 600.",
        expected={
            "requirements": {"product_name": "Замок Дракона", "quantity": 600},
        },
    ),
    # --- premium flag ---
    Scenario(
        id="ext_premium_finish",
        description="«преміальна» → premium_finish=True",
        input="Потрібна преміальна коробка для гри Аркан, тираж 400, колода 60 карт.",
        expected={
            "requirements": {"premium_finish": True, "quantity": 400},
        },
    ),
    # --- components detection ---
    Scenario(
        id="ext_has_no_components",
        description="«без комплектуючих» → has_game_components=False",
        input="Коробка і карти без жодних комплектуючих, тираж 800.",
        expected={
            "requirements": {"has_game_components": False},
        },
    ),
    Scenario(
        id="ext_customer_provides_components",
        description="«кубики ми маємо свої» → customer_provides_components=True",
        input="тираж 1000, коробка і карти. Кубики у нас свої, надамо окремо.",
        expected={
            "requirements": {
                "has_game_components": True,
                "customer_provides_components": True,
            },
        },
    ),
    Scenario(
        id="ext_has_game_board",
        description="«ігрове поле» → has_additional_elements=True, game_board у components",
        input="Потрібна коробка, карти 80 штук і ігрове поле, тираж 500.",
        expected={
            "requirements": {"has_additional_elements": True},
            "components": {"game_board": {}},
        },
    ),
    Scenario(
        id="ext_has_info_leaflet",
        description="«інформаційна листівка» → info_leaflet у components",
        input="Замовлення: коробка, карти 100 шт., правила, інформаційна листівка. Тираж 1200.",
        expected={
            "requirements": {"has_additional_elements": True},
            "components": {"info_leaflet": {}},
        },
    ),
]

# ---------------------------------------------------------------------------
# B – CONFUSION / DIMENSION TESTS
# ---------------------------------------------------------------------------

CONF_SCENARIOS: list[Scenario] = [
    # --- box size dimensions ---
    Scenario(
        id="conf_box_size_vs_quantity",
        description="розмір коробки 300×200×60 не плутати з тиражем 1000",
        input="коробка 300×200×60 мм, тираж 1000 шт.",
        expected={
            "requirements": {"quantity": 1000},
            "components": {"rigid_box": {"size_mm": [300, 200, 60]}},
        },
    ),
    Scenario(
        id="conf_box_size_big",
        description="велика коробка 400×300×80 мм + тираж 500",
        input="Потрібна коробка 400×300×80 мм, тираж 500 штук, картонна основа.",
        expected={
            "requirements": {"quantity": 500},
            "components": {"rigid_box": {"size_mm": [400, 300, 80]}},
        },
    ),
    Scenario(
        id="conf_card_size_vs_card_count",
        description="розмір карти 63×88 мм не плутати з кількістю карт 120",
        input="Карти розміром 63 на 88 мм, 120 карт у колоді, тираж 1000.",
        expected={
            "requirements": {"quantity": 1000},
            "components": {"card_deck": {"card_count": 120, "card_size_mm": [63, 88]}},
        },
    ),
    Scenario(
        id="conf_card_size_tarot",
        description="Tarot-формат 70×120 мм, 78 карт, тираж 300",
        input="Карти Таро: розмір 70×120 мм, 78 карт, тираж 300 екземплярів.",
        expected={
            "requirements": {"quantity": 300},
            "components": {"card_deck": {"card_count": 78, "card_size_mm": [70, 120]}},
        },
    ),
    Scenario(
        id="conf_rulebook_pages_vs_size",
        description="правила A5 (148×210 мм), 16 сторінок — не плутати pages з мм",
        input="Правила формату A5, 16 сторінок, на скобу.",
        expected={
            "components": {
                "rulebook": {
                    "size_mm": [148, 210],
                    "pages": 16,
                    "binding": "saddle_stitch",
                }
            },
        },
    ),
    Scenario(
        id="conf_rulebook_a4_8pages",
        description="правила A4, 8 сторінок — два різних числа",
        input="Інструкція: формат A4, 8 сторінок, фальцювання.",
        expected={
            "components": {
                "rulebook": {
                    "size_mm": [210, 297],
                    "pages": 8,
                    "binding": "folding",
                }
            },
        },
    ),
    Scenario(
        id="conf_board_thickness_vs_size",
        description="товщина картону 1.75 мм не плутати з розміром 420×297 мм",
        input="Ігрове поле 420×297 мм, складається вдвічі, палітурний картон 1.75 мм, матова ламінація.",
        expected={
            "components": {
                "game_board": {
                    "size_mm": [420, 297],
                    "board_thickness_mm": 1.75,
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="conf_board_thickness_2mm",
        description="товщина 2.0 мм, поле 600×600 мм",
        input="Поле розміром 600×600 мм, товщина основи 2 мм, з обклейкою торців.",
        expected={
            "components": {
                "game_board": {
                    "size_mm": [600, 600],
                    "board_thickness_mm": 2.0,
                    "edge_finish": "wrapped_edges",
                }
            },
        },
    ),
    Scenario(
        id="conf_gsm_vs_card_count",
        description="граматура 300 gsm не плутати з кількістю карт 110",
        input="Карти 110 штук, граматура 300 gsm, двосторонній друк 4+4.",
        expected={
            "components": {
                "card_deck": {
                    "card_count": 110,
                    "gsm": 300,
                    "print_colors": "4+4",
                }
            },
        },
    ),
    Scenario(
        id="conf_gsm_350_cards_54",
        description="350 gsm vs 54 карти — два числа поруч",
        input="Колода 54 карти, матеріал 350 gsm, матова ламінація.",
        expected={
            "components": {
                "card_deck": {
                    "card_count": 54,
                    "gsm": 350,
                    "front_finish": "matte_lamination",
                }
            },
        },
    ),
    Scenario(
        id="conf_leaflet_size_vs_crease",
        description="листівка 100×150 мм, з біговкою — розмір не плутати",
        input="Інформаційна листівка 100×150 мм, друк 4+4, є біговка.",
        expected={
            "components": {
                "info_leaflet": {
                    "size_mm": [100, 150],
                    "print_colors": "4+4",
                    "has_crease": True,
                }
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# C – MULTI-TURN CONVERSATIONS
# ---------------------------------------------------------------------------

MULTI_SCENARIOS: list[Scenario] = [
    # --- Scenario 1: стандартна розмова коробка+карти (3 turns) ---
    Scenario(
        id="multi_basic_turn2_box_details",
        description="Turn 2: клієнт відповідає на питання про коробку — зберігаємо quantity з turn 1",
        history=[
            (
                "Потрібна коробка для гри «Нова Ера», тираж 800, колода 60 карт і правила.",
                '{"status":"incomplete","client_requirements":{"quantity":800,"product_name":"Нова Ера"},'
                '"product_components":[{"id":"rigid_box","type":"rigid_box","name":"Нова Ера коробка"},'
                '{"id":"card_deck","type":"card_deck","name":"Нова Ера карти","card_count":60},'
                '{"id":"rulebook","type":"rulebook_thin","name":"Правила гри"}],'
                '"follow_up_question":"Уточніть деталі коробки..."}',
            ),
        ],
        accumulated={
            "requirements": {"quantity": 800, "product_name": "Нова Ера"},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Нова Ера коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Нова Ера карти", "card_count": 60},
                {"id": "rulebook", "type": "rulebook_thin", "name": "Правила гри"},
            ],
        },
        input="Розмір коробки 280×190×55 мм, кришка і дно, матова ламінація, палітурний картон 1.75 мм.",
        expected={
            "requirements": {"quantity": 800},
            "components": {
                "rigid_box": {
                    "size_mm": [280, 190, 55],
                    "construction": "lid_and_base",
                    "lamination": "matte",
                    "board_thickness_mm": 1.75,
                },
                "card_deck": {"card_count": 60},
            },
        },
    ),
    Scenario(
        id="multi_basic_turn3_cards_details",
        description="Turn 3: деталі карт — quantity і card_count з попередніх turns не губляться",
        history=[
            (
                "Гра «Сонячний Шлях», тираж 1200, колода 90 карт, коробка, правила.",
                "Зафіксував. Уточніть розмір та конструктив коробки.",
            ),
            (
                "Коробка 350×250×70 мм, кришка і дно, матова ламінація, 1.75 мм.",
                "Чудово. Тепер деталі карт?",
            ),
        ],
        accumulated={
            "requirements": {"quantity": 1200, "product_name": "Сонячний Шлях"},
            "components": [
                {
                    "id": "rigid_box",
                    "type": "rigid_box",
                    "name": "Сонячний Шлях коробка",
                    "size_mm": [350, 250, 70],
                    "construction": "lid_and_base",
                    "lamination": "matte",
                    "board_thickness_mm": 1.75,
                },
                {"id": "card_deck", "type": "card_deck", "name": "Сонячний Шлях карти", "card_count": 90},
                {"id": "rulebook", "type": "rulebook_thin", "name": "Правила гри"},
            ],
        },
        input="Карти 63×88 мм, 300 gsm, друк 4+4, матова ламінація з обох сторін.",
        expected={
            "requirements": {"quantity": 1200},
            "components": {
                "card_deck": {
                    "card_count": 90,
                    "card_size_mm": [63, 88],
                    "gsm": 300,
                    "print_colors": "4+4",
                    "front_finish": "matte_lamination",
                    "back_finish": "matte_lamination",
                },
            },
        },
    ),
    Scenario(
        id="multi_rulebook_turn4",
        description="Turn 4: деталі правил — всі попередні дані зберігаються",
        history=[
            ("Гра «Хаос», тираж 500, 120 карт, коробка, правила.", "Деталі коробки?"),
            ("Коробка 300×200×60 мм, кришка і дно, мат.", "Деталі карт?"),
            ("Карти 63×88, 300 gsm, 4+4, мат ламінація.", "Деталі правил?"),
        ],
        accumulated={
            "requirements": {"quantity": 500, "product_name": "Хаос"},
            "components": [
                {
                    "id": "rigid_box",
                    "type": "rigid_box",
                    "name": "Хаос коробка",
                    "size_mm": [300, 200, 60],
                    "construction": "lid_and_base",
                    "lamination": "matte",
                },
                {
                    "id": "card_deck",
                    "type": "card_deck",
                    "name": "Хаос карти",
                    "card_count": 120,
                    "card_size_mm": [63, 88],
                    "gsm": 300,
                    "print_colors": "4+4",
                    "front_finish": "matte_lamination",
                    "back_finish": "matte_lamination",
                },
                {"id": "rulebook", "type": "rulebook_thin", "name": "Правила гри"},
            ],
        },
        input="Правила A5, 8 сторінок, на скобу.",
        expected={
            "requirements": {"quantity": 500},
            "components": {
                "card_deck": {"card_count": 120},
                "rulebook": {
                    "size_mm": [148, 210],
                    "pages": 8,
                    "binding": "saddle_stitch",
                },
            },
        },
    ),
    Scenario(
        id="multi_no_re_ask",
        description="Агент НЕ перепитує вже відоме — тираж 800 вже є в accumulated",
        history=[
            (
                "Гра «Атлас», тираж 800, коробка, карти 100 шт.",
                "Чудово. Уточніть деталі коробки.",
            ),
        ],
        accumulated={
            "requirements": {"quantity": 800, "product_name": "Атлас"},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Атлас коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Атлас карти", "card_count": 100},
            ],
        },
        input="Коробка 320×220×65, самозбірна, матова ламінація.",
        expected={
            "requirements": {"quantity": 800},
            "components": {
                "rigid_box": {
                    "size_mm": [320, 220, 65],
                    "construction": "self_assembly",
                    "lamination": "matte",
                },
                "card_deck": {"card_count": 100},
            },
            "no_hallucination": [],
        },
    ),
    Scenario(
        id="multi_deadline_added_midway",
        description="Дедлайн вказується в середині розмови і зберігається",
        history=[
            ("Гра «Вектор», тираж 1000, коробка, карти 80 шт.", "Деталі коробки?"),
        ],
        accumulated={
            "requirements": {"quantity": 1000, "product_name": "Вектор"},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Вектор коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Вектор карти", "card_count": 80},
            ],
        },
        input="Дедлайн 30 днів. Коробка 300×200×60, кришка і дно, мат.",
        expected={
            "requirements": {"quantity": 1000, "deadline_days": 30},
            "components": {
                "rigid_box": {
                    "size_mm": [300, 200, 60],
                    "construction": "lid_and_base",
                    "lamination": "matte",
                },
            },
        },
    ),
    Scenario(
        id="multi_game_board_added",
        description="Ігрове поле додається в середині розмови",
        history=[
            ("Гра «Карта Світу», тираж 600, коробка, карти 50 шт.", "Чи є ігрове поле?"),
        ],
        accumulated={
            "requirements": {"quantity": 600, "product_name": "Карта Світу"},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Карта Світу коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Карта Світу карти", "card_count": 50},
            ],
        },
        input="Так, є ігрове поле 420×297 мм, складається вдвічі, матова ламінація.",
        expected={
            "requirements": {"has_additional_elements": True},
            "components": {
                "game_board": {
                    "size_mm": [420, 297],
                    "lamination": "matte",
                },
            },
        },
    ),
    Scenario(
        id="multi_components_customer_provides",
        description="В середині розмови клієнт каже що комплектуючі власні",
        history=[
            ("Гра «Місто», тираж 700, коробка, карти 90 шт.", "Чи є комплектуючі?"),
        ],
        accumulated={
            "requirements": {"quantity": 700},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Місто коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Місто карти", "card_count": 90},
            ],
        },
        input="Так, кубики і фішки — у нас є свої, надамо окремо.",
        expected={
            "requirements": {
                "has_game_components": True,
                "customer_provides_components": True,
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# D – GUARDRAIL TESTS
# ---------------------------------------------------------------------------

GUARD_SCENARIOS: list[Scenario] = [
    Scenario(
        id="guard_off_topic_tshirt",
        description="Запит на футболки — за межами профілю, агент ввічливо відмовляє",
        input="Хочу замовити 500 футболок з логотипом нашої компанії.",
        expected={
            "status": "incomplete",
            "follow_up_contains": "настільн",
        },
    ),
    Scenario(
        id="guard_off_topic_banner",
        description="Банер — за межами профілю",
        input="Потрібен банер 2×3 метри для виставки.",
        expected={
            "status": "incomplete",
            "follow_up_contains": "упаков",
        },
    ),
    Scenario(
        id="guard_off_topic_general_printing",
        description="Загальна поліграфія без прив'язки до гри",
        input="Хочу замовити бланки для офісу та рекламні листівки.",
        expected={
            "status": "incomplete",
            "follow_up_contains": "настільн",
        },
    ),
    Scenario(
        id="guard_no_components_explicit",
        description="«комплектуючих не треба» → has_game_components=False, не питати знову",
        input="коробка і карти 60 штук, тираж 400. Комплектуючих не треба.",
        expected={
            "requirements": {"has_game_components": False, "quantity": 400},
            "components": {"card_deck": {"card_count": 60}},
        },
    ),
]

# ---------------------------------------------------------------------------
# E – EDGE CASES
# ---------------------------------------------------------------------------

EDGE_SCENARIOS: list[Scenario] = [
    Scenario(
        id="edge_only_greeting",
        description="Лише привітання — агент не витягує жодних полів",
        input="Привіт",
        expected={
            "status": "incomplete",
            "requirements": {},
        },
    ),
    Scenario(
        id="edge_quantity_written_words",
        description="тираж словами «тисяча» — може бути не розпізнано",
        input="Хочу тисячу коробок для гри «Зорі», карти 80 штук.",
        expected={
            "requirements": {"quantity": 1000},
            "components": {"card_deck": {"card_count": 80}},
        },
    ),
    Scenario(
        id="edge_quantity_with_spaces",
        description="«1 000 шт» з пробілом у числі",
        input="Тираж 1 000 шт., колода 110 карт, коробка і правила.",
        expected={
            "requirements": {"quantity": 1000},
            "components": {"card_deck": {"card_count": 110}},
        },
    ),
    Scenario(
        id="edge_implicit_premium",
        description="«виглядало солідно, не дешево» → premium_finish=True (намір)",
        input="Хочу щоб коробка виглядала солідно і преміально, тираж 300.",
        expected={
            "requirements": {"premium_finish": True},
        },
    ),
    Scenario(
        id="edge_print_colors_one_side",
        description="«лише лице» → print_colors N+0",
        input="Карти 63×88, 300 gsm, друк лише з лицьової сторони повноколірний, тираж 500.",
        expected={
            "components": {"card_deck": {"print_colors": "4+0"}},
        },
    ),
    Scenario(
        id="edge_print_colors_pantone",
        description="«з Pantone» → print_colors 5+0 або 6+0",
        input="Карти з Pantone на лицьовій стороні, тираж 800.",
        expected={
            "components": {"card_deck": {}},
            "follow_up_contains": "Pantone",
        },
    ),
    Scenario(
        id="edge_uv_varnish_explicit",
        description="«УФ-лак на логотипі» → uv_varnish=True, uv_varnish_elements заповнено",
        input="Коробка 300×200×60, УФ-лак на логотипі на кришці, матова ламінація.",
        expected={
            "components": {
                "rigid_box": {
                    "uv_varnish": True,
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="edge_board_casherovane",
        description="«кашероване» поле → edge_finish=visible_board_edge",
        input="Ігрове поле 500×500 мм, кашероване, матова ламінація.",
        expected={
            "components": {
                "game_board": {
                    "edge_finish": "visible_board_edge",
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="edge_shrink_wrap_box",
        description="«термопакування» коробки → shrink_wrap=True",
        input="Коробка 300×200×60, матова, з термопакуванням.",
        expected={
            "components": {
                "rigid_box": {
                    "shrink_wrap": True,
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="edge_multiple_numbers_close",
        description="декілька чисел поруч: тираж 2000, поле 840×594, товщина 1.75, карти 150",
        input="Тираж 2000, ігрове поле 840×594 мм, товщина картону 1.75 мм, карти 150 штук розміром 63×88 мм.",
        expected={
            "requirements": {"quantity": 2000},
            "components": {
                "card_deck": {"card_count": 150, "card_size_mm": [63, 88]},
                "game_board": {"size_mm": [840, 594], "board_thickness_mm": 1.75},
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# F – EXTENDED EXTRACTION (more field/lamination/print/construction variants)
# ---------------------------------------------------------------------------

EXT2_SCENARIOS: list[Scenario] = [
    # --- lamination variants ---
    Scenario(
        id="ext2_gloss_lamination_box",
        description="«глянцева ламінація» коробки → lamination=gloss",
        input="Коробка 280×180×50 мм, кришка і дно, глянцева ламінація, тираж 600.",
        expected={
            "requirements": {"quantity": 600},
            "components": {
                "rigid_box": {
                    "size_mm": [280, 180, 50],
                    "construction": "lid_and_base",
                    "lamination": "gloss",
                }
            },
        },
    ),
    Scenario(
        id="ext2_gloss_lamination_cards",
        description="«глянцева ламінація» карт → front_finish=gloss_lamination",
        input="Карти 63×88 мм, 300 gsm, друк 4+4, глянцева ламінація з обох сторін, тираж 800.",
        expected={
            "requirements": {"quantity": 800},
            "components": {
                "card_deck": {
                    "card_count": None,
                    "card_size_mm": [63, 88],
                    "gsm": 300,
                    "print_colors": "4+4",
                    "front_finish": "gloss_lamination",
                    "back_finish": "gloss_lamination",
                }
            },
        },
    ),
    # --- construction variants ---
    Scenario(
        id="ext2_construction_sleeve",
        description="«дно і рукав» → construction=base_and_sleeve",
        input="Коробка 320×220×70 мм, дно і рукав, матова ламінація, тираж 400.",
        expected={
            "requirements": {"quantity": 400},
            "components": {
                "rigid_box": {
                    "size_mm": [320, 220, 70],
                    "construction": "base_and_sleeve",
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="ext2_construction_self_assembly",
        description="«самозбірна» коробка",
        input="Самозбірна коробка 250×180×45 мм, палітурний картон 1.5 мм, мат, тираж 1000.",
        expected={
            "requirements": {"quantity": 1000},
            "components": {
                "rigid_box": {
                    "construction": "self_assembly",
                    "board_thickness_mm": 1.5,
                    "lamination": "matte",
                }
            },
        },
    ),
    # --- print sides ---
    Scenario(
        id="ext2_print_inside_outside",
        description="«друк зовні та всередині» → print_sides=outside_and_inside",
        input="Коробка 300×200×60 мм, друк зовні та всередині, матова ламінація, тираж 500.",
        expected={
            "components": {
                "rigid_box": {
                    "print_sides": "outside_and_inside",
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="ext2_print_outside_only",
        description="«лише зовні» → print_sides=outside_only",
        input="Коробка 280×200×55 мм, друк тільки зовні, тираж 700.",
        expected={
            "components": {
                "rigid_box": {"print_sides": "outside_only"}
            },
        },
    ),
    # --- material variants ---
    Scenario(
        id="ext2_material_corrugated",
        description="«гофра» як основа коробки",
        input="Коробка на гофрі, 400×300×80 мм, матова ламінація, тираж 200.",
        expected={
            "components": {
                "rigid_box": {
                    "material": "corrugated",
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="ext2_material_bookbinding",
        description="«палітурний картон» як основа коробки",
        input="Коробка на палітурному картоні 2.0 мм, 350×250×70 мм, тираж 300.",
        expected={
            "components": {
                "rigid_box": {
                    "material": "bookbinding_board",
                    "board_thickness_mm": 2.0,
                }
            },
        },
    ),
    # --- UV varnish ---
    Scenario(
        id="ext2_uv_varnish_full_coverage",
        description="«УФ-лак по всій площі» → uv_varnish=True",
        input="Коробка 300×200×60 мм, матова ламінація, УФ-лак по всій поверхні, тираж 900.",
        expected={
            "components": {
                "rigid_box": {
                    "uv_varnish": True,
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="ext2_no_uv_varnish",
        description="«без УФ-лаку» → uv_varnish=False",
        input="Коробка 280×190×55, матова ламінація, без УФ-лаку, тираж 600.",
        expected={
            "components": {
                "rigid_box": {
                    "uv_varnish": False,
                    "lamination": "matte",
                }
            },
        },
    ),
    # --- shrink wrap ---
    Scenario(
        id="ext2_shrink_wrap_cards",
        description="«термопакування карт» → card_deck.shrink_wrap=True",
        input="Карти 63×88, 300 gsm, 4+4, матова ламінація, термопакування карт, тираж 1000.",
        expected={
            "components": {
                "card_deck": {
                    "shrink_wrap": True,
                    "front_finish": "matte_lamination",
                }
            },
        },
    ),
    # --- deadline ---
    Scenario(
        id="ext2_deadline_days_explicit",
        description="«дедлайн 45 днів» → deadline_days=45",
        input="Гра «Нептун», тираж 500, дедлайн 45 днів, коробка і карти 72 штуки.",
        expected={
            "requirements": {
                "quantity": 500,
                "deadline_days": 45,
                "product_name": "Нептун",
            },
            "components": {"card_deck": {"card_count": 72}},
        },
    ),
    Scenario(
        id="ext2_deadline_date_format",
        description="«до 1 червня» → агент має зафіксувати дедлайн у якомусь форматі",
        input="Тираж 1000, коробка, карти 90 шт. Потрібно до 1 червня.",
        expected={
            "requirements": {"quantity": 1000},
            "components": {"card_deck": {"card_count": 90}},
        },
    ),
    # --- client name ---
    Scenario(
        id="ext2_client_name_extracted",
        description="Ім'я клієнта витягується з повідомлення",
        input="Мене звуть Олена. Хочу замовити коробку для гри «Дракон», тираж 300.",
        expected={
            "requirements": {
                "client_name": "Олена",
                "product_name": "Дракон",
                "quantity": 300,
            },
        },
    ),
    # --- print colors asymmetric ---
    Scenario(
        id="ext2_print_colors_asymmetric",
        description="«лице 4 кольори, зворот 1 колір» → print_colors=4+1 (асиметричний)",
        input="Карти: лице повноколірне 4+0, зворот однофарбовий 1+0, тираж 600.",
        expected={
            "components": {
                "card_deck": {"print_colors": "4+1"}
            },
        },
    ),
    # --- rulebook binding variants ---
    Scenario(
        id="ext2_rulebook_folding",
        description="«фальцювання» → binding=folding",
        input="Правила A4, 4 сторінки, фальцювання (один згин), тираж 800.",
        expected={
            "components": {
                "rulebook": {
                    "size_mm": [210, 297],
                    "pages": 4,
                    "binding": "folding",
                }
            },
        },
    ),
    Scenario(
        id="ext2_rulebook_saddle_stitch",
        description="«на скобу / скорбу» → binding=saddle_stitch",
        input="Правила: формат A5, 12 сторінок, скріплення на скобу.",
        expected={
            "components": {
                "rulebook": {
                    "pages": 12,
                    "binding": "saddle_stitch",
                }
            },
        },
    ),
    # --- game board wrapped edges ---
    Scenario(
        id="ext2_game_board_wrapped_edges",
        description="«обклейка торців» → edge_finish=wrapped_edges",
        input="Ігрове поле 594×420 мм, з обклейкою торців, матова ламінація.",
        expected={
            "components": {
                "game_board": {
                    "size_mm": [594, 420],
                    "edge_finish": "wrapped_edges",
                    "lamination": "matte",
                }
            },
        },
    ),
    # --- game board fold ---
    Scenario(
        id="ext2_game_board_fold_twice",
        description="поле складається в А5 (два згини) — розмір і fold_description витягуються",
        history=[
            ("Гра «Космос», тираж 500, коробка, карти 80 шт., є ігрове поле.", "Деталі поля?"),
        ],
        accumulated={
            "requirements": {"quantity": 500, "product_name": "Космос", "has_additional_elements": True},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Космос коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Космос карти", "card_count": 80},
                {"id": "game_board", "type": "game_board", "name": "Ігрове поле"},
            ],
        },
        input="Ігрове поле 840×594 мм, складається в А5 (два згини), палітурний картон.",
        expected={
            "requirements": {"quantity": 500},
            "components": {
                "game_board": {
                    "size_mm": [840, 594],
                }
            },
        },
    ),
    # --- info leaflet no crease ---
    Scenario(
        id="ext2_info_leaflet_no_crease",
        description="«без біговки» → has_crease=False",
        input="Листівка 148×210 мм, друк 4+4, без біговки.",
        expected={
            "components": {
                "info_leaflet": {
                    "size_mm": [148, 210],
                    "print_colors": "4+4",
                    "has_crease": False,
                }
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# G – EXTENDED MULTI-TURN (complete flows + expert role)
# ---------------------------------------------------------------------------

MULTI2_SCENARIOS: list[Scenario] = [
    # --- повна розмова до status=complete ---
    Scenario(
        id="multi2_complete_flow_final_turn",
        description="Фінальний turn повної розмови → status=complete після заповнення всіх полів",
        history=[
            ("Гра «Феникс», тираж 1000, коробка 300×200×60, карти 90 шт., правила.", "Деталі коробки?"),
            ("Кришка і дно, мат, 1.75 мм, зовні.", "Деталі карт?"),
            ("63×88, 300 gsm, 4+4, мат ламінація.", "Деталі правил?"),
        ],
        accumulated={
            "requirements": {
                "quantity": 1000,
                "product_name": "Феникс",
                "has_game_components": False,
                "has_additional_elements": False,
                "deadline_days": 30,
                "client_name": "Максим",
                "premium_finish": False,
            },
            "components": [
                {
                    "id": "rigid_box",
                    "type": "rigid_box",
                    "name": "Феникс коробка",
                    "size_mm": [300, 200, 60],
                    "quantity": 1000,
                    "construction": "lid_and_base",
                    "lamination": "matte",
                    "board_thickness_mm": 1.75,
                    "print_sides": "outside_only",
                    "uv_varnish": False,
                    "shrink_wrap": False,
                },
                {
                    "id": "card_deck",
                    "type": "card_deck",
                    "name": "Феникс карти",
                    "card_count": 90,
                    "quantity": 1000,
                    "card_size_mm": [63, 88],
                    "gsm": 300,
                    "print_colors": "4+4",
                    "front_finish": "matte_lamination",
                    "back_finish": "matte_lamination",
                    "shrink_wrap": False,
                },
                {"id": "rulebook", "type": "rulebook_thin", "name": "Правила гри"},
            ],
        },
        input="Правила A5, 8 сторінок, на скобу.",
        expected={
            "requirements": {"quantity": 1000},
            "components": {
                "rulebook": {
                    "size_mm": [148, 210],
                    "pages": 8,
                    "binding": "saddle_stitch",
                },
            },
        },
    ),
    # --- expert role: client_name = контрагент ---
    Scenario(
        id="multi2_expert_role_contragent",
        description="Замовлення з назвою компанії — витягуємо назву гри і тираж",
        history=[],
        accumulated={},
        input="Потрібна коробка для гри «Лабіринт» від ТОВ «Ігровий Світ», тираж 2000, карти 60 шт.",
        expected={
            "requirements": {
                "quantity": 2000,
                "product_name": "Лабіринт",
            },
        },
    ),
    # --- поступове уточнення комплектуючих ---
    Scenario(
        id="multi2_components_catalog_then_choice",
        description="Після показу каталогу клієнт обирає конкретну позицію",
        history=[
            ("Гра «Зодіак», тираж 500, коробка, карти 100 шт. Потрібні кубики.", "Ось каталог: ..."),
        ],
        accumulated={
            "requirements": {
                "quantity": 500,
                "has_game_components": True,
                "customer_provides_components": False,
            },
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Зодіак коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Зодіак карти", "card_count": 100},
            ],
        },
        input="Беру Кубики D6 білі — 1000 штук.",
        expected={
            "requirements": {
                "has_game_components": True,
                "quantity": 500,
                "customer_provides_components": False,
            },
        },
    ),
    # --- зміна деталей після першої відповіді (клієнт виправляє) ---
    Scenario(
        id="multi2_client_correction",
        description="Клієнт виправляє раніше сказане: тираж спочатку 500, потім 800",
        history=[
            ("Гра «Меч», тираж 500, коробка і карти 80 шт.", "Деталі коробки?"),
        ],
        accumulated={
            "requirements": {"quantity": 500, "product_name": "Меч"},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Меч коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Меч карти", "card_count": 80},
            ],
        },
        input="Вибачте, тираж виправте на 800. Коробка 300×200×60, кришка і дно, мат.",
        expected={
            "requirements": {"quantity": 800},
            "components": {
                "rigid_box": {
                    "size_mm": [300, 200, 60],
                    "construction": "lid_and_base",
                    "lamination": "matte",
                },
                "card_deck": {"card_count": 80},
            },
        },
    ),
    # --- додавання поля і листівки в середині ---
    Scenario(
        id="multi2_both_additional_elements",
        description="Клієнт підтверджує і поле, і листівку → обидва в components",
        history=[
            ("Гра «Острів», тираж 400, коробка, карти 45 шт.", "Чи є додаткові елементи?"),
        ],
        accumulated={
            "requirements": {"quantity": 400},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Острів коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Острів карти", "card_count": 45},
            ],
        },
        input="Так, є ігрове поле і інформаційна листівка.",
        expected={
            "requirements": {"has_additional_elements": True},
            "components": {
                "game_board": {},
                "info_leaflet": {},
            },
        },
    ),
    # --- клієнт дає всі деталі за один раз (довге перше повідомлення) ---
    Scenario(
        id="multi2_rich_first_message",
        description="Всі деталі в одному довгому першому повідомленні",
        history=[],
        accumulated={},
        input=(
            "Гра «Всесвіт», тираж 1500. Коробка 350×250×75 мм, кришка і дно, "
            "матова ламінація, палітурний картон 1.75 мм, друк зовні. "
            "Карти 63×88 мм, 110 карт, 300 gsm, 4+4, матова ламінація. "
            "Правила A5, 16 сторінок, на скобу. "
            "Без комплектуючих, без додаткових елементів."
        ),
        expected={
            "requirements": {
                "quantity": 1500,
                "product_name": "Всесвіт",
                "has_game_components": False,
                "has_additional_elements": False,
            },
            "components": {
                "rigid_box": {
                    "size_mm": [350, 250, 75],
                    "construction": "lid_and_base",
                    "lamination": "matte",
                    "board_thickness_mm": 1.75,
                },
                "card_deck": {
                    "card_count": 110,
                    "card_size_mm": [63, 88],
                    "gsm": 300,
                    "print_colors": "4+4",
                    "front_finish": "matte_lamination",
                },
                "rulebook": {
                    "pages": 16,
                    "binding": "saddle_stitch",
                },
            },
        },
    ),
    # --- поступове уточнення ігрового поля ---
    Scenario(
        id="multi2_game_board_full_details",
        description="Turn з деталями ігрового поля після підтвердження його наявності",
        history=[
            ("Гра «Марс», тираж 600, коробка, карти 70 шт., ігрове поле.", "Деталі поля?"),
        ],
        accumulated={
            "requirements": {
                "quantity": 600,
                "product_name": "Марс",
                "has_additional_elements": True,
            },
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Марс коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Марс карти", "card_count": 70},
                {"id": "game_board", "type": "game_board", "name": "Ігрове поле"},
            ],
        },
        input="Поле 594×420 мм, складається з A2 в A4 (два згини), 1.75 мм, лише лице 4+0, обклейка торців, матова.",
        expected={
            "requirements": {"quantity": 600},
            "components": {
                "game_board": {
                    "size_mm": [594, 420],
                    "board_thickness_mm": 1.75,
                    "print_colors": "4+0",
                    "edge_finish": "wrapped_edges",
                    "lamination": "matte",
                },
            },
        },
    ),
    # --- деталі листівки окремим turn ---
    Scenario(
        id="multi2_info_leaflet_full_details",
        description="Turn з повними деталями інформаційної листівки",
        history=[
            ("Гра «Кристал», тираж 700, коробка, карти 55 шт., листівка.", "Деталі листівки?"),
        ],
        accumulated={
            "requirements": {
                "quantity": 700,
                "product_name": "Кристал",
                "has_additional_elements": True,
            },
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Кристал коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Кристал карти", "card_count": 55},
                {"id": "info_leaflet", "type": "info_leaflet", "name": "Інформаційна листівка"},
            ],
        },
        input="Листівка 105×148 мм, друк 4+4 з обох сторін, з біговкою.",
        expected={
            "requirements": {"quantity": 700},
            "components": {
                "info_leaflet": {
                    "size_mm": [105, 148],
                    "print_colors": "4+4",
                    "has_crease": True,
                },
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# H – EXTENDED CONFUSION (more similar numbers / units)
# ---------------------------------------------------------------------------

CONF2_SCENARIOS: list[Scenario] = [
    Scenario(
        id="conf2_board_thickness_1_5_vs_pages_8",
        description="товщина 1.5 мм у правилах 8 сторінок — не плутати",
        input="Правила A5, 8 сторінок, скоба. Коробка палітурний картон 1.5 мм.",
        expected={
            "components": {
                "rulebook": {"pages": 8, "binding": "saddle_stitch"},
                "rigid_box": {"board_thickness_mm": 1.5},
            },
        },
    ),
    Scenario(
        id="conf2_deadline_vs_quantity",
        description="дедлайн 30 днів не плутати з тиражем 1000",
        input="Тираж 1000 шт., дедлайн 30 днів, коробка і карти 80 шт.",
        expected={
            "requirements": {"quantity": 1000, "deadline_days": 30},
            "components": {"card_deck": {"card_count": 80}},
        },
    ),
    Scenario(
        id="conf2_gsm_vs_quantity",
        description="граматура 350 gsm не плутати з тиражем 350",
        input="Тираж 350 наборів, карти 63×88 мм, 350 gsm, матова ламінація.",
        expected={
            "requirements": {"quantity": 350},
            "components": {"card_deck": {"gsm": 350}},
        },
    ),
    Scenario(
        id="conf2_card_size_width_vs_count",
        description="ширина карти 63 мм не плутати з кількістю 63",
        input="Карти завширшки 63 мм, довжиною 88 мм. Всього 120 карт у колоді, тираж 500.",
        expected={
            "requirements": {"quantity": 500},
            "components": {
                "card_deck": {
                    "card_count": 120,
                    "card_size_mm": [63, 88],
                }
            },
        },
    ),
    Scenario(
        id="conf2_box_height_vs_board_thickness",
        description="висота коробки 60 мм та товщина 1.75 мм — різні поля",
        input="Коробка 300×200×60 мм, палітурний картон 1.75 мм, матова ламінація.",
        expected={
            "components": {
                "rigid_box": {
                    "size_mm": [300, 200, 60],
                    "board_thickness_mm": 1.75,
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="conf2_leaflet_size_vs_card_size",
        description="листівка 100×150 мм та карта 63×88 мм — два різних розміри",
        input="Карти 63×88 мм, 80 штук. Листівка 100×150 мм, 4+4, без біговки. Тираж 600.",
        expected={
            "requirements": {"quantity": 600},
            "components": {
                "card_deck": {"card_count": 80, "card_size_mm": [63, 88]},
                "info_leaflet": {"size_mm": [100, 150], "has_crease": False},
            },
        },
    ),
    Scenario(
        id="conf2_rulebook_size_vs_card_size",
        description="правила A4 (210×297) та карти 63×88 — не плутати розміри",
        input="Правила A4, 12 сторінок, скоба. Карти 63×88 мм, 96 штук. Тираж 400.",
        expected={
            "requirements": {"quantity": 400},
            "components": {
                "rulebook": {"size_mm": [210, 297], "pages": 12},
                "card_deck": {"card_count": 96, "card_size_mm": [63, 88]},
            },
        },
    ),
    Scenario(
        id="conf2_three_components_all_sizes",
        description="три компоненти з розмірами — коробка, карти, правила — не перемішати",
        input=(
            "Коробка 330×230×65 мм, кришка і дно. "
            "Карти 88×63 мм, 54 карти, 300 gsm. "
            "Правила A5, 8 сторінок. "
            "Тираж 1200."
        ),
        expected={
            "requirements": {"quantity": 1200},
            "components": {
                "rigid_box": {"size_mm": [330, 230, 65]},
                "card_deck": {"card_count": 54, "card_size_mm": [88, 63]},
                "rulebook": {"size_mm": [148, 210], "pages": 8},
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# I – EXTENDED GUARDRAILS
# ---------------------------------------------------------------------------

GUARD2_SCENARIOS: list[Scenario] = [
    Scenario(
        id="guard2_stickers",
        description="Наклейки — не в профілі компанії",
        input="Хочу замовити наклейки для ноутбуків, 1000 штук.",
        expected={
            "status": "incomplete",
            "follow_up_contains": "настільн",
        },
    ),
    Scenario(
        id="guard2_books",
        description="Книги — не в профілі компанії",
        input="Потрібно видати книгу на 300 сторінок, тираж 500 примірників.",
        expected={
            "status": "incomplete",
            "follow_up_contains": "упаков",
        },
    ),
    Scenario(
        id="guard2_calendars",
        description="Календарі — не в профілі компанії",
        input="Замовлення: настінні календарі на 2026 рік, 200 штук.",
        expected={
            "status": "incomplete",
        },
    ),
    Scenario(
        id="guard2_no_components_negation",
        description="«ні, комплектуючих не треба» → has_game_components=False",
        input="Ні, комплектуючих не треба, тільки коробка і карти.",
        expected={
            "requirements": {"has_game_components": False},
        },
    ),
    Scenario(
        id="guard2_no_additional_elements",
        description="«без додаткових елементів» → has_additional_elements=False",
        input="Тираж 800, коробка, карти 100 штук. Без ігрового поля, без листівки.",
        expected={
            "requirements": {
                "has_additional_elements": False,
                "has_game_components": False,
                "quantity": 800,
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# J – EXTENDED EDGE CASES
# ---------------------------------------------------------------------------

EDGE2_SCENARIOS: list[Scenario] = [
    Scenario(
        id="edge2_no_product_name",
        description="Замовлення без назви гри — статус incomplete, питає назву",
        input="Потрібна коробка і карти 60 штук, тираж 500.",
        expected={
            "requirements": {"quantity": 500},
            "components": {"card_deck": {"card_count": 60}},
            "status": "incomplete",
        },
    ),
    Scenario(
        id="edge2_only_box_no_cards",
        description="Тільки коробка без карт — card_deck НЕ має з'явитися",
        input="Потрібна тільки коробка для гри «Форт», 350×250×80 мм, тираж 200.",
        expected={
            "requirements": {"quantity": 200, "product_name": "Форт"},
            "components": {"rigid_box": {"size_mm": [350, 250, 80]}},
            "no_hallucination": [],
        },
    ),
    Scenario(
        id="edge2_only_cards_no_box",
        description="Тільки карти без коробки — rigid_box НЕ має з'явитися",
        input="Потрібна лише колода карт 54 штуки для гри «Дуель», тираж 1000.",
        expected={
            "requirements": {"quantity": 1000},
            "components": {"card_deck": {"card_count": 54}},
        },
    ),
    Scenario(
        id="edge2_all_defaults_proposed",
        description="«не знаю» → агент пропонує стандарт 1.75 мм і запитує підтвердження",
        input="Коробка 300×200×60, не знаю яка товщина картону.",
        expected={
            "components": {"rigid_box": {"size_mm": [300, 200, 60]}},
            "follow_up_contains": "1.75",
        },
    ),
    Scenario(
        id="edge2_lamination_not_specified",
        description="Ламінація не вказана → агент пропонує матову",
        input="Коробка 280×190×55, кришка і дно, палітурний картон 1.75 мм.",
        expected={
            "components": {
                "rigid_box": {
                    "size_mm": [280, 190, 55],
                    "board_thickness_mm": 1.75,
                }
            },
            "status": "incomplete",
        },
    ),
    Scenario(
        id="edge2_mixed_ukrainian_english",
        description="Мікс укр/англ: «box 300×200×60, 110 cards, 300 gsm»",
        input="Box 300×200×60 mm, 110 cards, 300 gsm, matte lamination, тираж 600.",
        expected={
            "requirements": {"quantity": 600},
            "components": {
                "rigid_box": {"size_mm": [300, 200, 60]},
                "card_deck": {"card_count": 110, "gsm": 300},
            },
        },
    ),
    Scenario(
        id="edge2_typo_quantity",
        description="Опечатка: «тираж 10000» — може бути 1000 або справді 10000",
        input="Тираж 10000 коробок, карти 90 штук.",
        expected={
            "requirements": {"quantity": 10000},
            "components": {"card_deck": {"card_count": 90}},
        },
    ),
    Scenario(
        id="edge2_dimensions_with_x_letter",
        description="Розміри через «x» латинську: 300x200x60",
        input="Коробка 300x200x60 мм, кришка і дно, матова ламінація, тираж 700.",
        expected={
            "requirements": {"quantity": 700},
            "components": {
                "rigid_box": {
                    "size_mm": [300, 200, 60],
                    "construction": "lid_and_base",
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="edge2_components_mentioned_dice",
        description="«кубики D6» → has_game_components=True, каталог не потрібен якщо вже кількість",
        input="Тираж 500, коробка, карти 80 шт. Кубики D6 — 1000 штук, самі купимо.",
        expected={
            "requirements": {
                "has_game_components": True,
                "customer_provides_components": True,
                "quantity": 500,
            },
        },
    ),
    Scenario(
        id="edge2_print_colors_symmetric_3_3",
        description="«3+3» → print_colors=3+3 (симетричний трифарбовий)",
        input="Карти 63×88, 300 gsm, друк 3+3, матова ламінація, тираж 400.",
        expected={
            "components": {
                "card_deck": {
                    "print_colors": "3+3",
                    "front_finish": "matte_lamination",
                }
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# K – EXTENDED BASIC EXTRACTION (more field variants)
# ---------------------------------------------------------------------------

EXT3_SCENARIOS: list[Scenario] = [
    # --- rulebook binding from first message ---
    Scenario(
        id="ext3_rulebook_a5_saddle_stitch",
        description="Правила A5, 8 сторінок, на скобу — з першого повідомлення",
        input="Коробка, карти 60 штук, правила A5 8 сторінок на скобу, тираж 500.",
        expected={
            "requirements": {"quantity": 500},
            "components": {
                "rulebook": {"size_mm": [148, 210], "pages": 8, "binding": "saddle_stitch"},
                "card_deck": {"card_count": 60},
            },
        },
    ),
    Scenario(
        id="ext3_rulebook_a4_folding",
        description="Правила A4, 4 сторінки, фальцювання",
        input="Правила A4, 4 сторінки, фальцювання.",
        expected={
            "components": {
                "rulebook": {"size_mm": [210, 297], "pages": 4, "binding": "folding"},
            },
        },
    ),
    Scenario(
        id="ext3_box_lid_and_base",
        description="«кришка і дно» → construction=lid_and_base",
        input="Коробка 300×200×60 мм, кришка і дно, матова ламінація, тираж 1000.",
        expected={
            "requirements": {"quantity": 1000},
            "components": {
                "rigid_box": {
                    "size_mm": [300, 200, 60],
                    "construction": "lid_and_base",
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="ext3_box_sleeve",
        description="«дно і рукав» → construction=base_and_sleeve",
        input="Коробка 280×200×55 мм, дно і рукав, палітурний картон 1.75 мм, тираж 700.",
        expected={
            "components": {
                "rigid_box": {
                    "construction": "base_and_sleeve",
                    "board_thickness_mm": 1.75,
                }
            },
        },
    ),
    Scenario(
        id="ext3_cards_gloss_lamination",
        description="«глянцева ламінація» карт → front_finish і back_finish=gloss_lamination",
        input="Карти 63×88 мм, 350 gsm, друк 4+4, глянцева ламінація з обох сторін, тираж 500.",
        expected={
            "components": {
                "card_deck": {
                    "gsm": 350,
                    "print_colors": "4+4",
                    "front_finish": "gloss_lamination",
                    "back_finish": "gloss_lamination",
                }
            },
        },
    ),
    Scenario(
        id="ext3_cards_matte_one_side",
        description="«матова ламінація лише на лицьовій» → front_finish=matte, back_finish=none",
        input="Карти 63×88 мм, 300 gsm, 4+0, матова ламінація лише на лицьовій стороні, тираж 400.",
        expected={
            "components": {
                "card_deck": {
                    "print_colors": "4+0",
                    "front_finish": "matte_lamination",
                    "back_finish": "none",
                }
            },
        },
    ),
    Scenario(
        id="ext3_box_corrugated",
        description="«гофра» як основа → material=corrugated",
        input="Коробка на гофрі 350×250×70 мм, матова ламінація, тираж 300.",
        expected={
            "components": {
                "rigid_box": {
                    "material": "corrugated",
                    "size_mm": [350, 250, 70],
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="ext3_box_print_inside_outside",
        description="«друк зовні та всередині» → print_sides=outside_and_inside",
        input="Коробка 320×220×65 мм, друк зовні та всередині, матова ламінація, тираж 600.",
        expected={
            "components": {
                "rigid_box": {
                    "print_sides": "outside_and_inside",
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="ext3_deadline_weeks",
        description="«через 3 тижні» → deadline_days=21",
        input="Гра «Кіт», тираж 800, коробка, карти 70 шт. Дедлайн — через 3 тижні.",
        expected={
            "requirements": {
                "quantity": 800,
                "product_name": "Кіт",
                "deadline_days": 21,
            },
        },
    ),
    Scenario(
        id="ext3_game_board_edge_wrapped",
        description="«обклейка торців» → edge_finish=wrapped_edges",
        input="Ігрове поле 594×420 мм, обклейка торців, матова ламінація, тираж 500.",
        expected={
            "components": {
                "game_board": {
                    "size_mm": [594, 420],
                    "edge_finish": "wrapped_edges",
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="ext3_game_board_casherovane",
        description="«кашероване» → edge_finish=visible_board_edge",
        input="Ігрове поле 420×297 мм, кашероване, глянцева ламінація.",
        expected={
            "components": {
                "game_board": {
                    "size_mm": [420, 297],
                    "edge_finish": "visible_board_edge",
                    "lamination": "gloss",
                }
            },
        },
    ),
    Scenario(
        id="ext3_info_leaflet_crease",
        description="Листівка з біговкою → has_crease=True",
        input="Інформаційна листівка 148×105 мм, друк 4+4, є біговка, тираж 1000.",
        expected={
            "components": {
                "info_leaflet": {
                    "size_mm": [148, 105],
                    "print_colors": "4+4",
                    "has_crease": True,
                }
            },
        },
    ),
    Scenario(
        id="ext3_product_name_quotes",
        description="Назва гри у «лапках» витягується правильно",
        input="Замовлення для гри «Зоряний Шлях», тираж 1500, коробка і карти 100 шт.",
        expected={
            "requirements": {"product_name": "Зоряний Шлях", "quantity": 1500},
            "components": {"card_deck": {"card_count": 100}},
        },
    ),
    Scenario(
        id="ext3_print_colors_3_3",
        description="«3+3» симетричний трифарбовий",
        input="Карти 63×88 мм, 300 gsm, друк 3+3, матова ламінація, тираж 600.",
        expected={
            "components": {
                "card_deck": {
                    "print_colors": "3+3",
                    "front_finish": "matte_lamination",
                }
            },
        },
    ),
    Scenario(
        id="ext3_shrink_wrap_cards",
        description="«термопакування карт» → card_deck.shrink_wrap=True",
        input="Карти 63×88 мм, 300 gsm, 4+4, матова ламінація, термопакування, тираж 1000.",
        expected={
            "components": {
                "card_deck": {
                    "shrink_wrap": True,
                    "front_finish": "matte_lamination",
                }
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# L – EXTENDED MULTI-TURN (складніші діалоги)
# ---------------------------------------------------------------------------

MULTI3_SCENARIOS: list[Scenario] = [
    Scenario(
        id="multi3_correction_lamination",
        description="Клієнт виправляє ламінацію з матової на глянцеву",
        history=[
            ("Коробка 300×200×60, кришка і дно, матова ламінація.", "Зафіксував."),
        ],
        accumulated={
            "requirements": {},
            "components": [
                {
                    "id": "rigid_box",
                    "type": "rigid_box",
                    "name": "коробка",
                    "size_mm": [300, 200, 60],
                    "construction": "lid_and_base",
                    "lamination": "matte",
                }
            ],
        },
        input="Вибачте, замініть ламінацію на глянцеву.",
        expected={
            "components": {
                "rigid_box": {
                    "size_mm": [300, 200, 60],
                    "construction": "lid_and_base",
                    "lamination": "gloss",
                }
            },
        },
    ),
    Scenario(
        id="multi3_add_rulebook_midway",
        description="Правила додаються в середині розмови, попередні дані зберігаються",
        history=[
            ("Гра «Буря», тираж 600, коробка 300×200×60, карти 80 шт.", "Деталі коробки?"),
        ],
        accumulated={
            "requirements": {"quantity": 600, "product_name": "Буря"},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Буря коробка", "size_mm": [300, 200, 60]},
                {"id": "card_deck", "type": "card_deck", "name": "Буря карти", "card_count": 80},
            ],
        },
        input="Також потрібні правила A5, 8 сторінок, на скобу.",
        expected={
            "requirements": {"quantity": 600},
            "components": {
                "rulebook": {"size_mm": [148, 210], "pages": 8, "binding": "saddle_stitch"},
                "card_deck": {"card_count": 80},
            },
        },
    ),
    Scenario(
        id="multi3_quantity_preserved_after_details",
        description="Тираж зберігається після введення деталей карт",
        history=[
            ("Гра «Блиск», тираж 2000, коробка 350×250×80, карти 110 шт.", "Деталі карт?"),
        ],
        accumulated={
            "requirements": {"quantity": 2000, "product_name": "Блиск"},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Блиск коробка", "size_mm": [350, 250, 80]},
                {"id": "card_deck", "type": "card_deck", "name": "Блиск карти", "card_count": 110},
            ],
        },
        input="Карти 63×88 мм, 300 gsm, 4+4, матова ламінація.",
        expected={
            "requirements": {"quantity": 2000},
            "components": {
                "card_deck": {
                    "card_count": 110,
                    "card_size_mm": [63, 88],
                    "gsm": 300,
                    "print_colors": "4+4",
                    "front_finish": "matte_lamination",
                },
            },
        },
    ),
    Scenario(
        id="multi3_no_components_confirmed",
        description="Клієнт підтверджує «без комплектуючих» — зберігається в accumulated",
        history=[
            ("Гра «Місяць», тираж 300, коробка і карти 50 шт.", "Чи є комплектуючі?"),
        ],
        accumulated={
            "requirements": {"quantity": 300, "product_name": "Місяць"},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Місяць коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Місяць карти", "card_count": 50},
            ],
        },
        input="Ні, комплектуючих не треба.",
        expected={
            "requirements": {
                "quantity": 300,
                "has_game_components": False,
            },
            "components": {"card_deck": {"card_count": 50}},
        },
    ),
    Scenario(
        id="multi3_game_board_details_turn",
        description="Деталі ігрового поля в окремому turn",
        history=[
            ("Гра «Земля», тираж 400, коробка, карти 60 шт., ігрове поле.", "Деталі поля?"),
        ],
        accumulated={
            "requirements": {"quantity": 400, "product_name": "Земля", "has_additional_elements": True},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Земля коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Земля карти", "card_count": 60},
                {"id": "game_board", "type": "game_board", "name": "Ігрове поле"},
            ],
        },
        input="Поле 420×594 мм, один згин, 1.75 мм, лише лице 4+0, обклейка торців, матова.",
        expected={
            "requirements": {"quantity": 400},
            "components": {
                "game_board": {
                    "size_mm": [420, 594],
                    "board_thickness_mm": 1.75,
                    "print_colors": "4+0",
                    "edge_finish": "wrapped_edges",
                    "lamination": "matte",
                },
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# M – EXTENDED GUARDRAILS (більше кейсів)
# ---------------------------------------------------------------------------

GUARD3_SCENARIOS: list[Scenario] = [
    Scenario(
        id="guard3_pens",
        description="Ручки з логотипом — не в профілі",
        input="Хочу замовити 500 ручок з логотипом компанії.",
        expected={
            "status": "incomplete",
            "follow_up_contains": "упаков",
        },
    ),
    Scenario(
        id="guard3_packaging_game_ok",
        description="«упаковка для настільної гри» — в профілі, не відмовляємо",
        input="Потрібна упаковка для настільної гри «Арена», тираж 1000.",
        expected={
            "requirements": {"quantity": 1000, "product_name": "Арена"},
            "status": "incomplete",
        },
    ),
    Scenario(
        id="guard3_off_topic_mixed",
        description="Змішаний запит: гра + банери — пояснюємо профіль",
        input="Потрібна коробка для гри і ще банер для виставки.",
        expected={
            "follow_up_contains": "упаков",
        },
    ),
    Scenario(
        id="guard3_no_additional_confirmed",
        description="«без ігрового поля і листівки» → has_additional_elements=False",
        input="Тираж 500, коробка і карти 80 шт. Без ігрового поля і без листівки.",
        expected={
            "requirements": {
                "quantity": 500,
                "has_additional_elements": False,
            },
            "components": {"card_deck": {"card_count": 80}},
        },
    ),
]

# ---------------------------------------------------------------------------
# N – EXTENDED EDGE CASES (нові граничні випадки)
# ---------------------------------------------------------------------------

EDGE3_SCENARIOS: list[Scenario] = [
    Scenario(
        id="edge3_all_in_one_complete",
        description="Всі деталі в одному повідомленні — максимум полів",
        input=(
            "Гра «Цитадель», тираж 1000. "
            "Коробка 350×250×75 мм, кришка і дно, матова ламінація, палітурний картон 1.75 мм. "
            "Карти 63×88 мм, 120 карт, 300 gsm, 4+4, матова ламінація. "
            "Правила A5, 12 сторінок, на скобу. "
            "Без комплектуючих, без додаткових елементів."
        ),
        expected={
            "requirements": {
                "quantity": 1000,
                "product_name": "Цитадель",
                "has_game_components": False,
                "has_additional_elements": False,
            },
            "components": {
                "rigid_box": {
                    "size_mm": [350, 250, 75],
                    "construction": "lid_and_base",
                    "lamination": "matte",
                    "board_thickness_mm": 1.75,
                },
                "card_deck": {
                    "card_count": 120,
                    "card_size_mm": [63, 88],
                    "gsm": 300,
                    "print_colors": "4+4",
                    "front_finish": "matte_lamination",
                },
                "rulebook": {
                    "size_mm": [148, 210],
                    "pages": 12,
                    "binding": "saddle_stitch",
                },
            },
        },
    ),
    Scenario(
        id="edge3_only_rulebook",
        description="Лише правила без коробки — rigid_box не додається",
        input="Потрібні лише правила для гри «Код», A5, 8 сторінок, фальцювання, тираж 500.",
        expected={
            "requirements": {"quantity": 500, "product_name": "Код"},
            "components": {
                "rulebook": {
                    "size_mm": [148, 210],
                    "pages": 8,
                    "binding": "folding",
                }
            },
            "no_hallucination": [],
        },
    ),
    Scenario(
        id="edge3_only_game_board",
        description="Лише ігрове поле — rigid_box НЕ з'являється",
        input="Потрібне лише ігрове поле 840×594 мм, кашероване, матова ламінація, тираж 300.",
        expected={
            "requirements": {"quantity": 300},
            "components": {
                "game_board": {
                    "size_mm": [840, 594],
                    "edge_finish": "visible_board_edge",
                    "lamination": "matte",
                }
            },
            "no_hallucination": [],
        },
    ),
    Scenario(
        id="edge3_pantone_one_color",
        description="«1 колір Pantone» → print_colors=5+0",
        input="Карти з 1 кольором Pantone на лицьовій, тираж 600.",
        expected={
            "components": {"card_deck": {"print_colors": "5+0"}},
        },
    ),
    Scenario(
        id="edge3_pantone_two_colors",
        description="«2 кольори Pantone» → print_colors=6+0",
        input="Карти з двома Pantone на лицьовій, тираж 800.",
        expected={
            "components": {"card_deck": {"print_colors": "6+0"}},
        },
    ),
    Scenario(
        id="edge3_board_thickness_default_proposed",
        description="Не знає товщину картону → агент пропонує 1.75 мм",
        input="Ігрове поле 420×297 мм, матова ламінація. Яку товщину картону зазвичай беруть?",
        expected={
            "components": {"game_board": {"size_mm": [420, 297]}},
            "follow_up_contains": "1.75",
        },
    ),
    Scenario(
        id="edge3_uv_elements",
        description="«УФ-лак на логотипі» → uv_varnish=True з описом елемента",
        input="Коробка 300×200×60 мм, матова ламінація, УФ-лак на логотипі, тираж 700.",
        expected={
            "components": {
                "rigid_box": {
                    "uv_varnish": True,
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="edge3_quantity_thousand_word",
        description="«тисяча» словом → quantity=1000",
        input="Потрібна тисяча коробок для гри «Граф», карти 80 штук.",
        expected={
            "requirements": {"quantity": 1000, "product_name": "Граф"},
            "components": {"card_deck": {"card_count": 80}},
        },
    ),
    Scenario(
        id="edge3_client_name_midsentence",
        description="Ім'я в середині речення витягується",
        input="Мене звати Андрій. Хочу коробку для гри «Степ», тираж 400, карти 50 шт.",
        expected={
            "requirements": {
                "client_name": "Андрій",
                "product_name": "Степ",
                "quantity": 400,
            },
            "components": {"card_deck": {"card_count": 50}},
        },
    ),
    Scenario(
        id="edge3_multiple_components_sizes_correct",
        description="Коробка, карти і правила — розміри не перемішуються",
        input=(
            "Коробка 400×300×80 мм. Карти 88×63 мм, 54 карти. "
            "Правила A5, 16 сторінок. Тираж 800."
        ),
        expected={
            "requirements": {"quantity": 800},
            "components": {
                "rigid_box": {"size_mm": [400, 300, 80]},
                "card_deck": {"card_count": 54, "card_size_mm": [88, 63]},
                "rulebook": {"size_mm": [148, 210], "pages": 16},
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# O – EXTENDED BASIC EXTRACTION 4 (нові поля і варіанти)
# ---------------------------------------------------------------------------

EXT4_SCENARIOS: list[Scenario] = [
    Scenario(
        id="ext4_box_all_fields",
        description="Коробка з усіма полями в одному повідомленні",
        input=(
            "Коробка 320×220×65 мм, кришка і дно, друк зовні та всередині, "
            "палітурний картон 1.75 мм, матова ламінація, УФ-лак на логотипі, "
            "без термопакування. Тираж 800."
        ),
        expected={
            "requirements": {"quantity": 800},
            "components": {
                "rigid_box": {
                    "size_mm": [320, 220, 65],
                    "construction": "lid_and_base",
                    "print_sides": "outside_and_inside",
                    "board_thickness_mm": 1.75,
                    "lamination": "matte",
                    "uv_varnish": True,
                    "shrink_wrap": False,
                }
            },
        },
    ),
    Scenario(
        id="ext4_cards_all_fields",
        description="Карти з усіма полями: розмір, gsm, друк, покриття, термопакування",
        input="Карти 70×120 мм, 54 карти, 350 gsm, друк 4+4, глянцева лицьова, мат зворот, термопакування. Тираж 500.",
        expected={
            "requirements": {"quantity": 500},
            "components": {
                "card_deck": {
                    "card_count": 54,
                    "card_size_mm": [70, 120],
                    "gsm": 350,
                    "print_colors": "4+4",
                    "front_finish": "gloss_lamination",
                    "back_finish": "matte_lamination",
                    "shrink_wrap": True,
                }
            },
        },
    ),
    Scenario(
        id="ext4_rulebook_a6_folding",
        description="Правила A6, 4 сторінки, фальцювання",
        input="Правила формату A6, 4 сторінки, фальцювання.",
        expected={
            "components": {
                "rulebook": {
                    "size_mm": [105, 148],
                    "pages": 4,
                    "binding": "folding",
                }
            },
        },
    ),
    Scenario(
        id="ext4_soft_touch_lamination",
        description="Soft-touch ламінація на коробці → lamination=soft_touch",
        input="Преміальна коробка 350×250×80 мм, soft touch ламінація, палітурний картон 2 мм, тираж 300.",
        expected={
            "requirements": {"quantity": 300, "premium_finish": True},
            "components": {
                "rigid_box": {
                    "size_mm": [350, 250, 80],
                    "lamination": "soft_touch",
                    "board_thickness_mm": 2.0,
                }
            },
        },
    ),
    Scenario(
        id="ext4_info_leaflet_standalone",
        description="Лише листівка без коробки і карт",
        input="Потрібна лише інформаційна листівка 148×210 мм, друк 4+4, з біговкою, тираж 2000.",
        expected={
            "requirements": {"quantity": 2000},
            "components": {
                "info_leaflet": {
                    "size_mm": [148, 210],
                    "print_colors": "4+4",
                    "has_crease": True,
                }
            },
        },
    ),
    Scenario(
        id="ext4_game_board_fold_once",
        description="Ігрове поле складається вдвічі (один згин) — fold_description",
        input="Ігрове поле 420×297 мм, складається вдвічі, палітурний картон 1.75 мм, матова ламінація, обклейка торців.",
        expected={
            "components": {
                "game_board": {
                    "size_mm": [420, 297],
                    "board_thickness_mm": 1.75,
                    "lamination": "matte",
                    "edge_finish": "wrapped_edges",
                }
            },
        },
    ),
    Scenario(
        id="ext4_pantone_both_sides",
        description="Pantone з обох сторін → print_colors 5+5",
        input="Карти з Pantone з обох сторін (CMYK + 1 Pantone з кожної), тираж 400.",
        expected={
            "components": {
                "card_deck": {"print_colors": "5+5"},
            },
        },
    ),
    Scenario(
        id="ext4_two_pantone_colors",
        description="CMYK + 2 Pantone на лицьовій → print_colors 6+0",
        input="Карти: CMYK плюс два Pantone на лицьовій стороні, без зворотного друку. Тираж 600.",
        expected={
            "components": {
                "card_deck": {"print_colors": "6+0"},
            },
        },
    ),
    Scenario(
        id="ext4_deadline_weeks_conversion",
        description="«через 6 тижнів» → deadline_days=42",
        input="Гра «Рубін», тираж 700, коробка і карти 80 шт. Дедлайн через 6 тижнів.",
        expected={
            "requirements": {
                "quantity": 700,
                "product_name": "Рубін",
                "deadline_days": 42,
            },
        },
    ),
    Scenario(
        id="ext4_card_size_poker",
        description="«покер-формат» карт → card_size_mm=[63,88]",
        input="Карти покер-формату (63×88 мм), 100 штук, 300 gsm, тираж 1000.",
        expected={
            "components": {
                "card_deck": {
                    "card_size_mm": [63, 88],
                    "card_count": 100,
                    "gsm": 300,
                }
            },
        },
    ),
    Scenario(
        id="ext4_no_lamination_explicit",
        description="«без ламінації» → lamination може бути none або агент питає підтвердження",
        input="Коробка 300×200×60 мм, кришка і дно, без ламінації, тираж 500.",
        expected={
            "components": {
                "rigid_box": {
                    "size_mm": [300, 200, 60],
                    "construction": "lid_and_base",
                }
            },
            "status": "incomplete",
        },
    ),
    Scenario(
        id="ext4_box_sleeve_2mm",
        description="Дно і рукав з 2 мм картоном",
        input="Коробка 280×200×55 мм, дно і рукав, палітурний картон 2.0 мм, матова, тираж 400.",
        expected={
            "components": {
                "rigid_box": {
                    "size_mm": [280, 200, 55],
                    "construction": "base_and_sleeve",
                    "board_thickness_mm": 2.0,
                    "lamination": "matte",
                }
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# P – EXTENDED CONFUSION 3 (нові числові пастки)
# ---------------------------------------------------------------------------

CONF3_SCENARIOS: list[Scenario] = [
    Scenario(
        id="conf3_pages_vs_thickness_vs_deadline",
        description="Правила 16 стор., картон 1.5 мм, дедлайн 30 днів — три числа не плутати",
        input="Правила A5, 16 сторінок, на скобу. Коробка палітурний картон 1.5 мм. Дедлайн 30 днів.",
        expected={
            "requirements": {"deadline_days": 30},
            "components": {
                "rulebook": {"pages": 16, "binding": "saddle_stitch"},
                "rigid_box": {"board_thickness_mm": 1.5},
            },
        },
    ),
    Scenario(
        id="conf3_card_size_vs_count_vs_gsm",
        description="Карти 63×88 мм, 78 штук, 300 gsm — три числа не плутати",
        input="Карти розмір 63×88 мм, 78 штук у колоді, матеріал 300 gsm, тираж 600.",
        expected={
            "requirements": {"quantity": 600},
            "components": {
                "card_deck": {
                    "card_size_mm": [63, 88],
                    "card_count": 78,
                    "gsm": 300,
                }
            },
        },
    ),
    Scenario(
        id="conf3_box_height_60_vs_rulebook_pages_60",
        description="висота коробки 60 мм і правила 60 сторінок — різні поля",
        input="Коробка 300×200×60 мм. Правила A4, 60 сторінок, на скобу. Тираж 400.",
        expected={
            "requirements": {"quantity": 400},
            "components": {
                "rigid_box": {"size_mm": [300, 200, 60]},
                "rulebook": {"size_mm": [210, 297], "pages": 60},
            },
        },
    ),
    Scenario(
        id="conf3_gsm_350_vs_quantity_350",
        description="граматура 350 gsm і тираж 350 — однакові числа",
        input="Тираж 350, карти 63×88 мм, 350 gsm, матова ламінація.",
        expected={
            "requirements": {"quantity": 350},
            "components": {
                "card_deck": {
                    "gsm": 350,
                    "card_size_mm": [63, 88],
                    "front_finish": "matte_lamination",
                }
            },
        },
    ),
    Scenario(
        id="conf3_board_thickness_vs_crease_count",
        description="товщина 1.75 мм і 2 згини — різні числа одного компонента",
        input="Ігрове поле 840×594 мм, два згини (складається в A5), палітурний картон 1.75 мм, матова.",
        expected={
            "components": {
                "game_board": {
                    "size_mm": [840, 594],
                    "board_thickness_mm": 1.75,
                    "lamination": "matte",
                }
            },
        },
    ),
    Scenario(
        id="conf3_box_size_vs_card_size_close",
        description="Коробка 63×88 (маленька) і карти 63×88 — однакові числа різних об'єктів",
        input="Маленька коробка 63×88×20 мм і карти 63×88 мм, 54 штуки, тираж 200.",
        expected={
            "requirements": {"quantity": 200},
            "components": {
                "rigid_box": {"size_mm": [63, 88, 20]},
                "card_deck": {"card_count": 54, "card_size_mm": [63, 88]},
            },
        },
    ),
    Scenario(
        id="conf3_five_numbers_no_confusion",
        description="П'ять чисел поруч: тираж 1000, коробка 300×200×60, карти 110, gsm 300",
        input="Тираж 1000, коробка 300×200×60 мм, 110 карт, граматура 300 gsm, правила A5 8 стор.",
        expected={
            "requirements": {"quantity": 1000},
            "components": {
                "rigid_box": {"size_mm": [300, 200, 60]},
                "card_deck": {"card_count": 110, "gsm": 300},
                "rulebook": {"size_mm": [148, 210], "pages": 8},
            },
        },
    ),
    Scenario(
        id="conf3_leaflet_size_vs_rulebook_size",
        description="Листівка 100×150 і правила A5 (148×210) — два розміри не плутати",
        input="Правила A5, 8 стор., скоба. Листівка 100×150 мм, 4+4, без біговки. Тираж 500.",
        expected={
            "requirements": {"quantity": 500},
            "components": {
                "rulebook": {"size_mm": [148, 210], "pages": 8},
                "info_leaflet": {"size_mm": [100, 150], "has_crease": False},
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# Q – EXTENDED MULTI-TURN 4 (складніші потоки)
# ---------------------------------------------------------------------------

MULTI4_SCENARIOS: list[Scenario] = [
    # --- Standalone game_board доданий окремим turn ---
    Scenario(
        id="multi4_standalone_game_board_turn",
        description="Клієнт спочатку каже «лише поле» — game_board без rigid_box",
        history=[],
        accumulated={},
        input="Мені потрібне лише ігрове поле для гри «Мандрівник», 594×420 мм, матова ламінація, обклейка торців. Тираж 500.",
        expected={
            "requirements": {"quantity": 500},
            "components": {
                "game_board": {
                    "size_mm": [594, 420],
                    "lamination": "matte",
                    "edge_finish": "wrapped_edges",
                }
            },
        },
    ),
    # --- Rulebook деталі у фінальному turn (FIX TEST) ---
    Scenario(
        id="multi4_rulebook_final_turn_a5",
        description="Фінальний turn: «Правила A5, 12 стор., скоба» — all 3 fields extracted",
        history=[
            ("Гра «Фортеця», тираж 600, коробка, карти 80 шт., правила.", "Деталі правил?"),
        ],
        accumulated={
            "requirements": {"quantity": 600, "product_name": "Фортеця"},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Фортеця коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Фортеця карти", "card_count": 80},
                {"id": "rulebook", "type": "rulebook_thin", "name": "Правила гри"},
            ],
        },
        input="Правила A5, 12 сторінок, на скобу.",
        expected={
            "requirements": {"quantity": 600},
            "components": {
                "rulebook": {
                    "size_mm": [148, 210],
                    "pages": 12,
                    "binding": "saddle_stitch",
                },
                "card_deck": {"card_count": 80},
            },
        },
    ),
    # --- Expert role: повна розмова від імені клієнта ---
    Scenario(
        id="multi4_expert_full_order_one_turn",
        description="Експерт вводить повне замовлення одним повідомленням за клієнта",
        history=[],
        accumulated={},
        input=(
            "Контрагент: ТОВ «Ігровий Альянс». Гра «Арктика», тираж 1500. "
            "Коробка 350×250×80 мм, кришка і дно, матова ламінація, картон 1.75 мм. "
            "Карти 63×88 мм, 90 штук, 300 gsm, 4+4, матова ламінація. "
            "Правила A5, 8 сторінок, на скобу. "
            "Без комплектуючих, без додаткових елементів. Дедлайн 45 днів."
        ),
        expected={
            "requirements": {
                "quantity": 1500,
                "product_name": "Арктика",
                "has_game_components": False,
                "has_additional_elements": False,
                "deadline_days": 45,
            },
            "components": {
                "rigid_box": {
                    "size_mm": [350, 250, 80],
                    "construction": "lid_and_base",
                    "lamination": "matte",
                    "board_thickness_mm": 1.75,
                },
                "card_deck": {
                    "card_count": 90,
                    "card_size_mm": [63, 88],
                    "gsm": 300,
                    "print_colors": "4+4",
                },
                "rulebook": {
                    "size_mm": [148, 210],
                    "pages": 8,
                    "binding": "saddle_stitch",
                },
            },
        },
    ),
    # --- Turn де клієнт додає листівку і одразу дає всі деталі ---
    Scenario(
        id="multi4_leaflet_added_with_details",
        description="Клієнт додає листівку і одразу дає деталі — все в одному turn",
        history=[
            ("Гра «Прибій», тираж 400, коробка 300×200×60, карти 60 шт.", "Чи є додаткові елементи?"),
        ],
        accumulated={
            "requirements": {"quantity": 400, "product_name": "Прибій"},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Прибій коробка", "size_mm": [300, 200, 60]},
                {"id": "card_deck", "type": "card_deck", "name": "Прибій карти", "card_count": 60},
            ],
        },
        input="Так, є листівка 100×148 мм, друк 4+4, з біговкою.",
        expected={
            "requirements": {"has_additional_elements": True},
            "components": {
                "info_leaflet": {
                    "size_mm": [100, 148],
                    "print_colors": "4+4",
                    "has_crease": True,
                },
            },
        },
    ),
    # --- Turn з виправленням кількості карт ---
    Scenario(
        id="multi4_correction_card_count",
        description="Клієнт виправляє кількість карт з 60 на 90",
        history=[
            ("Гра «Тінь», тираж 700, коробка, карти 60 шт., правила.", "Деталі коробки?"),
        ],
        accumulated={
            "requirements": {"quantity": 700, "product_name": "Тінь"},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Тінь коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Тінь карти", "card_count": 60},
                {"id": "rulebook", "type": "rulebook_thin", "name": "Правила гри"},
            ],
        },
        input="Вибачте, карт буде 90, не 60. Коробка 320×220×65 мм, кришка і дно, матова.",
        expected={
            "requirements": {"quantity": 700},
            "components": {
                "card_deck": {"card_count": 90},
                "rigid_box": {
                    "size_mm": [320, 220, 65],
                    "construction": "lid_and_base",
                    "lamination": "matte",
                },
            },
        },
    ),
    # --- Чотиритurnова розмова — деталі кожного компонента ---
    Scenario(
        id="multi4_four_turns_all_components",
        description="Після 3 turns всі дані накопичено — 4-й turn дає правила",
        history=[
            ("Гра «Легенда», тираж 1000, коробка, карти 100 шт., правила.", "Деталі коробки?"),
            ("Коробка 330×230×70 мм, кришка і дно, матова, 1.75 мм.", "Деталі карт?"),
            ("Карти 63×88 мм, 300 gsm, 4+4, матова ламінація.", "Деталі правил?"),
        ],
        accumulated={
            "requirements": {"quantity": 1000, "product_name": "Легенда"},
            "components": [
                {
                    "id": "rigid_box", "type": "rigid_box", "name": "Легенда коробка",
                    "size_mm": [330, 230, 70], "construction": "lid_and_base",
                    "lamination": "matte", "board_thickness_mm": 1.75,
                },
                {
                    "id": "card_deck", "type": "card_deck", "name": "Легенда карти",
                    "card_count": 100, "card_size_mm": [63, 88],
                    "gsm": 300, "print_colors": "4+4", "front_finish": "matte_lamination",
                },
                {"id": "rulebook", "type": "rulebook_thin", "name": "Правила гри"},
            ],
        },
        input="Правила A4, 16 сторінок, фальцювання.",
        expected={
            "requirements": {"quantity": 1000},
            "components": {
                "rulebook": {
                    "size_mm": [210, 297],
                    "pages": 16,
                    "binding": "folding",
                },
                "rigid_box": {"size_mm": [330, 230, 70]},
                "card_deck": {"card_count": 100},
            },
        },
    ),
    # --- Multi-turn: обидва додаткові елементи по черзі ---
    Scenario(
        id="multi4_game_board_then_leaflet",
        description="Спочатку підтвердили поле, потім листівку — обидва у components",
        history=[
            ("Гра «Хвиля», тираж 800, коробка, карти 70 шт.", "Чи є ігрове поле?"),
            ("Так, є ігрове поле 420×297 мм.", "Чи є інформаційна листівка?"),
        ],
        accumulated={
            "requirements": {"quantity": 800, "product_name": "Хвиля", "has_additional_elements": True},
            "components": [
                {"id": "rigid_box", "type": "rigid_box", "name": "Хвиля коробка"},
                {"id": "card_deck", "type": "card_deck", "name": "Хвиля карти", "card_count": 70},
                {"id": "game_board", "type": "game_board", "name": "Ігрове поле", "size_mm": [420, 297]},
            ],
        },
        input="Так, є листівка 105×148 мм, двостороння 4+4, без біговки.",
        expected={
            "requirements": {"has_additional_elements": True},
            "components": {
                "game_board": {"size_mm": [420, 297]},
                "info_leaflet": {
                    "size_mm": [105, 148],
                    "print_colors": "4+4",
                    "has_crease": False,
                },
            },
        },
    ),
    # --- Multi-turn: клієнт додає поле standalone після відмови від коробки ---
    Scenario(
        id="multi4_only_board_accumulated",
        description="Клієнт уточнює деталі standalone game_board (без коробки)",
        history=[
            ("Потрібне лише ігрове поле для гри «Карта», тираж 300.", "Деталі поля?"),
        ],
        accumulated={
            "requirements": {"quantity": 300, "product_name": "Карта"},
            "components": [
                {"id": "game_board", "type": "game_board", "name": "Ігрове поле"},
            ],
        },
        input="Поле 840×594 мм, один згин (складається в A3), матова ламінація, кашероване.",
        expected={
            "requirements": {"quantity": 300},
            "components": {
                "game_board": {
                    "size_mm": [840, 594],
                    "lamination": "matte",
                    "edge_finish": "visible_board_edge",
                }
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# R – EXTENDED GUARDRAILS 4 (нові off-topic кейси)
# ---------------------------------------------------------------------------

GUARD4_SCENARIOS: list[Scenario] = [
    Scenario(
        id="guard4_magazine",
        description="Журнал — не в профілі",
        input="Хочу замовити журнал 50 сторінок, тираж 1000 примірників.",
        expected={
            "status": "incomplete",
            "follow_up_contains": "настільн",
        },
    ),
    Scenario(
        id="guard4_mugs",
        description="Чашки з логотипом — не в профілі",
        input="Потрібно 200 чашок з логотипом нашої компанії.",
        expected={
            "status": "incomplete",
            "follow_up_contains": "упаков",
        },
    ),
    Scenario(
        id="guard4_brochure_only",
        description="Рекламна брошура без прив'язки до гри — не в профілі",
        input="Рекламна брошура 8 сторінок, A4, тираж 500.",
        expected={
            "status": "incomplete",
        },
    ),
    Scenario(
        id="guard4_medical_packaging",
        description="Медична упаковка — не ігрова тематика, але слово 'упаковка'",
        input="Потрібна упаковка для ліків, блістери та коробочки, тираж 5000.",
        expected={
            "status": "incomplete",
            "follow_up_contains": "настільн",
        },
    ),
    Scenario(
        id="guard4_box_game_ok",
        description="«коробка для настільної гри» — В профілі",
        input="Мені потрібна коробка для настільної гри «Воїн», тираж 600.",
        expected={
            "requirements": {"quantity": 600, "product_name": "Воїн"},
            "status": "incomplete",
        },
    ),
    Scenario(
        id="guard4_components_customer_explicit",
        description="«всі комплектуючі надаємо самі» → customer_provides_components=True",
        input="Коробка, карти 80 шт., тираж 500. Комплектуючі — кубики і фішки — усі наші.",
        expected={
            "requirements": {
                "has_game_components": True,
                "customer_provides_components": True,
                "quantity": 500,
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# S – EXTENDED EDGE CASES 4 (нові граничні ситуації)
# ---------------------------------------------------------------------------

EDGE4_SCENARIOS: list[Scenario] = [
    # --- FIX TEST: standalone game_board ---
    Scenario(
        id="edge4_standalone_game_board_full",
        description="Standalone game_board: rigid_box НЕ має з'явитися (FIX TEST)",
        input="Потрібне лише ігрове поле 840×594 мм, кашероване, матова ламінація, тираж 300.",
        expected={
            "requirements": {"quantity": 300},
            "components": {
                "game_board": {
                    "size_mm": [840, 594],
                    "edge_finish": "visible_board_edge",
                    "lamination": "matte",
                }
            },
            "no_hallucination": [],
        },
    ),
    # --- FIX TEST: rulebook A5 extraction from short message ---
    Scenario(
        id="edge4_rulebook_a5_short_message",
        description="«Правила A5, 8 сторінок, на скобу.» — всі 3 поля (FIX TEST)",
        input="Правила A5, 8 сторінок, на скобу.",
        expected={
            "components": {
                "rulebook": {
                    "size_mm": [148, 210],
                    "pages": 8,
                    "binding": "saddle_stitch",
                }
            },
        },
    ),
    # --- FIX TEST: rulebook A4 folding from short message ---
    Scenario(
        id="edge4_rulebook_a4_folding_short",
        description="«Правила A4, 4 сторінки, фальцювання» — 3 поля одразу (FIX TEST)",
        input="Правила A4, 4 сторінки, фальцювання.",
        expected={
            "components": {
                "rulebook": {
                    "size_mm": [210, 297],
                    "pages": 4,
                    "binding": "folding",
                }
            },
        },
    ),
    # --- Standalone info_leaflet ---
    Scenario(
        id="edge4_standalone_info_leaflet",
        description="Лише листівка — rigid_box і card_deck не додаються",
        input="Потрібна лише інформаційна листівка 148×105 мм, 4+0, без біговки, тираж 3000.",
        expected={
            "requirements": {"quantity": 3000},
            "components": {
                "info_leaflet": {
                    "size_mm": [148, 105],
                    "print_colors": "4+0",
                    "has_crease": False,
                }
            },
            "no_hallucination": [],
        },
    ),
    # --- Standalone rulebook ---
    Scenario(
        id="edge4_standalone_rulebook_no_box",
        description="Лише правила без коробки і карт",
        input="Потрібні лише правила для гри «Зефір», A4, 8 сторінок, фальцювання. Тираж 800.",
        expected={
            "requirements": {"quantity": 800, "product_name": "Зефір"},
            "components": {
                "rulebook": {
                    "size_mm": [210, 297],
                    "pages": 8,
                    "binding": "folding",
                }
            },
            "no_hallucination": [],
        },
    ),
    # --- Порожнє повідомлення після привітання ---
    Scenario(
        id="edge4_empty_message",
        description="Порожнє або занадто коротке повідомлення — агент питає що потрібно",
        input="...",
        expected={
            "status": "incomplete",
        },
    ),
    # --- Дуже довга назва гри ---
    Scenario(
        id="edge4_long_product_name",
        description="Дуже довга назва гри витягується повністю",
        input="Гра «Пригоди у Кристальному Лісі: Доповнення», тираж 400, коробка і карти 60 шт.",
        expected={
            "requirements": {
                "quantity": 400,
                "product_name": "Пригоди у Кристальному Лісі: Доповнення",
            },
            "components": {"card_deck": {"card_count": 60}},
        },
    ),
    # --- Клієнт вказує два тиражі — беремо чіткий ---
    Scenario(
        id="edge4_two_quantities_take_explicit",
        description="Клієнт згадує два числа «від 500 до 1000» — агент уточнює або бере конкретне",
        input="Нам потрібно від 500 до 1000 коробок, але зараз зробіть розрахунок на 700 шт.",
        expected={
            "requirements": {"quantity": 700},
        },
    ),
    # --- Змішана мова (EN+UK) з усіма полями ---
    Scenario(
        id="edge4_mixed_lang_all_fields",
        description="Мікс EN/UK: box 300×200×60, 90 cards, A5 rulebook 8 pages",
        input="Box 300×200×60 mm, lid and base, matte lamination. Cards 63×88, 90 pcs, 300 gsm. Rulebook A5, 8 pages, saddle stitch. Тираж 500.",
        expected={
            "requirements": {"quantity": 500},
            "components": {
                "rigid_box": {
                    "size_mm": [300, 200, 60],
                    "construction": "lid_and_base",
                    "lamination": "matte",
                },
                "card_deck": {"card_count": 90, "card_size_mm": [63, 88], "gsm": 300},
                "rulebook": {"size_mm": [148, 210], "pages": 8, "binding": "saddle_stitch"},
            },
        },
    ),
    # --- Великий тираж ---
    Scenario(
        id="edge4_large_quantity_50k",
        description="Дуже великий тираж 50000 — не плутати з іншими числами",
        input="Тираж 50 000 коробок, карти 80 штук у колоді.",
        expected={
            "requirements": {"quantity": 50000},
            "components": {"card_deck": {"card_count": 80}},
        },
    ),
]

# ---------------------------------------------------------------------------
# T – STRESS TESTS (повне замовлення з усіма компонентами)
# ---------------------------------------------------------------------------

STRESS_SCENARIOS: list[Scenario] = [
    Scenario(
        id="stress_all_five_components",
        description="Усі 5 компонентів в одному повідомленні — максимальна складність",
        input=(
            "Гра «Галактика», тираж 1000. "
            "Коробка 380×280×80 мм, кришка і дно, матова ламінація, палітурний картон 1.75 мм. "
            "Карти 63×88 мм, 120 карт, 300 gsm, 4+4, матова ламінація. "
            "Правила A5, 16 сторінок, на скобу. "
            "Ігрове поле 594×420 мм, один згин, матова ламінація, обклейка торців. "
            "Листівка 100×148 мм, 4+4, з біговкою. "
            "Без комплектуючих. Дедлайн 60 днів."
        ),
        expected={
            "requirements": {
                "quantity": 1000,
                "product_name": "Галактика",
                "has_game_components": False,
                "has_additional_elements": True,
                "deadline_days": 60,
            },
            "components": {
                "rigid_box": {
                    "size_mm": [380, 280, 80],
                    "construction": "lid_and_base",
                    "lamination": "matte",
                    "board_thickness_mm": 1.75,
                },
                "card_deck": {
                    "card_count": 120,
                    "card_size_mm": [63, 88],
                    "gsm": 300,
                    "print_colors": "4+4",
                },
                "rulebook": {
                    "size_mm": [148, 210],
                    "pages": 16,
                    "binding": "saddle_stitch",
                },
                "game_board": {
                    "size_mm": [594, 420],
                    "lamination": "matte",
                    "edge_finish": "wrapped_edges",
                },
                "info_leaflet": {
                    "size_mm": [100, 148],
                    "print_colors": "4+4",
                    "has_crease": True,
                },
            },
        },
    ),
    Scenario(
        id="stress_max_box_fields",
        description="Коробка з абсолютно всіма полями та комплектуючими",
        input=(
            "Гра «Оракул», тираж 500. Коробка 300×200×60 мм, дно і рукав, "
            "друк зовні та всередині, палітурний картон 2.0 мм, матова ламінація, "
            "УФ-лак на логотипі, термопакування. "
            "Карти 63×88, 54 карти, 350 gsm, 4+0, матова лицьова, без зворотного. Термопакування карт. "
            "Є кубики D6 — 500 штук, закупимо самі. "
            "Дедлайн 30 днів."
        ),
        expected={
            "requirements": {
                "quantity": 500,
                "product_name": "Оракул",
                "has_game_components": True,
                "customer_provides_components": True,
                "deadline_days": 30,
            },
            "components": {
                "rigid_box": {
                    "size_mm": [300, 200, 60],
                    "construction": "base_and_sleeve",
                    "print_sides": "outside_and_inside",
                    "board_thickness_mm": 2.0,
                    "lamination": "matte",
                    "uv_varnish": True,
                    "shrink_wrap": True,
                },
                "card_deck": {
                    "card_count": 54,
                    "card_size_mm": [63, 88],
                    "gsm": 350,
                    "print_colors": "4+0",
                    "front_finish": "matte_lamination",
                    "shrink_wrap": True,
                },
            },
        },
    ),
    Scenario(
        id="stress_redundant_info",
        description="Повідомлення з повторюваною інформацією — беремо лише одне значення",
        input=(
            "Тираж 1000 коробок (1000 штук). "
            "Коробка розміром 300 на 200, висота 60 мм (тобто 300×200×60 мм). "
            "Матова ламінація (не глянцева). "
            "Палітурний картон 1.75 мм (стандарт 1.75)."
        ),
        expected={
            "requirements": {"quantity": 1000},
            "components": {
                "rigid_box": {
                    "size_mm": [300, 200, 60],
                    "lamination": "matte",
                    "board_thickness_mm": 1.75,
                }
            },
        },
    ),
    Scenario(
        id="stress_three_components_all_details",
        description="Коробка + карти + правила — всі деталі кожного компонента",
        input=(
            "Гра «Кристал», тираж 800. "
            "Коробка 320×220×70 мм, кришка і дно, друк зовні, палітурний картон 1.75 мм, матова ламінація, без УФ, без термопакування. "
            "Карти 63×88 мм, 100 карт, 300 gsm, 4+4, матова ламінація з обох сторін, без термопакування. "
            "Правила A5, 8 сторінок, на скобу."
        ),
        expected={
            "requirements": {"quantity": 800, "product_name": "Кристал"},
            "components": {
                "rigid_box": {
                    "size_mm": [320, 220, 70],
                    "construction": "lid_and_base",
                    "print_sides": "outside_only",
                    "board_thickness_mm": 1.75,
                    "lamination": "matte",
                    "uv_varnish": False,
                    "shrink_wrap": False,
                },
                "card_deck": {
                    "card_count": 100,
                    "card_size_mm": [63, 88],
                    "gsm": 300,
                    "print_colors": "4+4",
                    "front_finish": "matte_lamination",
                    "back_finish": "matte_lamination",
                    "shrink_wrap": False,
                },
                "rulebook": {
                    "size_mm": [148, 210],
                    "pages": 8,
                    "binding": "saddle_stitch",
                },
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# ALL SCENARIOS combined
# ---------------------------------------------------------------------------

ALL_SCENARIOS: list[Scenario] = (
    EXT_SCENARIOS
    + EXT2_SCENARIOS
    + EXT3_SCENARIOS
    + EXT4_SCENARIOS
    + CONF_SCENARIOS
    + CONF2_SCENARIOS
    + CONF3_SCENARIOS
    + MULTI_SCENARIOS
    + MULTI2_SCENARIOS
    + MULTI3_SCENARIOS
    + MULTI4_SCENARIOS
    + GUARD_SCENARIOS
    + GUARD2_SCENARIOS
    + GUARD3_SCENARIOS
    + GUARD4_SCENARIOS
    + EDGE_SCENARIOS
    + EDGE2_SCENARIOS
    + EDGE3_SCENARIOS
    + EDGE4_SCENARIOS
    + STRESS_SCENARIOS
)

SCENARIO_IDS: list[str] = [s.id for s in ALL_SCENARIOS]
