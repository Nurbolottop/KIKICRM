"""
Централизованная система прав доступа по ролям для KIKI CRM.

Роли:
- FOUNDER: полный доступ
- MANAGER: управление заказами, клинерами, складом, расходами
- OPERATOR: создание клиентов/заказов, передача менеджеру
- SMM: только аналитика
- HR: управление сотрудниками
- SENIOR_CLEANER: управление командой, НЕ закрывает заказы
- CLEANER: только свои задачи
"""
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import UserPassesTestMixin

from apps.accounts.models import UserRole


# ============================================================================
# ROLE MATRIX - Централизованная матрица прав
# ============================================================================

ROLE_PERMISSIONS = {
    UserRole.FOUNDER: {
        # Clients
        'clients.view': True,
        'clients.create': True,
        'clients.edit': True,
        'clients.delete': True,
        # Orders
        'orders.view': True,
        'orders.create': True,
        'orders.edit': True,
        'orders.delete': True,
        'orders.assign_cleaners': True,
        'orders.close': True,  # Founder может закрывать в любой ситуации
        'orders.ready_for_review': True,
        # Services
        'services.view': True,
        'services.create': True,
        'services.edit': True,
        'services.delete': True,
        # Employees
        'employees.view': True,
        'employees.create': True,
        'employees.edit': True,
        'employees.delete': True,
        # Expenses
        'expenses.view': True,
        'expenses.create': True,
        'expenses.approve': True,
        'expenses.reject': True,
        # Inventory
        'inventory.view': True,
        'inventory.create': True,
        'inventory.edit': True,
        'inventory.transactions': True,
        # Dashboard
        'dashboard.full': True,
        'dashboard.limited': True,
        # Cleaner Panel
        'cleaner_panel.view': True,
        'cleaner_panel.assign': True,
        # Admin settings
        'admin.settings': True,
    },
    
    UserRole.MANAGER: {
        # Clients
        'clients.view': True,
        'clients.create': False,  # MANAGER НЕ создаёт клиентов - только OPERATOR
        'clients.edit': False,
        'clients.delete': False,
        # Orders
        'orders.view': True,
        'orders.create': False,  # MANAGER НЕ создаёт заказы - только OPERATOR
        'orders.edit': True,
        'orders.delete': False,
        'orders.assign_cleaners': True,
        'orders.close': True,  # Manager закрывает заказ
        'orders.ready_for_review': False,
        # Services
        'services.view': True,
        'services.create': False,  # MANAGER НЕ создаёт услуги
        'services.edit': True,
        'services.delete': False,
        # Employees
        'employees.view': True,
        'employees.create': False,
        'employees.edit': False,
        'employees.delete': False,
        # Expenses
        'expenses.view': True,
        'expenses.create': True,
        # Inventory
        'inventory.view': True,
        'inventory.create': True,
        'inventory.edit': True,
        'inventory.transactions': True,
        # Dashboard
        'dashboard.full': True,
        'dashboard.limited': True,
        # Cleaner Panel
        'cleaner_panel.view': True,
        'cleaner_panel.assign': True,
        # Admin settings
        'admin.settings': False,
    },
    
    UserRole.OPERATOR: {
        # Clients
        'clients.view': True,
        'clients.create': True,
        'clients.edit': True,
        'clients.delete': False,
        # Orders
        'orders.view': True,
        'orders.create': True,
        'orders.edit': True,
        'orders.delete': False,
        'orders.assign_cleaners': False,  # НЕ назначает клинеров
        'orders.close': True,  # Operator закрывает со своей стороны
        'orders.ready_for_review': False,
        # Services
        'services.view': True,
        'services.create': False,
        'services.edit': False,
        'services.delete': False,
        # Employees
        'employees.view': False,
        'employees.create': False,
        'employees.edit': False,
        'employees.delete': False,
        # Expenses
        'expenses.view': True,
        'expenses.create': True,
        # Inventory
        'inventory.view': True,
        'inventory.create': False,
        'inventory.edit': False,
        'inventory.transactions': False,
        # Dashboard
        'dashboard.full': False,
        'dashboard.limited': True,
        # Cleaner Panel
        'cleaner_panel.view': False,
        'cleaner_panel.assign': False,
        # Admin settings
        'admin.settings': False,
    },
    
    UserRole.SMM: {
        # Clients
        'clients.view': True,  # Только для аналитики источников
        'clients.create': False,
        'clients.edit': False,
        'clients.delete': False,
        # Orders
        'orders.view': False,
        'orders.create': False,
        'orders.edit': False,
        'orders.delete': False,
        'orders.assign_cleaners': False,
        'orders.close': False,
        'orders.ready_for_review': False,
        # Services
        'services.view': False,
        'services.create': False,
        'services.edit': False,
        'services.delete': False,
        # Employees
        'employees.view': False,
        'employees.create': False,
        'employees.edit': False,
        'employees.delete': False,
        # Expenses
        'expenses.view': True,
        'expenses.create': True,
        # Inventory
        'inventory.view': False,
        'inventory.create': False,
        'inventory.edit': False,
        'inventory.transactions': False,
        # Dashboard
        'dashboard.full': False,
        'dashboard.limited': True,  # Только аналитика
        # Cleaner Panel
        'cleaner_panel.view': False,
        'cleaner_panel.assign': False,
        # Admin settings
        'admin.settings': False,
    },
    
    UserRole.HR: {
        # Clients
        'clients.view': False,
        'clients.create': False,
        'clients.edit': False,
        'clients.delete': False,
        # Orders
        'orders.view': False,
        'orders.create': False,
        'orders.edit': False,
        'orders.delete': False,
        'orders.assign_cleaners': False,
        'orders.close': False,
        'orders.ready_for_review': False,
        # Services
        'services.view': False,
        'services.create': False,
        'services.edit': False,
        'services.delete': False,
        # Employees
        'employees.view': True,
        'employees.create': True,
        'employees.edit': True,
        'employees.delete': True,
        # Expenses
        'expenses.view': True,
        'expenses.create': True,
        # Inventory
        'inventory.view': False,
        'inventory.create': False,
        'inventory.edit': False,
        'inventory.transactions': False,
        # Dashboard
        'dashboard.full': False,
        'dashboard.limited': False,
        # Cleaner Panel
        'cleaner_panel.view': False,
        'cleaner_panel.assign': False,
        # Admin settings
        'admin.settings': False,
    },
    
    UserRole.SENIOR_CLEANER: {
        # Clients
        'clients.view': False,
        'clients.create': False,
        'clients.edit': False,
        'clients.delete': False,
        # Orders
        'orders.view': True,  # Видит назначенные заказы
        'orders.create': False,
        'orders.edit': False,
        'orders.delete': False,
        'orders.assign_cleaners': False,
        'orders.close': False,  # НЕ закрывает заказ!
        'orders.ready_for_review': True,  # Передает менеджеру
        # Services
        'services.view': False,
        'services.create': False,
        'services.edit': False,
        'services.delete': False,
        # Employees
        'employees.view': False,
        'employees.create': False,
        'employees.edit': False,
        'employees.delete': False,
        # Expenses
        'expenses.view': True,  # Видит только свои расходы
        'expenses.create': True,
        # Inventory
        'inventory.view': False,
        'inventory.create': False,
        'inventory.edit': False,
        'inventory.transactions': False,
        # Dashboard
        'dashboard.full': False,
        'dashboard.limited': False,
        # Cleaner Panel
        'cleaner_panel.view': True,
        'cleaner_panel.assign': True,
        # Admin settings
        'admin.settings': False,
    },
    
    UserRole.CLEANER: {
        # Clients
        'clients.view': False,
        'clients.create': False,
        'clients.edit': False,
        'clients.delete': False,
        # Orders
        'orders.view': False,  # Видит только через cleaner panel
        'orders.create': False,
        'orders.edit': False,
        'orders.delete': False,
        'orders.assign_cleaners': False,
        'orders.close': False,  # НЕ закрывает заказ!
        'orders.ready_for_review': False,
        # Services
        'services.view': False,
        'services.create': False,
        'services.edit': False,
        'services.delete': False,
        # Employees
        'employees.view': False,
        'employees.create': False,
        'employees.edit': False,
        'employees.delete': False,
        # Expenses
        'expenses.view': False,
        'expenses.create': False,
        'expenses.approve': False,
        'expenses.reject': False,
        # Inventory
        'inventory.view': False,
        'inventory.create': False,
        'inventory.edit': False,
        'inventory.transactions': False,
        # Dashboard
        'dashboard.full': False,
        'dashboard.limited': False,
        # Cleaner Panel
        'cleaner_panel.view': True,
        'cleaner_panel.assign': False,
        # Admin settings
        'admin.settings': False,
    },
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def has_role(user, roles):
    """
    Проверяет, имеет ли пользователь одну из указанных ролей.
    
    Args:
        user: объект пользователя
        roles: одна роль или список ролей (UserRole или строки)
    
    Returns:
        bool
    """
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    if isinstance(roles, (list, tuple, set)):
        return user.role in roles
    return user.role == roles


def has_permission(user, permission_key):
    """
    Проверяет, имеет ли пользователь указанное право.
    
    Args:
        user: объект пользователя
        permission_key: ключ права (например, 'orders.create')
    
    Returns:
        bool
    """
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    user_permissions = ROLE_PERMISSIONS.get(user.role, {})
    return user_permissions.get(permission_key, False)


# ============================================================================
# MODULE-SPECIFIC HELPERS
# ============================================================================

def can_view_clients(user):
    """Может ли пользователь просматривать клиентов."""
    return has_permission(user, 'clients.view')

def can_create_clients(user):
    """Может ли пользователь создавать клиентов."""
    return has_permission(user, 'clients.create')

def can_edit_clients(user):
    """Может ли пользователь редактировать клиентов."""
    return has_permission(user, 'clients.edit')

def can_delete_clients(user):
    """Может ли пользователь удалять клиентов."""
    return has_permission(user, 'clients.delete')


def can_view_orders(user):
    """Может ли пользователь просматривать заказы."""
    return has_permission(user, 'orders.view')

def can_create_orders(user):
    """Может ли пользователь создавать заказы."""
    return has_permission(user, 'orders.create')

def can_edit_orders(user):
    """Может ли пользователь редактировать заказы."""
    return has_permission(user, 'orders.edit')

def can_delete_orders(user):
    """Может ли пользователь удалять заказы."""
    return has_permission(user, 'orders.delete')

def can_assign_cleaners(user):
    """Может ли пользователь назначать клинеров на заказ."""
    return has_permission(user, 'orders.assign_cleaners')

def can_close_order_manager(user):
    """Может ли менеджер закрывать заказ."""
    return has_permission(user, 'orders.close') and has_role(user, [UserRole.MANAGER, UserRole.FOUNDER])

def can_close_order_operator(user):
    """Может ли оператор закрывать заказ."""
    return has_permission(user, 'orders.close') and has_role(user, [UserRole.OPERATOR, UserRole.FOUNDER])

def can_mark_order_ready_for_review(user):
    """Может ли пользователь отметить заказ как готовый к проверке (Senior Cleaner)."""
    return has_permission(user, 'orders.ready_for_review')


def can_view_services(user):
    """Может ли пользователь просматривать услуги."""
    return has_permission(user, 'services.view')

def can_create_services(user):
    """Может ли пользователь создавать услуги."""
    return has_permission(user, 'services.create')

def can_edit_services(user):
    """Может ли пользователь редактировать услуги."""
    return has_permission(user, 'services.edit')

def can_delete_services(user):
    """Может ли пользователь удалять услуги."""
    return has_permission(user, 'services.delete')


def can_view_employees(user):
    """Может ли пользователь просматривать сотрудников."""
    return has_permission(user, 'employees.view')

def can_create_employees(user):
    """Может ли пользователь создавать сотрудников."""
    return has_permission(user, 'employees.create')

def can_edit_employees(user):
    """Может ли пользователь редактировать сотрудников."""
    return has_permission(user, 'employees.edit')

def can_delete_employees(user):
    """Может ли пользователь удалять сотрудников."""
    return has_permission(user, 'employees.delete')


def can_view_expenses(user):
    """Может ли пользователь просматривать расходы."""
    return has_permission(user, 'expenses.view')

def can_create_expenses(user):
    """Может ли пользователь создавать расходы."""
    return has_permission(user, 'expenses.create')

def can_approve_expenses(user):
    """Может ли пользователь одобрять расходы."""
    return has_permission(user, 'expenses.approve')

def can_reject_expenses(user):
    """Может ли пользователь отклонять расходы."""
    return has_permission(user, 'expenses.reject')


def can_view_inventory(user):
    """Может ли пользователь просматривать склад."""
    return has_permission(user, 'inventory.view')

def can_create_inventory(user):
    """Может ли пользователь создавать позиции склада."""
    return has_permission(user, 'inventory.create')

def can_edit_inventory(user):
    """Может ли пользователь редактировать склад."""
    return has_permission(user, 'inventory.edit')

def can_manage_inventory_transactions(user):
    """Может ли пользователь управлять транзакциями склада."""
    return has_permission(user, 'inventory.transactions')


def has_full_dashboard_access(user):
    """Имеет ли пользователь полный доступ к dashboard."""
    return has_permission(user, 'dashboard.full')

def has_limited_dashboard_access(user):
    """Имеет ли пользователь ограниченный доступ к dashboard."""
    return has_permission(user, 'dashboard.limited')


def can_view_cleaner_panel(user):
    """Может ли пользователь просматривать cleaner panel."""
    return has_permission(user, 'cleaner_panel.view')

def can_assign_cleaner_tasks(user):
    """Может ли пользователь назначать задачи клинерам."""
    return has_permission(user, 'cleaner_panel.assign')


def can_access_admin_settings(user):
    """Может ли пользователь управлять глобальными настройками."""
    return has_permission(user, 'admin.settings')


# ============================================================================
# DECORATORS
# ============================================================================

def permission_required(permission_key):
    """
    Декоратор для проверки прав доступа.
    
    Usage:
        @permission_required('orders.create')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not has_permission(request.user, permission_key):
                raise PermissionDenied(f"Permission '{permission_key}' required.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def role_required(roles):
    """
    Декоратор для проверки ролей.
    
    Usage:
        @role_required([UserRole.MANAGER, UserRole.FOUNDER])
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not has_role(request.user, roles):
                raise PermissionDenied("Required role not found.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# ============================================================================
# MIXINS
# ============================================================================

class RoleRequiredMixin(UserPassesTestMixin):
    """
    Mixin для проверки роли в CBV.
    
    Usage:
        class MyView(RoleRequiredMixin, View):
            allowed_roles = [UserRole.MANAGER, UserRole.FOUNDER]
            ...
    """
    allowed_roles = []
    
    def test_func(self):
        return has_role(self.request.user, self.allowed_roles)


class PermissionRequiredMixin(UserPassesTestMixin):
    """
    Mixin для проверки права в CBV.
    
    Usage:
        class MyView(PermissionRequiredMixin, View):
            permission_key = 'orders.create'
            ...
    """
    permission_key = None
    
    def test_func(self):
        if not self.permission_key:
            return True
        return has_permission(self.request.user, self.permission_key)


class CanCloseOrderManagerMixin(UserPassesTestMixin):
    """Mixin для проверки права менеджера закрывать заказ."""
    def test_func(self):
        return can_close_order_manager(self.request.user)


class CanCloseOrderOperatorMixin(UserPassesTestMixin):
    """Mixin для проверки права оператора закрывать заказ."""
    def test_func(self):
        return can_close_order_operator(self.request.user)


class CanMarkOrderReadyMixin(UserPassesTestMixin):
    """Mixin для проверки права Senior Cleaner отметить заказ готовым."""
    def test_func(self):
        return can_mark_order_ready_for_review(self.request.user)
