-- =============================================================================
-- Seed: product_type_routes — послідовність операцій для кожного типу продукту
-- =============================================================================

-- rigid_box — жорстка коробка (реальний цикл Dyz-Art)
INSERT INTO product_type_routes (product_type, sort_order, operation_id) VALUES
    ('rigid_box',  1,  'prepress'),
    ('rigid_box',  2,  'roll_slitting'),
    ('rigid_box',  3,  'sheet_format_cutting'),
    ('rigid_box',  4,  'offset_printing'),
    ('rigid_box',  5,  'lamination'),
    ('rigid_box',  6,  'hot_foil_stamping'),
    ('rigid_box',  7,  'uv_varnishing'),
    ('rigid_box',  8,  'chipboard_laminating'),
    ('rigid_box',  9,  'die_cutting'),
    ('rigid_box',  10, 'creasing'),
    ('rigid_box',  11, 'corner_taping'),
    ('rigid_box',  12, 'box_assembly'),
    ('rigid_box',  13, 'blank_stripping'),
    ('rigid_box',  14, 'quality_control'),
    ('rigid_box',  15, 'game_kit_assembly'),
    ('rigid_box',  16, 'shrink_wrapping'),
    ('rigid_box',  17, 'shipper_packing'),
    ('rigid_box',  18, 'palletizing');

-- folding_box — з гофруванням після УФ за цеховим порядком; кашировка зазвичай не входить
INSERT INTO product_type_routes (product_type, sort_order, operation_id) VALUES
    ('folding_box', 1,  'prepress'),
    ('folding_box', 2,  'roll_slitting'),
    ('folding_box', 3,  'sheet_format_cutting'),
    ('folding_box', 4,  'offset_printing'),
    ('folding_box', 5,  'lamination'),
    ('folding_box', 6,  'uv_varnishing'),
    ('folding_box', 7,  'corrugating'),
    ('folding_box', 8,  'die_cutting'),
    ('folding_box', 9,  'creasing'),
    ('folding_box', 10, 'box_assembly'),
    ('folding_box', 11, 'blank_stripping'),
    ('folding_box', 12, 'quality_control'),
    ('folding_box', 13, 'shrink_wrapping'),
    ('folding_box', 14, 'shipper_packing'),
    ('folding_box', 15, 'palletizing');

-- card_deck — колоди карт (цеховий цикл Dyz-Art)
INSERT INTO product_type_routes (product_type, sort_order, operation_id) VALUES
    ('card_deck',  1,  'prepress'),
    ('card_deck',  2,  'roll_slitting'),
    ('card_deck',  3,  'sheet_format_cutting'),
    ('card_deck',  4,  'offset_printing'),
    ('card_deck',  5,  'lamination'),
    ('card_deck',  6,  'card_cutting'),
    ('card_deck',  7,  'quality_control'),
    ('card_deck',  8,  'shrink_wrapping'),
    ('card_deck',  9,  'shipper_packing'),
    ('card_deck',  10, 'palletizing');

-- info_leaflet — інформаційна листівка (той самий маршрут, що й card_deck)
INSERT INTO product_type_routes (product_type, sort_order, operation_id) VALUES
    ('info_leaflet', 1,  'prepress'),
    ('info_leaflet', 2,  'roll_slitting'),
    ('info_leaflet', 3,  'sheet_format_cutting'),
    ('info_leaflet', 4,  'offset_printing'),
    ('info_leaflet', 5,  'lamination'),
    ('info_leaflet', 6,  'card_cutting'),
    ('info_leaflet', 7,  'quality_control'),
    ('info_leaflet', 8,  'shrink_wrapping'),
    ('info_leaflet', 9,  'shipper_packing'),
    ('info_leaflet', 10, 'palletizing');

-- game_board — ігрове поле (палітурний картон / кашир, цеховий цикл Dyz-Art)
INSERT INTO product_type_routes (product_type, sort_order, operation_id) VALUES
    ('game_board', 1,  'prepress'),
    ('game_board', 2,  'roll_slitting'),
    ('game_board', 3,  'sheet_format_cutting'),
    ('game_board', 4,  'offset_printing'),
    ('game_board', 5,  'lamination'),
    ('game_board', 6,  'uv_varnishing'),
    ('game_board', 7,  'chipboard_laminating'),
    ('game_board', 8,  'die_cutting'),
    ('game_board', 9,  'game_board_hand_wrapping'),
    ('game_board', 10, 'forzats_tipping'),
    ('game_board', 11, 'game_board_platen_scoring'),
    ('game_board', 12, 'game_board_platen_creasing'),
    ('game_board', 13, 'quality_control'),
    ('game_board', 14, 'shrink_wrapping'),
    ('game_board', 15, 'shipper_packing'),
    ('game_board', 16, 'palletizing');

-- rulebook_thin — тонка брошурована інструкція (скоба)
INSERT INTO product_type_routes (product_type, sort_order, operation_id) VALUES
    ('rulebook_thin', 1,  'prepress'),
    ('rulebook_thin', 2,  'sheet_format_cutting'),
    ('rulebook_thin', 3,  'offset_printing'),
    ('rulebook_thin', 4,  'rulebook_final_cutting'),
    ('rulebook_thin', 5,  'rulebook_folding_creasing'),
    ('rulebook_thin', 6,  'saddle_stitching'),
    ('rulebook_thin', 7,  'quality_control'),
    ('rulebook_thin', 8,  'shrink_wrapping'),
    ('rulebook_thin', 9,  'shipper_packing'),
    ('rulebook_thin', 10, 'palletizing');

-- rulebook_thick — товста інструкція (клейове скріплення)
INSERT INTO product_type_routes (product_type, sort_order, operation_id) VALUES
    ('rulebook_thick', 1,  'prepress'),
    ('rulebook_thick', 2,  'sheet_format_cutting'),
    ('rulebook_thick', 3,  'offset_printing'),
    ('rulebook_thick', 4,  'lamination'),
    ('rulebook_thick', 5,  'rulebook_final_cutting'),
    ('rulebook_thick', 6,  'rulebook_folding_creasing'),
    ('rulebook_thick', 7,  'perfect_binding'),
    ('rulebook_thick', 8,  'quality_control'),
    ('rulebook_thick', 9,  'shrink_wrapping'),
    ('rulebook_thick', 10, 'shipper_packing'),
    ('rulebook_thick', 11, 'palletizing');

-- insert — картонна вкладка (малий тираж, цифровий друк)
INSERT INTO product_type_routes (product_type, sort_order, operation_id) VALUES
    ('insert', 1, 'prepress'),
    ('insert', 2, 'digital_printing'),
    ('insert', 3, 'die_cutting'),
    ('insert', 4, 'quality_control'),
    ('insert', 5, 'packaging');
