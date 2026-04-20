-- =============================================================================
-- Seed: cost_rates — тарифи калькулятора собівартості
-- Єдине джерело чисел: tools/cost_calculator.py читає цей файл як fallback,
-- якщо PostgreSQL недоступний.
-- =============================================================================

-- Глобальні скаляри (UAH, коефіцієнти, ставки)
INSERT INTO cost_rates (category, rate_key, value_numeric, unit, notes) VALUES
    ('global', 'hourly_rate_uah',             300.0,  'UAH/h',       NULL),
    ('global', 'offset_rate_per_color',      1800.0,  'UAH/прогін',  NULL),
    ('global', 'digital_rate_per_1k_sheets', 2500.0,  'UAH/1000арк', NULL),
    ('global', 'pantone_kg_per_run',            0.5,  'кг',          NULL),
    ('global', 'pantone_price_per_kg',       1200.0,  'UAH/кг',      NULL),
    ('global', 'flatting_rate_per_kg',          3.0,  'UAH/кг',      NULL),
    ('global', 'vysichka_setup_uah',          750.0,  'UAH',         'приладка висічки'),
    ('global', 'vysichka_rate_per_sheet',       0.75, 'UAH/арк',     NULL),
    ('global', 'creasing_setup_uah',          400.0,  'UAH',         'приладка рицовки'),
    ('global', 'creasing_rate_per_sheet',       0.50, 'UAH/арк',     NULL),
    ('global', 'uv_rate_m2',                   18.0,  'UAH/м²',      NULL),
    ('global', 'kashire_rate_m2',              13.0,  'UAH/м²',      NULL),
    ('global', 'default_margin',                1.10, 'коеф.',       '+10% до собівартості');

-- Матеріали (папір / картон / чіпборд / лайнери): орієнтовна закупівельна ціна, грн за 1 кг.
-- rate_key = id з таблиці papers (див. seeds/03_papers.sql). Якщо матеріалу немає у списку —
-- у калькуляторі використовується paper_kg._default.
INSERT INTO cost_rates (category, rate_key, value_numeric, unit, notes) VALUES
    ('paper_kg', 'coated_90',            72.0, 'UAH/кг', NULL),
    ('paper_kg', 'coated_115',           74.0, 'UAH/кг', NULL),
    ('paper_kg', 'coated_130',           76.0, 'UAH/кг', NULL),
    ('paper_kg', 'coated_150',           78.0, 'UAH/кг', NULL),
    ('paper_kg', 'coated_160',           80.0, 'UAH/кг', NULL),
    ('paper_kg', 'coated_170',           81.0, 'UAH/кг', NULL),
    ('paper_kg', 'coated_250',           86.0, 'UAH/кг', NULL),
    ('paper_kg', 'coated_300',           89.0, 'UAH/кг', NULL),
    ('paper_kg', 'coated_320',           90.0, 'UAH/кг', NULL),
    ('paper_kg', 'coated_350',           91.0, 'UAH/кг', NULL),
    ('paper_kg', 'coated_400',           93.0, 'UAH/кг', NULL),
    ('paper_kg', 'playing_card_310',     95.0, 'UAH/кг', NULL),
    ('paper_kg', 'offset_90',            56.0, 'UAH/кг', NULL),
    ('paper_kg', 'offset_120',           58.0, 'UAH/кг', NULL),
    ('paper_kg', 'offset_250',           64.0, 'UAH/кг', NULL),
    ('paper_kg', 'grey_chipboard_1500',  50.0, 'UAH/кг', NULL),
    ('paper_kg', 'grey_chipboard_2000',  53.0, 'UAH/кг', NULL),
    ('paper_kg', 'kraft_white_280',      66.0, 'UAH/кг', NULL),
    ('paper_kg', 'kraftliner_brown_170', 56.0, 'UAH/кг', NULL),
    ('paper_kg', 'liner_white_130',      54.0, 'UAH/кг', NULL),
    ('paper_kg', 'liner_topliner_100',   52.0, 'UAH/кг', NULL),
    ('paper_kg', 'liner_topliner_135',   55.0, 'UAH/кг', NULL),
    ('paper_kg', 'liner_topliner_160',   57.0, 'UAH/кг', NULL),
    ('paper_kg', 'liner_topliner_200',   59.0, 'UAH/кг', NULL),
    ('paper_kg', '_default',             75.0, 'UAH/кг', NULL);

-- Покриття — ламінація (грн/м²); ключі збігаються з типом ламінації в маршруті.
INSERT INTO cost_rates (category, rate_key, value_numeric, unit, notes) VALUES
    ('lam_m2', 'gloss',      11.0, 'UAH/м²', NULL),
    ('lam_m2', 'matte',      12.0, 'UAH/м²', NULL),
    ('lam_m2', 'soft_touch', 25.0, 'UAH/м²', NULL),
    ('lam_m2', '_default',   12.0, 'UAH/м²', NULL);

-- Приладочні втрати аркушів по типу операції
INSERT INTO cost_rates (category, rate_key, value_numeric, unit, notes) VALUES
    ('makeready', 'offset_printing',  350, 'арк', NULL),
    ('makeready', 'digital_printing',  50, 'арк', NULL),
    ('makeready', 'die_cutting',      200, 'арк', NULL),
    ('makeready', 'lamination',       100, 'арк', NULL),
    ('makeready', 'creasing',         150, 'арк', NULL),
    ('makeready', '_default',         200, 'арк', NULL);

-- Продуктивність ручних/лінійних операцій (шт/год)
INSERT INTO cost_rates (category, rate_key, value_numeric, unit, notes) VALUES
    ('productivity', 'blank_stripping',    2000, 'шт/год', NULL),
    ('productivity', 'flap_gluing',         300, 'шт/год', NULL),
    ('productivity', 'corner_wrapping',    1250, 'шт/год', NULL),
    ('productivity', 'manual_wrapping',      80, 'шт/год', NULL),
    ('productivity', 'card_cutting',       3000, 'шт/год', NULL),
    ('productivity', 'card_shrink_wrap',    600, 'шт/год', NULL),
    ('productivity', 'shrink_wrap_packing', 600, 'шт/год', NULL),
    ('productivity', 'box_packing',         200, 'шт/год', NULL),
    ('productivity', 'pallet_packing',     1000, 'шт/год', NULL),
    ('productivity', 'assembly',            300, 'шт/год', NULL),
    ('productivity', 'game_kit_assembly',   300, 'шт/год', NULL),
    ('productivity', '_default',            500, 'шт/год', NULL);
