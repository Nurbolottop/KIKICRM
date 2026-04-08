# Generated manually for ClientReview model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0004_clientnote'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('description', models.TextField(help_text='Текст отзыва клиента', verbose_name='Описание отзыва')),
                ('photo', models.ImageField(blank=True, help_text='Фотография от клиента (опционально)', null=True, upload_to='client_reviews/', verbose_name='Фотография')),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='client_reviews', to=settings.AUTH_USER_MODEL, verbose_name='Автор')),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='clients.client', verbose_name='Клиент')),
            ],
            options={
                'verbose_name': 'Отзыв клиента',
                'verbose_name_plural': 'Отзывы клиентов',
                'ordering': ['-created_at'],
            },
        ),
    ]
