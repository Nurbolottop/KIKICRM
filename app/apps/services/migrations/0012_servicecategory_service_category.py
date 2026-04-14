from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0011_alter_service_price_nullable'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServiceCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Название')),
                ('color', models.CharField(
                    default='#6366f1',
                    help_text='HEX-цвет для бейджика, например #6366f1',
                    max_length=20,
                    verbose_name='Цвет (hex)',
                )),
                ('icon', models.CharField(
                    default='bi-tag',
                    help_text='Имя Bootstrap Icons класса, например bi-house или bi-sparkles',
                    max_length=50,
                    verbose_name='Bootstrap-иконка',
                )),
                ('ordering', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
            ],
            options={
                'verbose_name': 'Категория услуги',
                'verbose_name_plural': 'Категории услуг',
                'ordering': ['ordering', 'name'],
            },
        ),
        migrations.AddField(
            model_name='service',
            name='category',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='services',
                to='services.servicecategory',
                verbose_name='Категория',
            ),
        ),
    ]
