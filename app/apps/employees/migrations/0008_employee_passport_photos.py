from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0007_employee_contract_file_employee_passport_expiry_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='passport_photo_front',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='employees/passports/',
                verbose_name='Фото паспорта (передняя сторона)',
                help_text='Фото передней стороны паспорта/ID карты',
            ),
        ),
        migrations.AddField(
            model_name='employee',
            name='passport_photo_back',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='employees/passports/',
                verbose_name='Фото паспорта (задняя сторона)',
                help_text='Фото задней стороны паспорта/ID карты',
            ),
        ),
    ]
