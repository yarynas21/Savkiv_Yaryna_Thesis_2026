from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger(__name__)

_COMPONENT_HEADINGS: dict[str, str] = {
    "_root": "Загальні питання",
    "rigid_box": "Коробка",
    "card_deck": "Колода карт",
    "rulebook": "Інструкція / Правила гри",
    "game_board": "Ігрове поле",
    "info_leaflet": "Інформаційна листівка",
}


@dataclass(frozen=True)
class FieldSpec:
    """Descriptor for a single required field in the extraction output.

    Attributes:
        key: Dot-notation identifier used for logging and deduplication.
        component: The product component id this field belongs to,
            or ``"_root"`` for top-level ``client_requirements`` fields.
        field: The dict key inside the component or requirements object.
        label: Human-readable Ukrainian question shown to the client.
    """

    key: str
    component: str
    field: str
    label: str


FIELD_SPECS: list[FieldSpec] = [
    FieldSpec(
        "product_name",
        "_root",
        "product_name",
        "**Назва гри** — як називається проєкт?",
    ),
    FieldSpec(
        "client_name",
        "_root",
        "client_name",
        "**Контрагент (замовник)** — від якої компанії/людини замовлення?",
    ),
    FieldSpec(
        "quantity",
        "_root",
        "quantity",
        "**Тираж** — скільки екземплярів друкувати?",
    ),
    FieldSpec(
        "deadline_days",
        "_root",
        "deadline_days",
        "**Дедлайн** — у скільки днів/до якої дати треба виготовити?",
    ),
    FieldSpec(
        "has_game_components",
        "_root",
        "has_game_components",
        "Чи є комплектуючі (кубики, фішки, пісочний годинник тощо)?",
    ),
    FieldSpec(
        "has_additional_elements",
        "_root",
        "has_additional_elements",
        "Чи є додаткові елементи (ігрове поле, листівка тощо)?",
    ),
    FieldSpec(
        "game_components_notes",
        "_root",
        "game_components_notes",
        "Які саме **комплектуючі** потрібні та в якій кількості (наприклад: *кубики D6 — 1000 шт*)?",
    ),
    FieldSpec(
        "box.size_mm",
        "rigid_box",
        "size_mm",
        "**Розмір коробки** — довжина × ширина × висота (мм)?",
    ),
    FieldSpec(
        "box.construction",
        "rigid_box",
        "construction",
        "**Конструктив коробки**: *кришка і дно* / *дно і рукав* / *самозбірна*?",
    ),
    FieldSpec(
        "box.print_sides",
        "rigid_box",
        "print_sides",
        "**Друк** — лише зовні коробки чи також і всередині?",
    ),
    FieldSpec(
        "box.material",
        "rigid_box",
        "material",
        "**Основа коробки** — *гофра* чи *палітурний картон*?",
    ),
    FieldSpec(
        "box.board_thickness_mm",
        "rigid_box",
        "board_thickness_mm",
        "**Товщина палітурного картону** (*1.5 мм* / *2.0 мм* — зазвичай обирають *1.75 мм*, підходить?)",
    ),
    FieldSpec(
        "box.lamination",
        "rigid_box",
        "lamination",
        "**Ламінація коробки** — *глянцева* чи *матова*?",
    ),
    FieldSpec(
        "box.uv_varnish",
        "rigid_box",
        "uv_varnish",
        "**УФ-лакування** на коробці — так чи ні? Якщо так — які елементи?",
    ),
    FieldSpec(
        "box.shrink_wrap",
        "rigid_box",
        "shrink_wrap",
        "**Термопакування коробки** — так чи ні?",
    ),
    FieldSpec(
        "cards.card_size_mm",
        "card_deck",
        "card_size_mm",
        "**Розмір карти** — довжина × ширина (мм)?",
    ),
    FieldSpec(
        "cards.gsm",
        "card_deck",
        "gsm",
        "**Граматура** матеріалу карт (наприклад *300 gsm*, *350 gsm*)?",
    ),
    FieldSpec(
        "cards.print_colors",
        "card_deck",
        "print_colors",
        "**Колірність друку** карт з двох сторін (наприклад *4+4*)?",
    ),
    FieldSpec(
        "cards.front_finish",
        "card_deck",
        "front_finish",
        "**Покриття лицьової сторони** карт (*глянцева ламінація* / *матова ламінація* / *УФ-лак* / *без*)?",
    ),
    FieldSpec(
        "cards.back_finish",
        "card_deck",
        "back_finish",
        "**Покриття зворотньої сторони** карт (*глянцева ламінація* / *матова ламінація* / *УФ-лак* / *без*)?",
    ),
    FieldSpec(
        "cards.shrink_wrap",
        "card_deck",
        "shrink_wrap",
        "**Термопакування карт** — так чи ні?",
    ),
    FieldSpec(
        "rulebook.size_mm",
        "rulebook",
        "size_mm",
        "**Розмір інструкції** — довжина × ширина (мм)?",
    ),
    FieldSpec(
        "rulebook.pages",
        "rulebook",
        "pages",
        "**Кількість сторінок** інструкції?",
    ),
    FieldSpec(
        "rulebook.binding",
        "rulebook",
        "binding",
        "**Кріплення інструкції**: *на скорбу* чи *фальцювання (згин)*?",
    ),
    FieldSpec(
        "game_board.size_mm",
        "game_board",
        "size_mm",
        "**Розмір ігрового поля** (розгорнутого) — довжина × ширина (мм)?",
    ),
    FieldSpec(
        "game_board.fold_description",
        "game_board",
        "fold_description",
        "**Формат складання поля** (наприклад *з A3 в A4*, один згин) — опишіть?",
    ),
    FieldSpec(
        "game_board.board_thickness_mm",
        "game_board",
        "board_thickness_mm",
        "**Товщина палітурного картону** основи поля (*1.5* / *2.0* мм; зазвичай *1.75* мм)?",
    ),
    FieldSpec(
        "game_board.print_sides",
        "game_board",
        "print_sides",
        "**Друк поля** — лише з лиця чи також із звороту?",
    ),
    FieldSpec(
        "game_board.edge_finish",
        "game_board",
        "edge_finish",
        "**Торці поля**: *з обклейкою* (торці закриті, картон не видно) чи *кашероване* (на зрізі видно палітурний картон)?",
    ),
    FieldSpec(
        "game_board.lamination",
        "game_board",
        "lamination",
        "**Ламінація поля** — *глянцева* чи *матова*?",
    ),
    FieldSpec(
        "info_leaflet.size_mm",
        "info_leaflet",
        "size_mm",
        "**Розмір листівки** — довжина × ширина (мм)?",
    ),
    FieldSpec(
        "info_leaflet.print_colors",
        "info_leaflet",
        "print_colors",
        "**Колірність друку** листівки з двох сторін (наприклад *4+4*)?",
    ),
    FieldSpec(
        "info_leaflet.has_crease",
        "info_leaflet",
        "has_crease",
        "**Чи передбачений згин (біговка)** на листівці — так чи ні?",
    ),
]


class ClientExtractionOutput(BaseModel):
    """Structured output contract for conversational requirements extraction."""

    status: str = Field(description="Either 'complete' or 'incomplete'")
    client_requirements: dict[str, Any] = Field(default_factory=dict)
    product_components: list[dict[str, Any]] = Field(default_factory=list)
    follow_up_question: str | None = Field(default=None)


def _find_missing_fields(result: dict[str, Any]) -> list[FieldSpec]:
    """Return the list of required fields that are absent or None in *result*.

    Checks both top-level ``client_requirements`` fields (component == "_root")
    and per-component fields keyed by ``id`` inside ``product_components``.
    """
    components = {component["id"]: component for component in result.get("product_components", [])}
    req = result.get("client_requirements", {})

    def value_of(spec: FieldSpec) -> Any:
        if spec.component == "_root":
            return req.get(spec.field)
        return components.get(spec.component, {}).get(spec.field)

    def spec_applies(spec: FieldSpec) -> bool:
        if spec.key == "game_components_notes":
            return req.get("has_game_components") is True
        if spec.component in _OPTIONAL_COMPONENT_IDS:
            return spec.component in components
        return True

    return [spec for spec in FIELD_SPECS if spec_applies(spec) and value_of(spec) is None]


_COMPONENT_ORDER: list[str] = [
    "_root",
    "rigid_box",
    "card_deck",
    "rulebook",
    "game_board",
    "info_leaflet",
]

_OPTIONAL_COMPONENT_IDS = frozenset({"game_board", "info_leaflet"})


def _format_missing_as_question(missing: list[FieldSpec]) -> str:
    """Ask only the first incomplete component group, not all at once.

    Fields are sorted by the canonical component order so the conversation
    progresses logically: root flags → box → cards → rulebook.
    Only the first group with missing fields is included in the question to
    avoid overwhelming the client with a wall of questions.
    """
    groups: dict[str, list[str]] = {}
    for spec in missing:
        groups.setdefault(spec.component, []).append(spec.label)

    first_component = next(
        (comp for comp in _COMPONENT_ORDER if comp in groups),
        next(iter(groups), None),
    )
    if first_component is None:
        return "Будь ласка, уточніть деталі замовлення."

    heading = _COMPONENT_HEADINGS.get(first_component, first_component)
    labels = groups[first_component]

    remaining_groups = sum(1 for c in _COMPONENT_ORDER if c in groups and c != first_component)
    progress_note = (
        f"\n_Ще {remaining_groups} розділ(и) після цього._" if remaining_groups else ""
    )

    sections: list[str] = [
        f"### {heading}",
        *[f"- {label}" for label in labels],
        progress_note,
        "",
        "Дякую! Як тільки уточнимо — одразу рухаємось далі.",
    ]
    return "\n".join(sections)


def _repair_extraction_result(result: Any) -> dict[str, Any]:
    """Normalise a raw LLM output dict, filling defaults for any missing or invalid keys.

    Ensures the returned dict always contains valid ``status``,
    ``client_requirements``, ``product_components``, and ``follow_up_question``
    entries regardless of what the model returned.
    """
    if not isinstance(result, dict):
        logger.warning(
            "LLM returned non-dict: %s (type=%s)", repr(result)[:120], type(result).__name__
        )
        result = {}

    repaired: dict[str, Any] = {
        "status": result.get("status", "incomplete"),
        "client_requirements": result.get("client_requirements") or {},
        "product_components": result.get("product_components") or [],
        "follow_up_question": result.get("follow_up_question"),
    }

    if repaired["status"] not in ("complete", "incomplete"):
        logger.warning("Invalid LLM status %r — defaulting to 'incomplete'", result.get("status"))
        repaired["status"] = "incomplete"

    if not isinstance(repaired["client_requirements"], dict):
        repaired["client_requirements"] = {}
    if not isinstance(repaired["product_components"], list):
        repaired["product_components"] = []
    if repaired["follow_up_question"] is not None and not isinstance(
        repaired["follow_up_question"], str
    ):
        repaired["follow_up_question"] = str(repaired["follow_up_question"])

    return repaired
