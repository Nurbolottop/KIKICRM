from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0004_service_salary_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='senior_cleaner_bonus',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Доп. оплата ст. клинеру'),
        ),
    ]
