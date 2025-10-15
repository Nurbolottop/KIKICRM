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


class ServiceTaskTemplateInline(admin.TabularInline):
    model = cms_models.ServiceTaskTemplate
    extra = 1
    fields = ('description', 'order')
    verbose_name = 'Шаблон задачи'
    verbose_name_plural = 'Шаблоны задач (автоматически добавляются при создании заказа)'


@admin.register(cms_models.Services)
class ServicesAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'order', 'created_at', 'updated_at', 'image_preview')
    list_display_links = ('title',)
    search_fields = ('title', 'description')
    list_filter = ('created_at', 'updated_at')
    ordering = ('order', 'title')
    readonly_fields = ('image_preview',)
    inlines = [ServiceTaskTemplateInline]

    fields = (
        'title',
        'price',
        'description',
        'image',
        'image_preview',
        'order',
    )

    def image_preview(self, obj):
        if getattr(obj, 'image', None):
            try:
                return format_html('<img src="{}" style="height:60px; border-radius:4px;"/>', obj.image.url)
            except Exception:
                return '—'
        return '—'
    image_preview.short_description = 'Превью'


@admin.register(cms_models.ServiceTaskTemplate)
class ServiceTaskTemplateAdmin(admin.ModelAdmin):
    list_display = ('service', 'description', 'order')
    list_filter = ('service',)
    search_fields = ('description', 'service__title')
    ordering = ('service', 'order')
