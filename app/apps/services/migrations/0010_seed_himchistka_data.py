"""
Data migration: добавляем основную услугу «Химчистка» (is_extra_only=True)
и все позиции прайс-листа доп. услуг из фото.
"""
from django.db import migrations


# ──────────────────────────────────────────────────────────
#  Данные
# ──────────────────────────────────────────────────────────

MAIN_SERVICE = {
    'name': 'Химчистка мебели',
    'description': (
        'Профессиональная химчистка мягкой мебели: диваны, кресла, матрасы, подушки. '
        'Минимальный заказ — 3 500 сом. '
        'Точную стоимость мастер скажет на месте.'
    ),
    'price': 3500,
    'is_extra_only': True,
    'is_active': True,
    'senior_cleaner_salary': 0,
    'senior_cleaner_bonus': 0,
    'room_count': 1,
    'senior_cleaner_count': 1,
    'cleaner_count': 1,
    'checklist': [],
}

EXTRA_SERVICES = [
    # Левая колонка прайса
    {'name': 'Пуф 30×30',            'price': 350,  'description': ''},
    {'name': 'Пуф 80×80',            'price': 450,  'description': ''},
    {'name': 'Диванная подушка',      'price': 200,  'description': 'От 200 до 250 сом — точную цену скажет мастер'},
    {'name': 'Изголовье кровати',     'price': 1000, 'description': 'От 1 000 до 1 200 сом — точную цену скажет мастер'},
    {'name': 'Детский матрас',        'price': 1000, 'description': 'От 1 000 до 1 100 сом — точную цену скажет мастер'},
    {'name': '1-спальный матрас',     'price': 1400, 'description': 'От 1 400 до 1 600 сом'},
    {'name': '1.5-спальный матрас',   'price': 1700, 'description': 'От 1 700 до 1 900 сом'},
    {'name': '2-спальный матрас',     'price': 2000, 'description': 'От 2 000 до 2 300 сом'},
    # Правая колонка прайса
    {'name': 'Кресло',                'price': 700,  'description': 'От 700 до 1 000 сом — зависит от типа'},
    {'name': 'Диван 2-местный',       'price': 1800, 'description': ''},
    {'name': 'Диван 3-местный',       'price': 2400, 'description': ''},
    {'name': 'Угловой диван',         'price': 2700, 'description': 'От 2 700 до 3 000 сом'},
    {'name': 'Большой угловой диван', 'price': 3600, 'description': 'От 3 600 до 4 000 сом. +800 сом за раскладную часть'},
]


def add_data(apps, schema_editor):
    Service = apps.get_model('services', 'Service')
    ExtraService = apps.get_model('services', 'ExtraService')

    # ── Основная услуга «Химчистка» ──────────────────────────
    if not Service.objects.filter(name='Химчистка мебели').exists():
        Service.objects.create(**MAIN_SERVICE)

    # ── Доп. услуги (прайс-лист) ─────────────────────────────
    for item in EXTRA_SERVICES:
        ExtraService.objects.get_or_create(
            name=item['name'],
            defaults={
                'price': item['price'],
                'description': item.get('description', ''),
                'is_active': True,
            }
        )


def remove_data(apps, schema_editor):
    Service = apps.get_model('services', 'Service')
    ExtraService = apps.get_model('services', 'ExtraService')

    Service.objects.filter(name='Химчистка мебели').delete()
    names = [item['name'] for item in EXTRA_SERVICES]
    ExtraService.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0009_service_is_extra_only'),
    ]

    operations = [
        migrations.RunPython(add_data, remove_data),
    ]
