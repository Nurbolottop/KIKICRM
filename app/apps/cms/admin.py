from django.contrib import admin
from apps.cms import models as cms_models

# Register your models here.

@admin.register(cms_models.Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ('title', 'email', 'phone', 'work_schedule')
    list_display_links = ('title',)
    search_fields = ('title', 'description', 'email', 'phone')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'logo','icon')
        }),
        ('Контактная информация', {
            'fields': ('email', 'phone', 'work_schedule','locate')
        }),
        ('Социальные сети', {
            'fields': ('whatsapp', 'telegram', 'instagram', 'facebook'),
            'classes': ('collapse',)
        }),
    )


class ServiceTaskTemplateInline(admin.TabularInline):
    model = cms_models.ServiceTaskTemplate
    extra = 1
    fields = ('description', 'order')
    verbose_name = 'Шаблон задачи'
    verbose_name_plural = 'Шаблоны задач (автоматически добавляются при создании заказа)'


@admin.register(cms_models.Services)
class ServicesAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'created_at', 'updated_at')
    list_display_links = ('title',)
    search_fields = ('title',)
    list_filter = ('created_at', 'updated_at')
    ordering = ('order', 'title')
    inlines = [ServiceTaskTemplateInline]

    fields = (
        'title',
        'order',
    )