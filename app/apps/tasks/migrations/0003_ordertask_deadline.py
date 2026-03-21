from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0002_alter_ordertask_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordertask',
            name='deadline',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Дедлайн'),
        ),
    ]
