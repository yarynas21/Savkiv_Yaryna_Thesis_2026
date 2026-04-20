-- =============================================================================
-- Dyz-Art MAS — Knowledge Base Schema (DDL only)
-- Єдине джерело CREATE TABLE для всієї БД. Сиди — у backend/db/seeds/.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Machines
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS machines (
    id                 VARCHAR PRIMARY KEY,
    name               VARCHAR     NOT NULL,
    type               VARCHAR     NOT NULL,
    operation          VARCHAR     NOT NULL,
    max_sheet_mm       INTEGER[],
    min_sheet_mm       INTEGER[],
    colors             INTEGER,
    min_run            INTEGER,
    max_run            INTEGER,
    max_stock_gsm      INTEGER,
    min_stock_gsm      INTEGER,
    max_pages          INTEGER,
    min_pages          INTEGER,
    supported_finishes TEXT[],
    notes              TEXT
);

-- Global production constraints (key/value pairs)
CREATE TABLE IF NOT EXISTS machine_constraints (
    key   VARCHAR PRIMARY KEY,
    value TEXT    NOT NULL
);

-- ---------------------------------------------------------------------------
-- Materials — paper & cardboard substrates
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS papers (
    id              VARCHAR PRIMARY KEY,
    name            VARCHAR      NOT NULL,
    type            VARCHAR      NOT NULL,
    weight_gsm      INTEGER      NOT NULL,
    compatible_with TEXT[]       NOT NULL,
    typical_use     TEXT[]       NOT NULL,
    thickness_mm    NUMERIC(5,3)
);

-- Warehouse line items (exact CSV «Товар»); link to canonical papers for routing.
-- supply_form: roll = рулон (перед друком зазвичай roll_slitting); sheet = готові листи;
--   web = рулонний варіант (WEB у назві); film = плівка; NULL = не задано.
CREATE TABLE IF NOT EXISTS stock_items (
    stock_no    INTEGER  PRIMARY KEY,
    name        TEXT     NOT NULL,
    for_use     TEXT,
    supply_form VARCHAR(16),
    notes       TEXT,
    paper_id    VARCHAR  REFERENCES papers (id) ON DELETE SET NULL
);

-- ---------------------------------------------------------------------------
-- Materials — surface finishes
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS finishes (
    id                   VARCHAR PRIMARY KEY,
    name                 VARCHAR NOT NULL,
    applies_to           TEXT[]  NOT NULL,
    compatible_adhesives TEXT[],
    notes                TEXT
);

-- ---------------------------------------------------------------------------
-- Materials — adhesives
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS adhesives (
    id                   VARCHAR PRIMARY KEY,
    name                 VARCHAR NOT NULL,
    compatible_materials TEXT[]  NOT NULL,
    use_case             TEXT
);

-- ---------------------------------------------------------------------------
-- Production operations
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS operations (
    id                   VARCHAR PRIMARY KEY,
    name                 VARCHAR NOT NULL,
    step                 INTEGER NOT NULL,
    description          TEXT,
    required_for         TEXT[],
    compatible_materials TEXT[],
    duration_config      JSONB,
    output_text          VARCHAR,
    min_run              INTEGER,
    max_run              INTEGER
);

-- ---------------------------------------------------------------------------
-- Product type routes — ordered list of operations per product type
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS product_type_routes (
    product_type VARCHAR NOT NULL,
    sort_order   INTEGER NOT NULL,
    operation_id VARCHAR NOT NULL,
    PRIMARY KEY (product_type, sort_order)
);

-- ---------------------------------------------------------------------------
-- Game components — purchasable board-game parts (dice, meeples, tokens, …)
-- з цінами для орієнтовного підрахунку собівартості.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS game_components (
    id        VARCHAR(32)    PRIMARY KEY,
    name      TEXT           NOT NULL,
    category  VARCHAR(32)    NOT NULL,
    unit      VARCHAR(32)    NOT NULL,
    price_uah NUMERIC(10, 2) NOT NULL,
    notes     TEXT
);

-- ---------------------------------------------------------------------------
-- Cost calculator tariffs (paper UAH/kg, lamination, makeready, labour, …)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS cost_rates (
    category      VARCHAR(64)    NOT NULL,
    rate_key      VARCHAR(128)   NOT NULL,
    value_numeric NUMERIC(18, 6) NOT NULL,
    unit          VARCHAR(32),
    notes         TEXT,
    PRIMARY KEY (category, rate_key)
);

-- ---------------------------------------------------------------------------
-- Users & authentication
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) NOT NULL UNIQUE,
    username      VARCHAR(100) NOT NULL UNIQUE,
    password_hash TEXT         NOT NULL,
    role          VARCHAR(20)  NOT NULL DEFAULT 'operator'
                               CHECK (role IN ('admin', 'operator', 'expert')),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email    ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

-- Auto-update updated_at on row change
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS users_updated_at ON users;
CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
