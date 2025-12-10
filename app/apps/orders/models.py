from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.clients import models as clients_models
from apps.cms import models as cms_models

class Order(models.Model):
    # --- Статусы ---
    class OperatorStatus(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "В обработке"
        ACCEPTED = "ACCEPTED", "Принято"
        DECLINED = "DECLINED", "Отклонено оператором"

    class ManagerStatus(models.TextChoices):
        ASSIGNED = "ASSIGNED", "Назначен"
        IN_PROGRESS = "IN_PROGRESS", "В работе"
        PENDING_REVIEW = "PENDING_REVIEW", "На проверке"
        COMPLETED = "COMPLETED", "Завершён"
        DECLINED = "DECLINED", "Отклонено"
    
    class SeniorCleanerStatus(models.TextChoices):
        ASSIGNED = "ASSIGNED", "Назначен"
        ACCEPTED = "ACCEPTED", "Принят"
        IN_PROGRESS = "IN_PROGRESS", "В работе"
        PENDING_REVIEW = "PENDING_REVIEW", "На проверке менеджера"
        COMPLETED = "COMPLETED", "Завершён"
        DECLINED = "DECLINED", "Отказался"

    class Priority(models.TextChoices):
        NORMAL = "NORMAL", "Обычный"
        URGENT = "URGENT", "Срочный"
    
    # Тип помещения
    class PropertyType(models.TextChoices):
        APARTMENT = "APARTMENT", "Квартира"
        HOUSE = "HOUSE", "Дом"
        LAND = "LAND", "Земельный участок"
        BUSINESS = "BUSINESS", "Бизнес помещение"
        OFFICE = "OFFICE", "Офис"
        OTHER = "OTHER", "Другое"

    # Канал привлечения (верхний уровень)
    class Channel(models.TextChoices):
        WEBSITE = "WEBSITE", "Сайт"
        INSTAGRAM = "INSTAGRAM", "Instagram"
        TELEGRAM = "TELEGRAM", "Telegram"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        PHONE = "PHONE", "Звонок"
        REFERRAL = "REFERRAL", "Рекомендация"
        ADS = "ADS", "Реклама"
        OTHER = "OTHER", "Другое"

    # Источник обращения (зависит от канала — ограничить на фронтенде)
    class Source(models.TextChoices):
        WEBSITE_FORM = "WEBSITE_FORM", "Форма на сайте"
        WEBSITE_CHAT = "WEBSITE_CHAT", "Чат на сайте"
        INSTAGRAM_DM = "INSTAGRAM_DM", "Instagram Direct"
        INSTAGRAM_BIO = "INSTAGRAM_BIO", "Ссылка в профиле"
        TELEGRAM_BOT = "TELEGRAM_BOT", "Telegram-бот"
        TELEGRAM_DM = "TELEGRAM_DM", "Личные сообщения Telegram"
        WHATSAPP_CHAT = "WHATSAPP_CHAT", "Чат WhatsApp"
        PHONE_CALL = "PHONE_CALL", "Телефонный звонок"
        REFERRAL_FRIEND = "REFERRAL_FRIEND", "Рекомендация (знакомые)"
        REFERRAL_PARTNER = "REFERRAL_PARTNER", "Рекомендация (партнёры)"
        GOOGLE_ADS = "GOOGLE_ADS", "Google Ads"
        YANDEX_ADS = "YANDEX_ADS", "Яндекс Реклама"
        SOCIAL_ADS = "SOCIAL_ADS", "Реклама в соцсетях"
        OTHER = "OTHER", "Другое"

    # --- Поля заказа (Оператор) ---
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=20, unique=True, editable=False, verbose_name="Код заказа")

    client = models.ForeignKey(clients_models.Client, on_delete=models.CASCADE, related_name="orders", verbose_name="Клиент")
    category = models.CharField(
        max_length=50,
        choices=[("NEW", "Новый"), ("REPEATED", "Повторный")],
        verbose_name="Категория заказа"
    )
    service = models.ForeignKey(
        cms_models.Services,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="Услуга",
        null=True,
        blank=True,
    )
    address = models.TextField(verbose_name="Адрес выполнения")
    property_type = models.CharField(
        max_length=20,
        choices=PropertyType.choices,
        null=True,
        blank=True,
        verbose_name="Тип помещения"
    )
    date_time = models.DateTimeField(verbose_name="Дата и время уборки")

    estimated_cost = models.PositiveIntegerField(null=True, blank=True, verbose_name="Предварительная стоимость")
    estimated_area = models.CharField(
        max_length=100,
        null=True, 
        blank=True, 
        verbose_name="Объём работы",
        help_text="Например: 50 м², 3 комнаты, 5 окон"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Заметки клиента")

    channel = models.CharField(
        max_length=20,
        choices=Channel.choices,
        null=True,
        blank=True,
        verbose_name="Канал привлечения",
    )
    source = models.CharField(
        max_length=30,
        choices=Source.choices,
        null=True,
        blank=True,
        verbose_name="Источник обращения",
    )
    contact_time = models.DateTimeField(
    default=timezone.now,
    verbose_name="Время обращения"
)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL, verbose_name="Приоритет")

    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="orders_operator", verbose_name="Оператор"
    )
    status_operator = models.CharField(
        max_length=20,
        choices=OperatorStatus.choices,
        default=OperatorStatus.IN_PROGRESS,
        null=True,
        blank=True,
        verbose_name="Статус (оператор)"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    # --- Поля заказа (Менеджер) ---
    final_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Итоговая стоимость")
    final_area = models.CharField(
        max_length=100,
        null=True, 
        blank=True, 
        verbose_name="Фактический объём работы",
        help_text="Например: 50 м², 3 комнаты, 5 окон"
    )

    senior_cleaner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="orders_senior", verbose_name="Старший клинер"
    )
    cleaners = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="orders_cleaners",
        blank=True, verbose_name="Клинеры"
    )
    deadline = models.DateTimeField(null=True, blank=True, verbose_name="Крайний срок выполнения")

    manager_comment = models.TextField(blank=True, null=True, verbose_name="Комментарий менеджера")
    status_manager = models.CharField(max_length=20, choices=ManagerStatus.choices, null=True, blank=True, verbose_name="Статус (менеджер)")
    
    # --- Поля старшего клинера ---
    status_senior_cleaner = models.CharField(
        max_length=20, 
        choices=SeniorCleanerStatus.choices, 
        default=SeniorCleanerStatus.ASSIGNED,
        null=True, 
        blank=True, 
        verbose_name="Статус (старший клинер)"
    )
    senior_cleaner_comment = models.TextField(blank=True, null=True, verbose_name="Комментарий старшего клинера")
    decline_reason = models.TextField(blank=True, null=True, verbose_name="Причина отказа")
    
    # --- Отслеживание работы ---
    work_started_at = models.DateTimeField(null=True, blank=True, verbose_name="Работа начата")
    work_finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Работа завершена")
    
    # --- Оценка качества ---
    quality_rating = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name="Оценка качества (1-5)",
        help_text="Оценка от 1 до 5 звёзд"
    )
    quality_comment = models.TextField(blank=True, null=True, verbose_name="Комментарий по качеству")
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата проверки")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reviewed_orders",
        verbose_name="Проверил (менеджер)"
    )

    def __str__(self):
        service_title = self.service.title if getattr(self, "service", None) else "—"
        return f"{self.code} | {self.client} | {service_title}"

    def save(self, *args, **kwargs):
        if not self.code:
            last_id = Order.objects.count() + 1
            self.code = f"KIKI-{last_id:06d}"
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]


class Task(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tasks", verbose_name="Заказ")
    cleaner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Исполнитель"
    )

    description = models.CharField(max_length=255, verbose_name="Описание задачи")
    status = models.CharField(
        max_length=20,
        choices=[
            ("IN_PROGRESS", "В работе"),
            ("PENDING_REVIEW", "На проверке"),
            ("DONE", "Готово"),
        ],
        default="IN_PROGRESS",
        verbose_name="Статус задачи"
    )
    photo_before = models.ImageField(upload_to="orders/tasks/", null=True, blank=True, verbose_name="Фото до")
    photo_after = models.ImageField(upload_to="orders/tasks/", null=True, blank=True, verbose_name="Фото после")
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий по задаче")

    def __str__(self):
        return f"{self.description} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ["status", "id"]