-- =============================================================================
-- Dyz-Art MAS — Knowledge Base Schema
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Machines
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS machines (
    id                VARCHAR PRIMARY KEY,
    name              VARCHAR         NOT NULL,
    type              VARCHAR         NOT NULL,
    operation         VARCHAR         NOT NULL,
    max_sheet_mm      INTEGER[],
    min_sheet_mm      INTEGER[],
    colors            INTEGER,
    min_run           INTEGER,
    max_run           INTEGER,
    max_stock_gsm     INTEGER,
    min_stock_gsm     INTEGER,
    max_pages         INTEGER,
    min_pages         INTEGER,
    supported_finishes TEXT[],
    notes             TEXT
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
    name            VARCHAR     NOT NULL,
    type            VARCHAR     NOT NULL,
    weight_gsm      INTEGER     NOT NULL,
    compatible_with TEXT[]      NOT NULL,
    typical_use     TEXT[]      NOT NULL,
    thickness_mm    NUMERIC(5,3)
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
    name                 VARCHAR  NOT NULL,
    step                 INTEGER  NOT NULL,
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
