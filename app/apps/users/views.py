from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import get_object_or_404, render, redirect
from apps.cms import models as cms_models
from django.contrib import messages

from apps.orders import models as orders_models
from apps.users.models import User


_SENIOR_CLEANER_ROLES = [
    User.Role.SENIOR_CLEANER,
    'SENIOR_CLINER',
    'SENIOR_CLEANING',
    'SENIOR',
    'SENIOR_STAFF',
    'ST_CLEANER',
    'ST_CLINER',
]

_CLEANER_ROLES = [
    User.Role.CLEANER,
    'CLINER',
    'CLEANING',
    'STAFF',
]

def login_view(request):
    settings = cms_models.Settings.objects.first()

    # если пользователь уже вошёл → сразу на index
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            messages.error(request, 'Неверный логин или пароль')

    return render(request, 'pages/users/auth-signin.html', {"settings": settings})


@login_required
def staff_list(request):
    settings = cms_models.Settings.objects.first()
    if request.user.role not in [User.Role.FOUNDER, User.Role.MANAGER]:
        messages.error(request, "У вас нет доступа к разделу сотрудников")
        return redirect('index')

    employees = User.objects.exclude(pk=request.user.pk)
    busy_cleaner_ids = set()
    busy_senior_ids = set()

    if request.user.role == User.Role.MANAGER:
        employees = employees.filter(role__in=[*_SENIOR_CLEANER_ROLES, *_CLEANER_ROLES])

        busy_cleaner_ids = set(
            orders_models.Task.objects.filter(status='IN_PROGRESS', cleaner_id__isnull=False)
            .values_list('cleaner_id', flat=True)
            .distinct()
        )

        busy_senior_ids = set(
            orders_models.Order.objects.filter(
                senior_cleaner_id__isnull=False,
                status_manager__in=[
                    orders_models.Order.ManagerStatus.ASSIGNED,
                    orders_models.Order.ManagerStatus.IN_PROGRESS,
                    orders_models.Order.ManagerStatus.PENDING_REVIEW,
                ],
            )
            .values_list('senior_cleaner_id', flat=True)
            .distinct()
        )

    employees = employees.annotate(
        role_priority=Case(
            When(role=User.Role.SMM, then=Value(1)),
            When(role=User.Role.OPERATOR, then=Value(2)),
            When(role=User.Role.MANAGER, then=Value(3)),
            When(role__in=[
                'SENIOR_CLEANER',
                'SENIOR_CLINER',
                'SENIOR_CLEANING',
                'SENIOR',
                'SENIOR_STAFF',
                'ST_CLEANER',
                'ST_CLINER',
            ], then=Value(4)),
            When(role__in=[
                'CLEANER',
                'CLINER',
                'CLEANING',
                'STAFF',
            ], then=Value(5)),
            default=Value(99),
            output_field=IntegerField(),
        )
    ).order_by('role_priority', 'full_name', 'username')

    return render(
        request,
        'pages/users/staff_list.html',
        {
            'settings': settings,
            'employees': employees,
            'busy_cleaner_ids': list(busy_cleaner_ids),
            'busy_senior_ids': list(busy_senior_ids),
        },
    )


@login_required
def staff_detail(request, pk: int):
    settings = cms_models.Settings.objects.first()
    if request.user.role not in [User.Role.FOUNDER, User.Role.MANAGER]:
        messages.error(request, "У вас нет доступа к разделу сотрудников")
        return redirect('index')

    employee = get_object_or_404(User, pk=pk)

    if request.user.role == User.Role.MANAGER and employee.role not in [*_SENIOR_CLEANER_ROLES, *_CLEANER_ROLES]:
        messages.error(request, "У вас нет доступа к этому сотруднику")
        return redirect('staff_list')

    is_busy = False
    if employee.role in _CLEANER_ROLES:
        is_busy = orders_models.Task.objects.filter(cleaner=employee, status='IN_PROGRESS').exists()
    elif employee.role in _SENIOR_CLEANER_ROLES:
        is_busy = orders_models.Order.objects.filter(
            senior_cleaner=employee,
            status_manager__in=[
                orders_models.Order.ManagerStatus.ASSIGNED,
                orders_models.Order.ManagerStatus.IN_PROGRESS,
                orders_models.Order.ManagerStatus.PENDING_REVIEW,
            ],
        ).exists()

    return render(
        request,
        'pages/users/staff_detail.html',
        {
            'settings': settings,
            'employee': employee,
            'viewer_role': request.user.role,
            'is_busy': is_busy,
        },
    )
