# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0003_remove_expense_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='expense',
            name='is_general',
        ),
        migrations.AlterField(
            model_name='expense',
            name='employee',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='expenses',
                to='employees.employee',
                verbose_name='Сотрудник'
            ),
        ),
    ]
