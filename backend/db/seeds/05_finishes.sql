-- =============================================================================
-- Seed: finishes — варіанти поверхневого оздоблення
-- =============================================================================

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
