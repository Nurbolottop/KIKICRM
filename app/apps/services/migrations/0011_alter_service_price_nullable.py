from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0010_seed_himchistka_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='price',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Оставьте пустым если цена считается на месте (напр. Химчистка)',
                max_digits=10,
                null=True,
                verbose_name='Цена',
            ),
        ),
    ]
