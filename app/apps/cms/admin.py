from django.contrib import admin
from apps.cms import models as cms_models
from django.utils.html import format_html

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
