from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.common.permissions import PermissionRequiredMixin
from apps.accounts.models import User, UserRole
from .models import Employee, EmployeeStatus


class EmployeeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Список сотрудников с фильтрацией по ролям и статусам."""
    permission_key = 'employees.view'
    model = User
    template_name = 'employees/list.html'
    context_object_name = 'employees'
    paginate_by = 20

    def get_queryset(self):
        queryset = User.objects.filter(is_active=True).order_by('full_name')

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                full_name__icontains=search
            ) | queryset.filter(phone__icontains=search)

        role = self.request.GET.get('role')
        if role:
            queryset = queryset.filter(role=role)

        status = self.request.GET.get('status')
        if status:
            if status == 'active':
                queryset = queryset.filter(is_active=True)
            elif status == 'inactive':
                queryset = queryset.filter(is_active=False)

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['role_filter'] = self.request.GET.get('role', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['role_choices'] = UserRole.choices
        context['total_count'] = User.objects.filter(is_active=True).count()

        role_stats = []
        for role_value, role_label in UserRole.choices:
            role_stats.append({
                'value': role_value,
                'label': role_label,
                'count': User.objects.filter(role=role_value, is_active=True).count(),
            })
        context['role_stats'] = role_stats

        return context


class EmployeeDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Детальная страница сотрудника."""
    permission_key = 'employees.view'
    model = User
    template_name = 'employees/detail.html'
    context_object_name = 'emp'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        emp = self.get_object()
        context['recent_expenses'] = emp.expenses.order_by('-created_at')[:10] if hasattr(emp, 'expenses') else []
        return context
