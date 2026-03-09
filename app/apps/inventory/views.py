from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from apps.cms import models as cms_models
from apps.users.models import User
from .models import Product, Stock, StockMovement, InventoryCheck, InventoryCheckItem, WriteOff
from .forms import (
    ProductForm, StockMovementForm, OrderIssueForm, 
    WriteOffForm, InventoryCheckForm, InventoryCheckItemForm
)


def _check_inventory_access(request, allowed_roles=None):
    """Проверка доступа к инвентарю"""
    if allowed_roles is None:
        allowed_roles = [User.Role.FOUNDER, User.Role.MANAGER, User.Role.OPERATOR]
    if request.user.role not in allowed_roles:
        messages.error(request, "У вас нет доступа к разделу инвентаря")
        return False
    return True


def _is_founder(user):
    return user.role == User.Role.FOUNDER


def _is_manager(user):
    return user.role == User.Role.MANAGER


def _is_operator(user):
    return user.role == User.Role.OPERATOR


# ============ ОСТАТКИ (СТОК) ============

@login_required
def stock_list(request):
    """Список остатков — доступен Founder, Manager, Operator (только просмотр)"""
    if not _check_inventory_access(request):
        return redirect("index")
    
    settings = cms_models.Settings.objects.first()
    
    # Фильтры
    category = request.GET.get("category", "")
    low_stock = request.GET.get("low_stock", "")
    search = request.GET.get("search", "")
    
    stocks = Stock.objects.select_related("product").all()
    
    if category:
        stocks = stocks.filter(product__category=category)
    if low_stock:
        stocks = [s for s in stocks if s.is_low_stock] if low_stock == "yes" else [s for s in stocks if not s.is_low_stock]
    if search:
        stocks = stocks.filter(product__name__icontains=search)
    
    return render(request, "pages/system/others/inventory/stock_list.html", {
        "settings": settings,
        "stocks": stocks,
        "category_choices": Product.Category.choices,
    })


# ============ ТОВАРЫ (PRODUCTS) ============

@login_required
def product_list(request):
    """Список товаров — Founder полный доступ, Manager/Operator только просмотр"""
    if not _check_inventory_access(request):
        return redirect("index")
    
    settings = cms_models.Settings.objects.first()
    
    category = request.GET.get("category", "")
    is_active = request.GET.get("is_active", "")
    search = request.GET.get("search", "")
    
    products = Product.objects.all()
    
    if category:
        products = products.filter(category=category)
    if is_active:
        products = products.filter(is_active=is_active == "true")
    if search:
        products = products.filter(name__icontains=search)
    
    return render(request, "pages/system/others/inventory/product_list.html", {
        "settings": settings,
        "products": products,
        "category_choices": Product.Category.choices,
        "can_edit": _is_founder(request.user) or _is_manager(request.user),
    })


@login_required
def product_add(request):
    """Добавление товара — только Founder и Manager"""
    if not _check_inventory_access(request, [User.Role.FOUNDER, User.Role.MANAGER]):
        return redirect("inventory:product_list")
    
    settings = cms_models.Settings.objects.first()
    
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Товар добавлен")
            return redirect("inventory:product_list")
    else:
        form = ProductForm()
    
    return render(request, "pages/system/others/inventory/product_form.html", {
        "settings": settings,
        "form": form,
        "title": "Добавить товар",
    })


@login_required
def product_edit(request, pk):
    """Редактирование товара — только Founder и Manager"""
    if not _check_inventory_access(request, [User.Role.FOUNDER, User.Role.MANAGER]):
        return redirect("inventory:product_list")
    
    settings = cms_models.Settings.objects.first()
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Товар обновлён")
            return redirect("inventory:product_list")
    else:
        form = ProductForm(instance=product)
    
    return render(request, "pages/system/others/inventory/product_form.html", {
        "settings": settings,
        "form": form,
        "product": product,
        "title": "Редактировать товар",
    })


@login_required
def product_delete(request, pk):
    """Удаление товара — только Founder"""
    if request.user.role != User.Role.FOUNDER:
        messages.error(request, "Только основатель может удалять товары")
        return redirect("inventory:product_list")
    
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.delete()
        messages.success(request, "Товар удалён")
    return redirect("inventory:product_list")


# ============ ПРИХОД ТОВАРА ============

@login_required
def stock_incoming(request):
    """Приход товара — только Founder и Manager"""
    if not _check_inventory_access(request, [User.Role.FOUNDER, User.Role.MANAGER]):
        return redirect("inventory:stock_list")
    
    settings = cms_models.Settings.objects.first()
    
    if request.method == "POST":
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.movement_type = StockMovement.MovementType.INCOMING
            movement.created_by = request.user
            movement.save()
            messages.success(request, f"Приход {movement.product.name} ({movement.quantity}) зарегистрирован")
            return redirect("inventory:stock_list")
    else:
        form = StockMovementForm()
        # Для прихода ограничиваем причины
        form.fields["reason"].choices = [
            (StockMovement.Reason.PURCHASE, "Закупка"),
            (StockMovement.Reason.RETURN, "Возврат"),
            (StockMovement.Reason.ADJUSTMENT, "Корректировка"),
        ]
    
    return render(request, "pages/system/others/inventory/movement_form.html", {
        "settings": settings,
        "form": form,
        "title": "Приход товара",
        "movement_type": "incoming",
    })


# ============ ВЫДАЧА НА ЗАКАЗ ============

@login_required
def order_issue(request):
    """Выдача товара на заказ — Founder и Manager"""
    if not _check_inventory_access(request, [User.Role.FOUNDER, User.Role.MANAGER]):
        return redirect("inventory:stock_list")
    
    settings = cms_models.Settings.objects.first()
    
    if request.method == "POST":
        form = OrderIssueForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data["product"]
            quantity = form.cleaned_data["quantity"]
            notes = form.cleaned_data["notes"]
            
            # Проверяем достаточно ли остатка
            stock, _ = Stock.objects.get_or_create(product=product)
            if stock.quantity < quantity:
                messages.error(request, f"Недостаточно остатка. Доступно: {stock.quantity}")
                return render(request, "pages/system/others/inventory/order_issue.html", {
                    "settings": settings,
                    "form": form,
                })
            
            movement = StockMovement.objects.create(
                product=product,
                movement_type=StockMovement.MovementType.OUTGOING,
                reason=StockMovement.Reason.ORDER_ISSUE,
                quantity=quantity,
                created_by=request.user,
                notes=notes,
            )
            messages.success(request, f"Выдача {product.name} ({quantity}) зарегистрирована")
            return redirect("inventory:stock_list")
    else:
        form = OrderIssueForm()
    
    return render(request, "pages/system/others/inventory/order_issue.html", {
        "settings": settings,
        "form": form,
    })


# ============ ИСТОРИЯ ДВИЖЕНИЙ ============

@login_required
def movement_history(request):
    """История движений товаров — Founder полный, Manager/Operator только просмотр"""
    if not _check_inventory_access(request):
        return redirect("index")
    
    settings = cms_models.Settings.objects.first()
    
    product_id = request.GET.get("product", "")
    movement_type = request.GET.get("type", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    
    movements = StockMovement.objects.select_related("product", "created_by").all()
    
    if product_id:
        movements = movements.filter(product_id=product_id)
    if movement_type:
        movements = movements.filter(movement_type=movement_type)
    if date_from:
        movements = movements.filter(created_at__date__gte=date_from)
    if date_to:
        movements = movements.filter(created_at__date__lte=date_to)
    
    movements = movements[:100]  # Ограничиваем последние 100 записей
    
    return render(request, "pages/system/others/inventory/movement_history.html", {
        "settings": settings,
        "movements": movements,
        "products": Product.objects.filter(is_active=True),
    })


# ============ ИНВЕНТАРИЗАЦИЯ ============

@login_required
def inventory_check_list(request):
    """Список инвентаризаций — Founder и Manager"""
    if not _check_inventory_access(request, [User.Role.FOUNDER, User.Role.MANAGER]):
        return redirect("inventory:stock_list")
    
    settings = cms_models.Settings.objects.first()
    
    status = request.GET.get("status", "")
    
    checks = InventoryCheck.objects.all()
    if status:
        checks = checks.filter(status=status)
    
    return render(request, "pages/system/others/inventory/check_list.html", {
        "settings": settings,
        "checks": checks,
    })


@login_required
def inventory_check_create(request):
    """Создание инвентаризации — Founder и Manager"""
    if not _check_inventory_access(request, [User.Role.FOUNDER, User.Role.MANAGER]):
        return redirect("inventory:check_list")
    
    settings = cms_models.Settings.objects.first()
    
    if request.method == "POST":
        form = InventoryCheckForm(request.POST)
        if form.is_valid():
            check = form.save(commit=False)
            check.created_by = request.user
            check.save()
            
            # Автоматически добавляем все товары с текущими остатками
            products = Product.objects.filter(is_active=True)
            for product in products:
                stock = Stock.objects.filter(product=product).first()
                expected = stock.quantity if stock else 0
                InventoryCheckItem.objects.create(
                    inventory_check=check,
                    product=product,
                    expected_quantity=expected,
                    actual_quantity=0,  # Будет заполнено при подсчёте
                )
            
            messages.success(request, f"Инвентаризация {check.name} создана. Товаров: {products.count()}")
            return redirect("inventory:check_detail", pk=check.pk)
    else:
        form = InventoryCheckForm()
    
    return render(request, "pages/system/others/inventory/check_form.html", {
        "settings": settings,
        "form": form,
    })


@login_required
def inventory_check_detail(request, pk):
    """Детальная страница инвентаризации с подсчётом"""
    if not _check_inventory_access(request, [User.Role.FOUNDER, User.Role.MANAGER]):
        return redirect("inventory:check_list")
    
    settings = cms_models.Settings.objects.first()
    check = get_object_or_404(InventoryCheck, pk=pk)
    
    return render(request, "pages/system/others/inventory/check_detail.html", {
        "settings": settings,
        "check": check,
        "items": check.items.select_related("product").all(),
    })


@login_required
def inventory_check_item_update(request, check_pk, item_pk):
    """Обновление фактического количества"""
    if not _check_inventory_access(request, [User.Role.FOUNDER, User.Role.MANAGER]):
        return redirect("inventory:check_list")
    
    check = get_object_or_404(InventoryCheck, pk=check_pk)
    item = get_object_or_404(InventoryCheckItem, pk=item_pk, inventory_check=check)
    
    if check.status != InventoryCheck.Status.IN_PROGRESS:
        messages.error(request, "Инвентаризация завершена, редактирование невозможно")
        return redirect("inventory:check_detail", pk=check.pk)
    
    if request.method == "POST":
        form = InventoryCheckItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Количество обновлено")
            return redirect("inventory:check_detail", pk=check.pk)
    else:
        form = InventoryCheckItemForm(instance=item)
    
    return render(request, "pages/system/others/inventory/check_item_form.html", {
        "check": check,
        "item": item,
        "form": form,
    })


@login_required
def inventory_check_complete(request, pk):
    """Завершение инвентаризации с созданием корректировок"""
    if not _check_inventory_access(request, [User.Role.FOUNDER, User.Role.MANAGER]):
        return redirect("inventory:check_list")
    
    check = get_object_or_404(InventoryCheck, pk=pk)
    
    if check.status != InventoryCheck.Status.IN_PROGRESS:
        messages.error(request, "Инвентаризация уже завершена")
        return redirect("inventory:check_detail", pk=pk)
    
    if request.method == "POST":
        with transaction.atomic():
            # Создаём корректировки для расхождений
            adjustments = 0
            for item in check.items.all():
                discrepancy = item.discrepancy
                if discrepancy != 0:
                    movement_type = (
                        StockMovement.MovementType.INCOMING 
                        if discrepancy > 0 
                        else StockMovement.MovementType.OUTGOING
                    )
                    StockMovement.objects.create(
                        product=item.product,
                        movement_type=movement_type,
                        reason=StockMovement.Reason.INVENTORY,
                        quantity=abs(discrepancy),
                        created_by=request.user,
                        notes=f"Корректировка по инвентаризации: {check.name}",
                    )
                    adjustments += 1
            
            check.complete(request.user)
            messages.success(request, f"Инвентаризация завершена. Корректировок: {adjustments}")
        
        return redirect("inventory:check_list")
    
    return render(request, "pages/system/others/inventory/check_complete.html", {
        "check": check,
        "discrepancies": [i for i in check.items.all() if i.discrepancy != 0],
    })


# ============ СПИСАНИЕ ============

@login_required
def write_off_list(request):
    """Список списаний — Founder полный, Manager только просмотр"""
    if not _check_inventory_access(request, [User.Role.FOUNDER, User.Role.MANAGER]):
        return redirect("inventory:stock_list")
    
    settings = cms_models.Settings.objects.first()
    
    reason = request.GET.get("reason", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    
    write_offs = WriteOff.objects.select_related("product", "created_by").all()
    
    if reason:
        write_offs = write_offs.filter(reason=reason)
    if date_from:
        write_offs = write_offs.filter(created_at__date__gte=date_from)
    if date_to:
        write_offs = write_offs.filter(created_at__date__lte=date_to)
    
    return render(request, "pages/system/others/inventory/writeoff_list.html", {
        "settings": settings,
        "write_offs": write_offs,
        "reason_choices": WriteOff.Reason.choices,
        "can_create": _is_founder(request.user),
    })


@login_required
def write_off_create(request):
    """Создание списания — только Founder"""
    if request.user.role != User.Role.FOUNDER:
        messages.error(request, "Только основатель может списывать товары")
        return redirect("inventory:writeoff_list")
    
    settings = cms_models.Settings.objects.first()
    
    if request.method == "POST":
        form = WriteOffForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data["product"]
            quantity = form.cleaned_data["quantity"]
            
            # Проверяем достаточно ли остатка
            stock, _ = Stock.objects.get_or_create(product=product)
            if stock.quantity < quantity:
                messages.error(request, f"Недостаточно остатка. Доступно: {stock.quantity}")
                return render(request, "pages/system/others/inventory/writeoff_form.html", {
                    "settings": settings,
                    "form": form,
                })
            
            write_off = form.save(commit=False)
            write_off.created_by = request.user
            write_off.save()
            
            messages.success(request, f"Списание {product.name} ({quantity}) зарегистрировано")
            return redirect("inventory:writeoff_list")
    else:
        form = WriteOffForm()
    
    return render(request, "pages/system/others/inventory/writeoff_form.html", {
        "settings": settings,
        "form": form,
    })
