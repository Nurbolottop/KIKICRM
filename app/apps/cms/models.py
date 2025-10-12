from django.db import models
from django_resized.forms import ResizedImageField
from ckeditor_uploader.fields import RichTextUploadingField

# Create your models here.
class Settings(models.Model):
    title = models.CharField(
        max_length=100,
        verbose_name='Название сайта'
    )
    description = models.TextField(
        verbose_name='Описание сайта'
    )
    logo = ResizedImageField(
        force_format="WEBP", 
        quality=100, 
        upload_to='logo/', 
        verbose_name="Логотип",
        null=True, blank=True
    )
    icon = ResizedImageField(
        force_format="WEBP", 
        quality=100, 
        upload_to='icon/', 
        verbose_name="Иконка",
        null=True, blank=True
    )
    locate = models.CharField(
        max_length=100,
        verbose_name='Адрес'
    )
    email = models.EmailField(
        verbose_name='Email'
    )
    phone = models.CharField(
        max_length=100,
        verbose_name='Телефон'
    )
    work_schedule = models.CharField(
        max_length=100,
        verbose_name='Режим работы'
    )
    whatsapp = models.URLField(
        verbose_name='Whatsapp'
    )
    telegram = models.URLField(
        verbose_name='Telegram'
    )
    instagram = models.URLField(
        verbose_name='Instagram'
    )  
    facebook = models.URLField(
        verbose_name='Facebook'
    )
    class Meta:
        verbose_name = '1) Настройки'
        verbose_name_plural = '1) Настройки'
    def __str__(self):
        return self.title


class Services(models.Model):
    title = models.CharField(
        max_length=100,
        verbose_name='Название услуги'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена'
    )
    description = RichTextUploadingField(
        verbose_name='Описание Услуги'
    )
    image = ResizedImageField(
        force_format="WEBP", 
        quality=100, 
        upload_to='services/', 
        verbose_name="Изображение услуги",
        null=True, blank=True
    )
    order = models.IntegerField(
        verbose_name='Порядок',
        default=0
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    class Meta:
        verbose_name = '2) Услуги'
        verbose_name_plural = '2) Услуги'
    def __str__(self):
        return self.title