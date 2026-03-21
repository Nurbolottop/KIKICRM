# Generated manually for status_changes_thread_id field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_bot', '0003_rename_group_chat_id_telegramsettings_chat_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='telegramsettings',
            name='status_changes_thread_id',
            field=models.CharField(
                blank=True,
                help_text='ID темы Telegram для уведомлений об изменении статуса заказов',
                max_length=100,
                verbose_name='ID темы изменений статуса',
            ),
        ),
    ]
