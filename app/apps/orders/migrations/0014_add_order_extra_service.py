from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0013_orderinventoryusage'),
        ('services', '0003_extraservice'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderExtraService',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1, help_text='Количество единиц данной доп. услуги', verbose_name='Количество')),
                ('price_at_order', models.DecimalField(decimal_places=2, help_text='Фиксируется при добавлении, чтобы изменение базовой цены не влияло на старые заказы', max_digits=10, verbose_name='Цена на момент заказа')),
                ('note', models.CharField(blank=True, default='', max_length=255, verbose_name='Примечание')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('extra_service', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='order_usages', to='services.extraservice', verbose_name='Доп. услуга')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_extra_services', to='orders.order', verbose_name='Заказ')),
            ],
            options={
                'verbose_name': 'Доп. услуга в заказе',
                'verbose_name_plural': 'Доп. услуги в заказах',
                'ordering': ['extra_service__name'],
                'unique_together': {('order', 'extra_service')},
            },
        ),
    ]
