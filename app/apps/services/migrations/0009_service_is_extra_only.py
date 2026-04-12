from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0008_remove_service_inventory_items_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='is_extra_only',
            field=models.BooleanField(
                default=False,
                verbose_name='Только доп. услуга',
                help_text=(
                    'Включите, если услуга не требует данных по помещению '
                    '(например: химчистка мебели, мытьё окон, уборка балкона). '
                    'При выборе такой услуги в заказе поля «Тип помещения», '
                    '«Комнаты», «Площадь», «Санузлы» и «После ремонта» будут скрыты.'
                )
            ),
        ),
    ]
