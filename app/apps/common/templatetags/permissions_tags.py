"""Template tags для проверки permissions."""
from django import template
from apps.common import permissions

register = template.Library()


@register.filter
def can_view_expenses(user):
    """Может ли пользователь просматривать расходы."""
    return permissions.can_view_expenses(user)


@register.filter
def can_create_expenses(user):
    """Может ли пользователь создавать расходы."""
    return permissions.can_create_expenses(user)


@register.filter
def can_view_inventory(user):
    """Может ли пользователь просматривать склад."""
    return permissions.can_view_inventory(user)


@register.filter
def can_create_inventory(user):
    """Может ли пользователь создавать товары на складе."""
    return permissions.can_create_inventory(user)


@register.filter
def can_edit_inventory(user):
    """Может ли пользователь редактировать склад."""
    return permissions.can_edit_inventory(user)


@register.filter
def can_manage_inventory_transactions(user):
    """Может ли пользователь управлять операциями склада."""
    return permissions.can_manage_inventory_transactions(user)
