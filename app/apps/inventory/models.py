from django.db import models
from django.db.models import F
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone

User = get_user_model()


class Product(models.Model):
    """Товар/инвентарь для уборки"""
    class Unit(models.TextChoices):
        PIECE = "PIECE", "шт"
        LITER = "LITER", "л"
        ML = "ML", "мл"
        KG = "KG", "кг"
        GRAM = "GRAM", "г"
        METER = "METER", "м"
        CM = "CM", "см"
        PACK = "PACK", "упаковка"
        SET = "SET", "комплект"
    
    class Category(models.TextChoices):
        CLEANING = "CLEANING", "Моющие средства"
        DISINFECTANT = "DISINFECTANT", "Дезинфицирующие средства"
        EQUIPMENT = "EQUIPMENT", "Оборудование"
        TOOLS = "TOOLS", "Инструменты"
        CONSUMABLES = "CONSUMABLES", "Расходники"
        UNIFORM = "UNIFORM", "Униформа"
        OTHER = "OTHER", "Прочее"
    
    name = models.CharField(max_length=200, verbose_name="Название")
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.CLEANING,
        verbose_name="Категория"
    )
    unit = models.CharField(
        max_length=20,
        choices=Unit.choices,
        default=Unit.PIECE,
        verbose_name="Единица измерения"
    )
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    photo = models.ImageField(upload_to="inventory/products/", blank=True, null=True, verbose_name="Фото")
    
    # Для отслеживания минимального остатка
    min_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Минимальный остаток"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    def __str__(self):
        return f"{self.name} ({self.get_unit_display()})"
    
    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["category", "name"]


class Stock(models.Model):
    """Остатки на складе"""
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="stock",
        verbose_name="Товар"
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Количество"
    )
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")
    
    def __str__(self):
        return f"{self.product.name}: {self.quantity} {self.product.get_unit_display()}"
    
    @property
    def is_low_stock(self):
        """Низкий остаток"""
        return self.quantity <= self.product.min_quantity
    
    class Meta:
        verbose_name = "Остаток"
        verbose_name_plural = "Остатки"


class StockMovement(models.Model):
    """Движение товаров (приход/расход)"""
    class MovementType(models.TextChoices):
        INCOMING = "INCOMING", "Приход"
        OUTGOING = "OUTGOING", "Расход"
    
    class Reason(models.TextChoices):
        PURCHASE = "PURCHASE", "Закупка"
        RETURN = "RETURN", "Возврат"
        ORDER_ISSUE = "ORDER_ISSUE", "Выдача на заказ"
        WRITE_OFF = "WRITE_OFF", "Списание"
        INVENTORY = "INVENTORY", "Инвентаризация"
        ADJUSTMENT = "ADJUSTMENT", "Корректировка"
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="movements",
        verbose_name="Товар"
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices,
        verbose_name="Тип движения"
    )
    reason = models.CharField(
        max_length=20,
        choices=Reason.choices,
        verbose_name="Причина"
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Количество"
    )
    
    # Связь с заказом (для выдачи на заказ)
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
        verbose_name="Заказ"
    )
    
    # Кто провёл операцию
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Кем выполнено"
    )
    
    notes = models.TextField(blank=True, null=True, verbose_name="Примечания")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата операции")
    
    def __str__(self):
        direction = "+" if self.movement_type == self.MovementType.INCOMING else "-"
        return f"{self.product.name} {direction}{self.quantity} ({self.get_reason_display()}))"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Обновляем остаток
        if is_new:
            stock, _ = Stock.objects.get_or_create(product=self.product)
            if self.movement_type == self.MovementType.INCOMING:
                stock.quantity += self.quantity
            else:
                stock.quantity -= self.quantity
            stock.save()
    
    class Meta:
        verbose_name = "Движение товара"
        verbose_name_plural = "Движения товаров"
        ordering = ["-created_at"]


class InventoryCheck(models.Model):
    """Инвентаризация"""
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "В процессе"
        COMPLETED = "COMPLETED", "Завершена"
        CANCELLED = "CANCELLED", "Отменена"
    
    name = models.CharField(max_length=200, verbose_name="Название инвентаризации")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
        verbose_name="Статус"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Примечания")
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inventory_checks_created",
        verbose_name="Кем создана"
    )
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_checks_completed",
        verbose_name="Кем завершена"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата завершения")
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def complete(self, user):
        """Завершить инвентаризацию"""
        self.status = self.Status.COMPLETED
        self.completed_by = user
        self.completed_at = timezone.now()
        self.save()
    
    @property
    def total_items(self):
        return self.items.count()
    
    @property
    def discrepancies_count(self):
        return self.items.exclude(actual_quantity=F("expected_quantity")).count()
    
    class Meta:
        verbose_name = "Инвентаризация"
        verbose_name_plural = "Инвентаризации"
        ordering = ["-created_at"]


class InventoryCheckItem(models.Model):
    """Позиция инвентаризации"""
    inventory_check = models.ForeignKey(
        InventoryCheck,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Инвентаризация"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="Товар"
    )
    expected_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Ожидаемое количество"
    )
    actual_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Фактическое количество"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Примечания")
    
    @property
    def discrepancy(self):
        return self.actual_quantity - self.expected_quantity
    
    def __str__(self):
        return f"{self.product.name}: ожидалось {self.expected_quantity}, факт {self.actual_quantity}"
    
    class Meta:
        verbose_name = "Позиция инвентаризации"
        verbose_name_plural = "Позиции инвентаризации"
        unique_together = ["inventory_check", "product"]


class WriteOff(models.Model):
    """Списание товара"""
    class Reason(models.TextChoices):
        EXPIRED = "EXPIRED", "Просроченный срок годности"
        DAMAGED = "DAMAGED", "Повреждение"
        DEFECT = "DEFECT", "Брак"
        LOSS = "LOSS", "Утрата"
        OTHER = "OTHER", "Иное"
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="write_offs",
        verbose_name="Товар"
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Количество"
    )
    reason = models.CharField(
        max_length=20,
        choices=Reason.choices,
        verbose_name="Причина списания"
    )
    reason_other = models.TextField(
        blank=True,
        null=True,
        verbose_name="Описание причины (если иное)"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Примечания")
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Кем списано"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата списания")
    
    def __str__(self):
        return f"{self.product.name} -{self.quantity} ({self.get_reason_display()})"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Автоматически создаём движение и обновляем остаток
        if is_new:
            StockMovement.objects.create(
                product=self.product,
                movement_type=StockMovement.MovementType.OUTGOING,
                reason=StockMovement.Reason.WRITE_OFF,
                quantity=self.quantity,
                created_by=self.created_by,
                notes=f"Списание: {self.get_reason_display()}. {self.notes or ''}"
            )
    
    class Meta:
        verbose_name = "Списание"
        verbose_name_plural = "Списания"
        ordering = ["-created_at"]
