from django.db import migrations, models
import random
import string

def generate_unique_client_id():
    """Generate a unique 5-character alphanumeric ID"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

def populate_client_ids(apps, schema_editor):
    Client = apps.get_model('clients', 'Client')
    for client in Client.objects.all():
        # Generate a unique ID for each client
        while True:
            client_id = generate_unique_client_id()
            if not Client.objects.filter(client_id=client_id).exists():
                client.client_id = client_id
                client.save(update_fields=['client_id'])
                break

class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='client_id',
            field=models.CharField(blank=True, max_length=5, null=True, verbose_name='ID клиента', help_text='Уникальный 5-значный идентификатор клиента'),
        ),
        migrations.RunPython(populate_client_ids, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='client',
            name='client_id',
            field=models.CharField(max_length=5, unique=True, verbose_name='ID клиента', help_text='Уникальный 5-значный идентификатор клиента'),
        ),
    ]
