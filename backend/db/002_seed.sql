-- =============================================================================
-- Dyz-Art MAS — Knowledge Base Seed Data
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Machines
-- ---------------------------------------------------------------------------

INSERT INTO machines
    (id, name, type, operation, max_sheet_mm, min_sheet_mm, colors,
     min_run, max_run, max_stock_gsm, min_stock_gsm, notes)
VALUES
    ('heidelberg_sm52',
     'Heidelberg Speedmaster SM 52',
     'offset_press', 'offset_printing',
     ARRAY[360, 520], ARRAY[100, 150],
     4, 100, NULL, 400, 60,
     'Основна аркушева офсетна машина. CMYK + Pantone.'),

    ('heidelberg_sm74',
     'Heidelberg Speedmaster SM 74',
     'offset_press', 'offset_printing',
     ARRAY[530, 740], ARRAY[200, 280],
     5, 500, NULL, 400, 60,
     '5-фарбова машина. CMYK + 1 Pantone або лак inline.'),

    ('hp_indigo_12000',
     'HP Indigo 12000',
     'digital_press', 'digital_printing',
     ARRAY[480, 660], ARRAY[100, 148],
     7, NULL, 1000, 350, 60,
     'Цифровий друк для малих тиражів. Персоналізація.'),

    ('laminator_autobond',
     'Autobond Mini 76 T',
     'laminator', 'lamination',
     ARRAY[760, 1060], ARRAY[200, 280],
     NULL, NULL, NULL, 400, NULL,
     'Термоламінатор для аркушевої продукції.'),

    ('uv_coater_dk',
     'DK-1650 UV Coater',
     'uv_coater', 'uv_varnishing',
     ARRAY[650, 1050], NULL,
     NULL, NULL, NULL, 400, NULL,
     'Суцільне та вибіркове УФ-лакування.'),

    ('foil_stamper_kama',
     'KAMA ProCut 74',
     'foil_stamper', 'hot_foil_stamping',
     ARRAY[530, 740], NULL,
     NULL, 100, NULL, 450, NULL,
     'Гаряче тиснення фольгою. Потрібне кліше (виготовлення 3-5 днів).'),

    ('die_cutter_bobst',
     'BOBST SP 76 E',
     'die_cutter', 'die_cutting',
     ARRAY[760, 1060], NULL,
     NULL, 200, NULL, 800, NULL,
     'Висічна машина. Потрібен висічний штамп (виготовлення 1-2 дні).'),

    ('creaser_morgana',
     'Morgana AutoCreaser Pro 50',
     'creaser', 'creasing',
     ARRAY[350, 500], NULL,
     NULL, NULL, NULL, 400, NULL,
     'Автоматична біговка.'),

    ('card_cutter_polar',
     'POLAR 115 + Corner Rounder',
     'guillotine_cutter', 'card_cutting',
     ARRAY[1150, 1150], NULL,
     NULL, NULL, NULL, NULL, NULL,
     'Різання карт + закруглення кутів R3/R4.'),

    ('saddle_stitcher_muller',
     'Müller Martini BRAVO',
     'saddle_stitcher', 'saddle_stitching',
     NULL, NULL,
     NULL, NULL, NULL, 170, NULL,
     'Зшивання скобою. Мінімум 8 сторінок.'),

    ('perfect_binder_horizon',
     'Horizon BQ-270',
     'perfect_binder', 'perfect_binding',
     NULL, NULL,
     NULL, NULL, NULL, 170, NULL,
     'Клейове скріплення для книг і товстих правил.');

-- Machines with max_pages / min_pages
UPDATE machines SET max_pages = 96,  min_pages = 8  WHERE id = 'saddle_stitcher_muller';
UPDATE machines SET max_pages = 500, min_pages = 32 WHERE id = 'perfect_binder_horizon';

-- Laminator supported finishes
UPDATE machines
SET supported_finishes = ARRAY['gloss_lamination','matte_lamination','soft_touch_lamination']
WHERE id = 'laminator_autobond';

UPDATE machines
SET supported_finishes = ARRAY['uv_varnish']
WHERE id = 'uv_coater_dk';

-- ---------------------------------------------------------------------------
-- Machine constraints
-- ---------------------------------------------------------------------------

INSERT INTO machine_constraints (key, value) VALUES
    ('foil_stamping_requires_cliche',   'true'),
    ('foil_cliche_lead_time_days',      '5'),
    ('die_cutting_requires_die',        'true'),
    ('die_lead_time_days',              '2'),
    ('min_offset_run',                  '100'),
    ('digital_max_run',                 '1000'),
    ('soft_touch_requires_heat_press',  'true'),
    ('card_min_gsm',                    '280'),
    ('card_max_gsm',                    '360');

-- ---------------------------------------------------------------------------
-- Papers
-- ---------------------------------------------------------------------------

INSERT INTO papers (id, name, type, weight_gsm, compatible_with, typical_use, thickness_mm)
VALUES
    ('coated_300',
     'Крейдований картон 300 г/м²',
     'cardboard', 300,
     ARRAY['offset_printing','digital_printing','uv_varnish',
           'gloss_lamination','matte_lamination','soft_touch_lamination'],
     ARRAY['rigid_box_cover','premium_packaging'],
     0.400),

    ('coated_250',
     'Крейдований картон 250 г/м²',
     'cardboard', 250,
     ARRAY['offset_printing','digital_printing','uv_varnish',
           'gloss_lamination','matte_lamination'],
     ARRAY['box_cover','card_deck_packaging'],
     0.320),

    ('coated_350',
     'Крейдований картон 350 г/м²',
     'cardboard', 350,
     ARRAY['offset_printing','uv_varnish',
           'gloss_lamination','matte_lamination','soft_touch_lamination'],
     ARRAY['heavy_rigid_box','premium_game_box'],
     0.500),

    ('grey_chipboard_1500',
     'Сірий картон 1500 г/м² (чіпборд)',
     'chipboard', 1500,
     ARRAY['lamination_cover','wrapping'],
     ARRAY['rigid_box_inner','game_board_base'],
     1.800),

    ('grey_chipboard_2000',
     'Сірий картон 2000 г/м² (чіпборд)',
     'chipboard', 2000,
     ARRAY['lamination_cover','wrapping'],
     ARRAY['rigid_box_heavy','book_cover_base'],
     2.500),

    ('playing_card_310',
     'Картон для карт 310 г/м² (блакитний оборот)',
     'playing_card_stock', 310,
     ARRAY['offset_printing','digital_printing','uv_varnish','aqueous_coating'],
     ARRAY['playing_cards','tarot_cards'],
     0.300),

    ('offset_90',
     'Офсетний папір 90 г/м²',
     'paper', 90,
     ARRAY['offset_printing','digital_printing'],
     ARRAY['rulebook','insert_pages'],
     0.100),

    ('offset_120',
     'Офсетний папір 120 г/м²',
     'paper', 120,
     ARRAY['offset_printing','digital_printing'],
     ARRAY['rulebook_premium','thick_insert'],
     0.130);

-- ---------------------------------------------------------------------------
-- Finishes
-- ---------------------------------------------------------------------------

INSERT INTO finishes (id, name, applies_to, compatible_adhesives, notes)
VALUES
    ('gloss_lamination',
     'Глянцева ламінація',
     ARRAY['cardboard','paper'],
     ARRAY['hot_melt_EVA','water_based'],
     'Стандартна ламінація, яскраві кольори'),

    ('matte_lamination',
     'Матова ламінація',
     ARRAY['cardboard','paper'],
     ARRAY['hot_melt_EVA','water_based'],
     'Елегантний вигляд, відсутність відблисків'),

    ('soft_touch_lamination',
     'Soft Touch ламінація',
     ARRAY['cardboard'],
     ARRAY['hot_melt_EVA'],
     'Оксамитова текстура, преміум сегмент. Потребує термічного преса'),

    ('uv_varnish',
     'УФ-лак',
     ARRAY['cardboard','paper'],
     ARRAY[]::TEXT[],
     'Наноситься поверх задрукованого матеріалу'),

    ('aqueous_coating',
     'Водний лак',
     ARRAY['cardboard','paper','playing_card_stock'],
     ARRAY[]::TEXT[],
     'Захисне покриття, підходить для карт'),

    ('hot_foil_stamping',
     'Тиснення фольгою',
     ARRAY['cardboard'],
     ARRAY[]::TEXT[],
     'Потребує спеціального кліше; золота / срібна / кольорова фольга'),

    ('embossing',
     'Рельєфне тиснення (конгрев/деборг)',
     ARRAY['cardboard'],
     ARRAY[]::TEXT[],
     'Потребує кліше; часто комбінується з фольгуванням');

-- ---------------------------------------------------------------------------
-- Adhesives
-- ---------------------------------------------------------------------------

INSERT INTO adhesives (id, name, compatible_materials, use_case)
VALUES
    ('hot_melt_EVA',
     'Термоклей EVA',
     ARRAY['cardboard','chipboard','paper'],
     'склеювання жорстких коробок, ламінація'),

    ('water_based',
     'Клей на водній основі',
     ARRAY['paper','cardboard'],
     'брошурування, склеювання вставок'),

    ('pva',
     'ПВА',
     ARRAY['paper','cardboard'],
     'палітурні роботи, клеєні вставки'),

    ('uv_glue',
     'УФ-клей',
     ARRAY['playing_card_stock'],
     'склеювання двошарових ігрових карт');

-- ---------------------------------------------------------------------------
-- Operations
-- ---------------------------------------------------------------------------

INSERT INTO operations
    (id, name, step, description, required_for, compatible_materials,
     duration_config, output_text, min_run, max_run)
VALUES
    ('prepress',
     'Допечатна підготовка', 1,
     'Верстка, кольорокорекція, підготовка PDF до друку (ICC-профілі, треппінг, марки)',
     ARRAY['all'], NULL,
     '{"duration_hours_per_job": 2}',
     'print-ready PDF', NULL, NULL),

    ('offset_printing',
     'Офсетний друк', 2,
     '4-кольоровий (CMYK) або Pantone друк на аркушевій офсетній машині',
     ARRAY['box_cover','card_deck','rulebook','insert'],
     ARRAY['coated_300','coated_250','coated_350','offset_90','offset_120','playing_card_310'],
     '{"duration_hours_per_1000_sheets": 0.5}',
     'задрукований аркуш', 500, NULL),

    ('digital_printing',
     'Цифровий друк', 2,
     'HP Indigo або Xerox — для малих тиражів і персоналізації',
     ARRAY['box_cover','card_deck','rulebook'],
     ARRAY['coated_300','coated_250','offset_90','offset_120','playing_card_310'],
     '{"duration_hours_per_1000_sheets": 1.5}',
     'задрукований аркуш', NULL, 499),

    ('lamination',
     'Ламінація', 3,
     'Нанесення захисної плівки (глянець / матова / soft touch) на задруковану поверхню',
     ARRAY['box_cover','card_deck_cover','premium_insert'],
     ARRAY['coated_300','coated_250','coated_350','offset_120'],
     '{"duration_hours_per_1000_sheets": 0.4}',
     'ламінований аркуш', NULL, NULL),

    ('uv_varnishing',
     'УФ-лакування', 4,
     'Суцільне або вибіркове УФ-лакування для блиску або захисту',
     ARRAY['premium_box_cover','card_deck'],
     ARRAY['coated_300','coated_250','playing_card_310'],
     '{"duration_hours_per_1000_sheets": 0.3}',
     'лакований аркуш', NULL, NULL),

    ('hot_foil_stamping',
     'Гаряче тиснення фольгою', 5,
     'Нанесення металевої або голографічної фольги за допомогою нагрітого кліше',
     ARRAY['premium_box_cover'],
     ARRAY['coated_300','coated_350'],
     '{"duration_hours_per_1000_sheets": 1.0}',
     'аркуш з фольгою', NULL, NULL),

    ('embossing',
     'Рельєфне тиснення', 5,
     'Формування рельєфу (конгрев — опуклий / деборг — увігнутий) без фарби',
     ARRAY['premium_box_cover'],
     ARRAY['coated_300','coated_350'],
     '{"duration_hours_per_1000_sheets": 0.8}',
     'аркуш з рельєфом', NULL, NULL),

    ('die_cutting',
     'Вирубка (висічка)', 6,
     'Вирізання заготовок за формою за допомогою висічного штампу',
     ARRAY['box_blank','card_blank','insert_blank'],
     ARRAY['coated_300','coated_250','coated_350','playing_card_310'],
     '{"duration_hours_per_1000_sheets": 0.6}',
     'готова заготовка', NULL, NULL),

    ('creasing',
     'Біговка', 6,
     'Нанесення ліній згину на картон для подальшого складання',
     ARRAY['box_blank'],
     ARRAY['coated_300','coated_250','coated_350'],
     '{"duration_hours_per_1000_sheets": 0.3}',
     'заготовка з лініями згину', NULL, NULL),

    ('chipboard_laminating',
     'Обклейка сірого картону (чіпборда)', 7,
     'Приклеювання задрукованого покривного аркуша на основу з сірого картону',
     ARRAY['rigid_box'],
     ARRAY['grey_chipboard_1500','grey_chipboard_2000'],
     '{"duration_hours_per_1000_units": 2.0}',
     'сторінка жорсткої коробки', NULL, NULL),

    ('box_assembly',
     'Складання коробки', 8,
     'Ручне або машинне складання заготовки у готову коробку',
     ARRAY['rigid_box','folding_box'],
     NULL,
     '{"duration_hours_per_1000_units": 3.0}',
     'готова коробка', NULL, NULL),

    ('card_cutting',
     'Різання карт (гільотина + закруглення кутів)', 7,
     'Порізка задрукованого аркуша на картки, закруглення кутів R3/R4',
     ARRAY['card_deck'],
     ARRAY['playing_card_310'],
     '{"duration_hours_per_1000_cards": 0.2}',
     'готові картки', NULL, NULL),

    ('saddle_stitching',
     'Зшивання скобою (садл-стітч)', 7,
     'Зшивання аркушів металевими скобами по корінцю',
     ARRAY['rulebook_thin'],
     ARRAY['offset_90','offset_120'],
     '{"duration_hours_per_1000_units": 0.5}',
     'готова брошура', NULL, NULL),

    ('perfect_binding',
     'Клейове скріплення (perfect binding)', 7,
     'Клеєне скріплення аркушів по корінцю — для товстих книг/правил',
     ARRAY['rulebook_thick'],
     ARRAY['offset_90','offset_120'],
     '{"duration_hours_per_1000_units": 1.0}',
     'готова книга', NULL, NULL),

    ('quality_control',
     'Контроль якості', 9,
     'Візуальна та інструментальна перевірка якості готової продукції',
     ARRAY['all'], NULL,
     '{"duration_hours_per_1000_units": 0.5}',
     'верифікований продукт', NULL, NULL),

    ('packaging',
     'Пакування та відвантаження', 10,
     'Пакування у транспортну упаковку, маркування, підготовка до відвантаження',
     ARRAY['all'], NULL,
     '{"duration_hours_per_1000_units": 0.3}',
     'готовий замовлення', NULL, NULL);

-- ---------------------------------------------------------------------------
-- Product type routes
-- ---------------------------------------------------------------------------

INSERT INTO product_type_routes (product_type, sort_order, operation_id) VALUES
    -- rigid_box
    ('rigid_box',  1,  'prepress'),
    ('rigid_box',  2,  'offset_printing'),
    ('rigid_box',  3,  'lamination'),
    ('rigid_box',  4,  'hot_foil_stamping'),
    ('rigid_box',  5,  'die_cutting'),
    ('rigid_box',  6,  'creasing'),
    ('rigid_box',  7,  'chipboard_laminating'),
    ('rigid_box',  8,  'box_assembly'),
    ('rigid_box',  9,  'quality_control'),
    ('rigid_box',  10, 'packaging'),
    -- folding_box
    ('folding_box', 1, 'prepress'),
    ('folding_box', 2, 'offset_printing'),
    ('folding_box', 3, 'lamination'),
    ('folding_box', 4, 'uv_varnishing'),
    ('folding_box', 5, 'die_cutting'),
    ('folding_box', 6, 'creasing'),
    ('folding_box', 7, 'box_assembly'),
    ('folding_box', 8, 'quality_control'),
    ('folding_box', 9, 'packaging'),
    -- card_deck
    ('card_deck', 1, 'prepress'),
    ('card_deck', 2, 'offset_printing'),
    ('card_deck', 3, 'uv_varnishing'),
    ('card_deck', 4, 'die_cutting'),
    ('card_deck', 5, 'card_cutting'),
    ('card_deck', 6, 'quality_control'),
    ('card_deck', 7, 'packaging'),
    -- rulebook_thin
    ('rulebook_thin', 1, 'prepress'),
    ('rulebook_thin', 2, 'offset_printing'),
    ('rulebook_thin', 3, 'saddle_stitching'),
    ('rulebook_thin', 4, 'quality_control'),
    ('rulebook_thin', 5, 'packaging'),
    -- rulebook_thick
    ('rulebook_thick', 1, 'prepress'),
    ('rulebook_thick', 2, 'offset_printing'),
    ('rulebook_thick', 3, 'lamination'),
    ('rulebook_thick', 4, 'perfect_binding'),
    ('rulebook_thick', 5, 'quality_control'),
    ('rulebook_thick', 6, 'packaging'),
    -- insert
    ('insert', 1, 'prepress'),
    ('insert', 2, 'digital_printing'),
    ('insert', 3, 'die_cutting'),
    ('insert', 4, 'quality_control'),
    ('insert', 5, 'packaging');
