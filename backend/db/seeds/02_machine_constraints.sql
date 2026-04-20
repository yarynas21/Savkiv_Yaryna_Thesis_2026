-- =============================================================================
-- Seed: machine_constraints — глобальні обмеження виробництва (key/value)
-- =============================================================================

INSERT INTO machine_constraints (key, value) VALUES
    ('foil_stamping_requires_cliche',     'true'),
    ('foil_cliche_lead_time_days',        '5'),
    ('die_cutting_requires_die',          'true'),
    ('die_lead_time_days',                '2'),
    ('min_offset_run',                    '100'),
    ('digital_max_run',                   '1000'),
    ('soft_touch_requires_heat_press',    'true'),
    ('card_min_gsm',                      '280'),
    ('card_max_gsm',                      '360'),
    ('lamination_max_width_mm',           '700'),
    ('offset_sm102_max_sheet_mm',         '1040x730'),
    ('roll_slitting_skip_if_sheet_stock', 'true');
