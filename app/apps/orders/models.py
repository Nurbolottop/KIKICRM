from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.common.models import TimeStampedModel


class OrderStatus(models.TextChoices):
    """Главный статус заказа (рассчитывается автоматически)."""
    PROCESSING = 'PROCESSING', 'В обработке'
    IN_WORK = 'IN_WORK', 'В работе'
    ON_REVIEW = 'ON_REVIEW', 'На проверке'
    CANCELLED = 'CANCELLED', 'Отклонён'
    COMPLETED = 'COMPLETED', 'Успешно завершён'


class Order(TimeStampedModel):
    """Модель заказа в CRM KIKI."""

    # Категория заказа
    class OrderCategory(models.TextChoices):
        """Категория заказа: новый или повторный."""
        NEW = 'NEW', 'Новый заказ'
        REPEAT = 'REPEAT', 'Повторный заказ'

    # Тип помещения (с иконками как на скриншоте)
    class PropertyType(models.TextChoices):
        NOT_SPECIFIED = 'NOT_SPECIFIED', 'Не указан'
        APARTMENT = 'APARTMENT', 'Квартира'
        HOUSE = 'HOUSE', 'Дом'
        LAND = 'LAND', 'Земельный участок'
        BUSINESS = 'BUSINESS', 'Бизнес помещение'
        OFFICE = 'OFFICE', 'Офис'
        OTHER = 'OTHER', 'Другое'

    # Статусы для оператора и менеджера
    class OperatorStatus(models.TextChoices):
        """Статус оператора."""
        IN_PROGRESS = 'IN_PROGRESS', 'В обработке'
        TRANSFERRED = 'TRANSFERRED', 'Передано'
        REJECTED = 'REJECTED', 'Отклонено'
        SUCCESS = 'SUCCESS', 'Успешно'

    class ManagerStatus(models.TextChoices):
        """Статус менеджера."""
        WAITING = 'WAITING', 'В ожидании'
        IN_PROGRESS = 'IN_PROGRESS', 'В обработке'
        PROCESS = 'PROCESS', 'В процессе'
        REVIEW = 'REVIEW', 'В проверке'
        DELIVERED = 'DELIVERED', 'Сдано'
        REJECTED = 'REJECTED', 'Отклонено'

    class SeniorCleanerStatus(models.TextChoices):
        """Статус старшего клинера."""
        WAITING = 'WAITING', 'В ожидании'
        ACCEPTED = 'ACCEPTED', 'Принял'
        WORKING = 'WORKING', 'В работе'
        SENT_FOR_REVIEW = 'SENT_FOR_REVIEW', 'Отправлено на проверку'
        REJECTED = 'REJECTED', 'Отклонено'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Низкий'
        NORMAL = 'NORMAL', 'Обычный'
        HIGH = 'HIGH', 'Высокий'
        URGENT = 'URGENT', 'Срочный'

    # Канал привлечения
    class LeadChannel(models.TextChoices):
        PHONE = 'PHONE', 'Телефон'
        WEBSITE = 'WEBSITE', 'Сайт'
        INSTAGRAM = 'INSTAGRAM', 'Instagram'
        TELEGRAM = 'TELEGRAM', 'Telegram'
        WHATSAPP = 'WHATSAPP', 'WhatsApp'
        REFERRAL = 'REFERRAL', 'Рекомендация'
        OTHER = 'OTHER', 'Другое'

    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='Клиент'
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='Услуга',
        blank=True,
        null=True
    )

    # Категория и тип
    category = models.CharField(
        'Категория заказа',
        max_length=30,
        choices=OrderCategory.choices,
        default=OrderCategory.NEW
    )
    property_type = models.CharField(
        'Тип помещения',
        max_length=30,
        choices=PropertyType.choices,
        default=PropertyType.NOT_SPECIFIED
    )

    # Адрес и время
    address = models.CharField(
        'Адрес выполнения',
        max_length=255
    )
    scheduled_date = models.DateField(
        'Дата уборки'
    )
    scheduled_time = models.TimeField(
        'Время уборки'
    )

    # Параметры помещения
    rooms_count = models.PositiveIntegerField(
        'Количество комнат',
        default=1,
        null=True,
        blank=True
    )
    area = models.DecimalField(
        'Площадь (м²)',
        max_digits=6,
        decimal_places=2,
        default=0,
        null=True,
        blank=True
    )
    windows_count = models.PositiveIntegerField(
        'Количество окон',
        default=0,
        blank=True,
        null=True,
        help_text='0 — это валидное значение (нет окон)'
    )
    bathrooms_count = models.PositiveIntegerField(
        'Количество санузлов',
        default=1,
        null=True,
        blank=True
    )

    # Дополнительно
    after_renovation = models.BooleanField(
        'После ремонта',
        default=False
    )
    work_scope = models.TextField(
        'Объём работы',
        blank=True,
        help_text='Пример: 50м², 2 комнаты, кухня'
    )

    # Цена и статус
    preliminary_price = models.DecimalField(
        'Предварительная стоимость',
        max_digits=10,
        decimal_places=2,
        default=0,
        null=True,
        blank=True
    )
    price = models.DecimalField(
        'Итоговая цена',
        max_digits=10,
        decimal_places=2,
        default=0,
        null=True,
        blank=True
    )
    status = models.CharField(
        'Статус заказа',
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PROCESSING,
        db_index=True,
        help_text='Главный статус (рассчитывается автоматически)'
    )

    # Статусы оператора и менеджера
    operator_status = models.CharField(
        'Статус оператора',
        max_length=20,
        choices=OperatorStatus.choices,
        default=OperatorStatus.IN_PROGRESS
    )
    manager_status = models.CharField(
        'Статус менеджера',
        max_length=20,
        choices=ManagerStatus.choices,
        default=ManagerStatus.WAITING
    )
    senior_cleaner_status = models.CharField(
        'Статус старшего клинера',
        max_length=20,
        choices=SeniorCleanerStatus.choices,
        default=SeniorCleanerStatus.WAITING
    )
    handed_to_manager = models.BooleanField(
        'Передано менеджеру',
        default=False,
        help_text='Галочка - передано менеджеру, пусто - не передано'
    )
    handed_to_manager_at = models.DateTimeField(
        'Дата передачи менеджеру',
        null=True,
        blank=True
    )

    # Приоритет
    priority = models.CharField(
        'Приоритет',
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL
    )
    lead_channel = models.CharField(
        'Канал привлечения',
        max_length=20,
        choices=LeadChannel.choices,
        default=LeadChannel.PHONE,
        blank=True
    )
    
    # Поле для оператора - сумма предоплаты
    prepayment_amount = models.DecimalField(
        'Сумма предоплаты',
        max_digits=10,
        decimal_places=2,
        default=0,
        null=True,
        blank=True,
        help_text='Указывается оператором при создании заказа'
    )

    # Комментарий
    comment = models.TextField(
        'Заметки',
        blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_orders',
        verbose_name='Кто создал'
    )
    assigned_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_orders',
        verbose_name='Назначенный менеджер'
    )
    
    # Order Closing Workflow Fields
    # Senior Cleaner marks as ready for review
    ready_for_review_at = models.DateTimeField(
        'Готов к проверке (дата)',
        null=True,
        blank=True,
        help_text='Когда Senior Cleaner передал заказ менеджеру для проверки'
    )
    ready_for_review_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders_marked_ready',
        verbose_name='Готов к проверке (кто)'
    )
    
    # Manager closes order
    manager_closed_at = models.DateTimeField(
        'Закрыт менеджером (дата)',
        null=True,
        blank=True,
        help_text='Когда менеджер закрыл заказ со своей стороны'
    )
    
    # Operator closes order
    operator_closed_at = models.DateTimeField(
        'Закрыт оператором (дата)',
        null=True,
        blank=True,
        help_text='Когда оператор закрыл заказ со своей стороны'
    )
    
    # Transfer to Manager Workflow Fields
    # Operator transfers order to manager for processing
    transferred_to_manager = models.BooleanField(
        'Передан менеджеру',
        default=False,
        help_text='Оператор передал заказ менеджеру для обработки'
    )
    transferred_to_manager_at = models.DateTimeField(
        'Передан менеджеру (дата)',
        null=True,
        blank=True,
        help_text='Когда оператор передал заказ менеджеру'
    )
    transferred_to_manager_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders_transferred_to_manager',
        verbose_name='Передан менеджеру (кем)'
    )
    
    order_code = models.CharField(
        'Код заказа',
        max_length=30,
        unique=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-scheduled_date', '-scheduled_time']

    def __str__(self):
        return f'{self.order_code} - {self.client.get_full_name()}'

    def save(self, *args, **kwargs):
        """Генерация order_code и автоматический расчёт главного статуса."""
        # Генерация order_code
        if not self.order_code:
            last_order = Order.objects.order_by('-id').first()
            if last_order:
                try:
                    last_number = int(last_order.order_code.split('-')[1])
                    new_number = last_number + 1
                except (IndexError, ValueError):
                    new_number = Order.objects.count() + 1
            else:
                new_number = 1
            self.order_code = f'KIKI-{new_number:04d}'
        
        # Автоматический расчёт главного статуса
        self._recalculate_main_status()
        
        super().save(*args, **kwargs)
    
    def _recalculate_main_status(self):
        """Пересчитывает главный статус заказа на основе внутренних статусов."""
        # Если оператор отклонил - заказ отклонён
        if self.operator_status == self.OperatorStatus.REJECTED:
            self.status = OrderStatus.CANCELLED
            return
        
        # Если оператор в обработке - заказ в обработке
        if self.operator_status == self.OperatorStatus.IN_PROGRESS:
            self.status = OrderStatus.PROCESSING
            return
        
        # Если менеджер в обработке или процессе - заказ в работе
        if self.manager_status in [
            self.ManagerStatus.IN_PROGRESS,
            self.ManagerStatus.PROCESS
        ]:
            self.status = OrderStatus.IN_WORK
            return
        
        # Если менеджер в проверке - заказ на проверке
        if self.manager_status == self.ManagerStatus.REVIEW:
            self.status = OrderStatus.ON_REVIEW
            return
        
        # Если менеджер сдал и оператор подтвердил - заказ завершён
        if (self.manager_status == self.ManagerStatus.DELIVERED and 
            self.operator_status == self.OperatorStatus.SUCCESS):
            self.status = OrderStatus.COMPLETED
            return

    def get_operator_status_display_ru(self):
        """Возвращает русское название статуса оператора."""
        mapping = {
            'IN_PROGRESS': 'В обработке',
            'TRANSFERRED': 'Передано',
            'REJECTED': 'Отклонено',
            'SUCCESS': 'Успешно',
            'PROCESSING': 'В обработке',  # fallback для старых данных
        }
        return mapping.get(self.operator_status, self.operator_status)

    def get_manager_status_display_ru(self):
        """Возвращает русское название статуса менеджера."""
        mapping = {
            'WAITING': 'В ожидании',
            'PENDING': 'В ожидании',  # fallback для старых данных
            'IN_PROGRESS': 'В обработке',
            'PROCESS': 'В процессе',
            'REVIEW': 'В проверке',
            'DELIVERED': 'Сдано',
            'REJECTED': 'Отклонено',
        }
        return mapping.get(self.manager_status, self.manager_status)

    def get_senior_cleaner_status_display_ru(self):
        """Возвращает русское название статуса старшего клинера."""
        mapping = {
            'WAITING': 'В ожидании',
            'ACCEPTED': 'Принял',
            'WORKING': 'В работе',
            'SENT_FOR_REVIEW': 'Отправлено на проверку',
            'REJECTED': 'Отклонено',
        }
        return mapping.get(self.senior_cleaner_status, self.senior_cleaner_status)


class OrderEmployee(models.Model):
    """Связующая модель для назначения сотрудников на заказ."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_employees',
        verbose_name='Заказ'
    )
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='employee_orders',
        verbose_name='Сотрудник'
    )
    role_on_order = models.CharField(
        'Роль в заказе',
        max_length=100,
        blank=True,
        help_text='Например: cleaner, senior_cleaner, trainee (стажер)'
    )
    assigned_at = models.DateTimeField(
        'Дата назначения',
        auto_now_add=True
    )
    is_confirmed = models.BooleanField(
        'Подтверждено',
        default=False
    )
    confirmed_at = models.DateTimeField(
        'Время подтверждения',
        null=True,
        blank=True
    )
    started_at = models.DateTimeField(
        'Время начала работы',
        null=True,
        blank=True
    )
    finished_at = models.DateTimeField(
        'Время завершения работы',
        null=True,
        blank=True
    )
    notes = models.TextField(
        'Заметки',
        blank=True,
        help_text='Внутренние заметки сотрудника о заказе'
    )
    
    # Refuse fields
    refused_at = models.DateTimeField(
        'Дата отказа',
        null=True,
        blank=True
    )
    
    refuse_reason = models.TextField(
        'Причина отказа',
        blank=True
    )

    class Meta:
        verbose_name = 'Назначение сотрудника'
        verbose_name_plural = 'Назначения сотрудников'
        unique_together = ['order', 'employee']
        ordering = ['-assigned_at']

    def __str__(self):
        return f'{self.order.order_code} - {self.employee}'


class PhotoType(models.TextChoices):
    """Типы фото заказа."""
    BEFORE = 'BEFORE', 'До'
    AFTER = 'AFTER', 'После'


class OrderPhoto(models.Model):
    """Модель фотографий заказа (до/после)."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name='Заказ'
    )
    uploaded_by = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='uploaded_order_photos',
        verbose_name='Загружено'
    )
    photo = models.ImageField(
        'Фото',
        upload_to='orders/photos/%Y/%m/%d/'
    )
    photo_type = models.CharField(
        'Тип фото',
        max_length=20,
        choices=PhotoType.choices,
        default=PhotoType.BEFORE
    )
    uploaded_at = models.DateTimeField(
        'Время загрузки',
        auto_now_add=True
    )
    comment = models.TextField(
        'Комментарий',
        blank=True,
        help_text='Описание или комментарий к фото'
    )

    class Meta:
        verbose_name = 'Фото заказа'
        verbose_name_plural = 'Фотографии заказов'
        ordering = ['-uploaded_at']


class OrderAttachment(models.Model):
    """Файлы и документы по заказу."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name='Заказ'
    )
    file = models.FileField(
        'Файл',
        upload_to='orders/attachments/%Y/%m/%d/'
    )
    filename = models.CharField(
        'Имя файла',
        max_length=255,
        blank=True
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_attachments',
        verbose_name='Кто загрузил'
    )
    uploaded_at = models.DateTimeField(
        'Дата загрузки',
        auto_now_add=True
    )
    comment = models.TextField(
        'Комментарий',
        blank=True,
        help_text='Описание файла'
    )

    class Meta:
        verbose_name = 'Вложение заказа'
        verbose_name_plural = 'Вложения заказа'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.filename or self.file.name} - {self.order.order_code}'

    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            self.filename = self.file.name
        super().save(*args, **kwargs)


class OrderInventoryUsage(models.Model):
    """Фактически использованный инвентарь по заказу."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='inventory_usages',
        verbose_name='Заказ'
    )
    inventory_item = models.ForeignKey(
        'inventory.InventoryItem',
        on_delete=models.PROTECT,
        related_name='order_usages',
        verbose_name='Инвентарь'
    )
    quantity = models.DecimalField(
        'Использованное количество',
        max_digits=12,
        decimal_places=3,
        default=0
    )
    note = models.CharField(
        'Примечание',
        max_length=255,
        blank=True,
        default=''
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Использование инвентаря в заказе'
        verbose_name_plural = 'Использование инвентаря в заказах'
        ordering = ['inventory_item__item_type', 'inventory_item__category__name', 'inventory_item__name']
        unique_together = ('order', 'inventory_item')

    def __str__(self):
        return f'{self.order.order_code} — {self.inventory_item.name} ({self.quantity})'


class OrderExtraService(models.Model):
    """Дополнительная услуга, прикреплённая к заказу."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_extra_services',
        verbose_name='Заказ'
    )
    extra_service = models.ForeignKey(
        'services.ExtraService',
        on_delete=models.PROTECT,
        related_name='order_usages',
        verbose_name='Доп. услуга'
    )
    quantity = models.PositiveIntegerField(
        'Количество',
        default=1,
        help_text='Количество единиц данной доп. услуги'
    )
    price_at_order = models.DecimalField(
        'Цена на момент заказа',
        max_digits=10,
        decimal_places=2,
        help_text='Фиксируется при добавлении, чтобы изменение базовой цены не влияло на старые заказы'
    )
    note = models.CharField(
        'Примечание',
        max_length=255,
        blank=True,
        default=''
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Доп. услуга в заказе'
        verbose_name_plural = 'Доп. услуги в заказах'
        ordering = ['extra_service__name']
        unique_together = ('order', 'extra_service')

    def __str__(self):
        return f'{self.order.order_code} — {self.extra_service.name} x{self.quantity}'

    @property
    def total_price(self):
        """Итоговая стоимость позиции."""
        return self.price_at_order * self.quantity


@receiver(post_save, sender=Order)
def order_completed_notification(sender, instance, created, **kwargs):
    """Отправляет уведомление при завершении заказа."""
    if not created and instance.status == OrderStatus.COMPLETED:
        from apps.notifications.services.notification_service import NotificationService
        try:
            NotificationService.order_completed(instance)
        except Exception:
            pass  # Не блокируем сохранение заказа если Telegram недоступен


class RefuseSettings(models.Model):
    """Настройки для ограничения отказов клинеров."""

    max_refuses = models.PositiveIntegerField(
        "Максимум отказов",
        default=3,
        help_text="Максимальное количество отказов за период"
    )

    period_days = models.PositiveIntegerField(
        "Период (дней)",
        default=14,
        help_text="Период в днях для подсчета отказов"
    )

    is_active = models.BooleanField(
        "Активно",
        default=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Refuse Settings"
        verbose_name_plural = "Refuse Settings"

    def __str__(self):
        return f"{self.max_refuses} refuses / {self.period_days} days"
