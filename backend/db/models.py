"""
SQLAlchemy Core table definitions (metadata only — no ORM classes).

These are used both by Alembic (for schema introspection) and by
repository.py (for type-safe queries).
"""

from __future__ import annotations

from sqlalchemy import (
    ARRAY,
    Column,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

# Machines

machines = Table(
    "machines",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("type", String, nullable=False),
    Column("operation", String, nullable=False),
    Column("max_sheet_mm", ARRAY(Integer)),
    Column("min_sheet_mm", ARRAY(Integer)),
    Column("colors", Integer),
    Column("min_run", Integer),
    Column("max_run", Integer),
    Column("max_stock_gsm", Integer),
    Column("min_stock_gsm", Integer),
    Column("max_pages", Integer),
    Column("min_pages", Integer),
    Column("supported_finishes", ARRAY(String)),
    Column("notes", Text),
)

machine_constraints = Table(
    "machine_constraints",
    metadata,
    Column("key", String, primary_key=True),
    Column("value", Text, nullable=False),
)

# Materials — papers

papers = Table(
    "papers",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("type", String, nullable=False),
    Column("weight_gsm", Integer, nullable=False),
    Column("compatible_with", ARRAY(String), nullable=False),
    Column("typical_use", ARRAY(String), nullable=False),
    Column("thickness_mm", Numeric(5, 3)),
)

stock_items = Table(
    "stock_items",
    metadata,
    Column("stock_no", Integer, primary_key=True),
    Column("name", Text, nullable=False),
    Column("for_use", Text),
    Column("supply_form", String(16)),
    Column("notes", Text),
    Column("paper_id", String),
)

# Materials — finishes

finishes = Table(
    "finishes",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("applies_to", ARRAY(String), nullable=False),
    Column("compatible_adhesives", ARRAY(String)),
    Column("notes", Text),
)

# Materials — adhesives

adhesives = Table(
    "adhesives",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("compatible_materials", ARRAY(String), nullable=False),
    Column("use_case", Text),
)

# Operations

operations = Table(
    "operations",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("step", Integer, nullable=False),
    Column("description", Text),
    Column("required_for", ARRAY(String)),
    Column("compatible_materials", ARRAY(String)),
    Column("duration_config", JSONB),
    Column("output_text", String),
    Column("min_run", Integer),
    Column("max_run", Integer),
)

# Product type routes (ordered list of operations per product type)

product_type_routes = Table(
    "product_type_routes",
    metadata,
    Column("product_type", String, primary_key=True),
    Column("sort_order", Integer, primary_key=True),
    Column("operation_id", String, nullable=False),
)

# Game components — purchasable board-game parts with prices (UAH)

game_components = Table(
    "game_components",
    metadata,
    Column("id", String(32), primary_key=True),
    Column("name", Text, nullable=False),
    Column("category", String(32), nullable=False),
    Column("unit", String(32), nullable=False),
    Column("price_uah", Numeric(10, 2), nullable=False),
    Column("notes", Text),
)

# Cost calculator — numeric tariffs (merged with Python fallbacks in code)

cost_rates = Table(
    "cost_rates",
    metadata,
    Column("category", String(64), primary_key=True),
    Column("rate_key", String(128), primary_key=True),
    Column("value_numeric", Numeric(18, 6), nullable=False),
    Column("unit", String(32)),
    Column("notes", Text),
)
