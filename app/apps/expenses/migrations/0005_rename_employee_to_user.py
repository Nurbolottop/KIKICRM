# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('expenses', '0004_remove_is_general_alter_employee'),
    ]

    operations = [
        migrations.RenameField(
            model_name='expense',
            old_name='employee',
            new_name='user',
        ),
        migrations.AlterField(
            model_name='expense',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='expenses',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Пользователь'
            ),
        ),
    ]
