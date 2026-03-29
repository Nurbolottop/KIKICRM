from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from apps.accounts.models import User, UserRole
from .models import HRSettings


def is_hr(user):
    """Проверка что пользователь HR."""
    return user.is_authenticated and user.role == UserRole.HR


@login_required
def hr_dashboard(request):
    """Главная страница HR панели."""
    if not is_hr(request.user):
        return render(request, 'hr_panel/error.html', {'message': 'Доступ только для HR менеджера.'})

    cleaners = User.objects.filter(role__in=[UserRole.CLEANER, UserRole.SENIOR_CLEANER])
    total = cleaners.count()
    active = cleaners.filter(is_active=True).count()
    inactive = cleaners.filter(is_active=False).count()
    seniors = cleaners.filter(role=UserRole.SENIOR_CLEANER).count()
    regulars = cleaners.filter(role=UserRole.CLEANER).count()

    return render(request, 'hr_panel/dashboard.html', {
        'total': total,
        'active': active,
        'inactive': inactive,
        'seniors': seniors,
        'regulars': regulars,
    })


@login_required
def hr_employees(request):
    """Список клинеров для HR."""
    if not is_hr(request.user):
        return render(request, 'hr_panel/error.html', {'message': 'Доступ только для HR менеджера.'})

    queryset = User.objects.filter(
        role__in=[UserRole.CLEANER, UserRole.SENIOR_CLEANER]
    ).order_by('full_name')

    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(full_name__icontains=search) | Q(phone__icontains=search)
        )

    role_filter = request.GET.get('role', '')
    if role_filter:
        queryset = queryset.filter(role=role_filter)

    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        queryset = queryset.filter(is_active=True)
    elif status_filter == 'inactive':
        queryset = queryset.filter(is_active=False)

    return render(request, 'hr_panel/employees.html', {
        'employees': queryset,
        'search': search,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'total': queryset.count(),
    })


@login_required
def hr_employee_create(request):
    """Создание нового клинера."""
    if not is_hr(request.user):
        return render(request, 'hr_panel/error.html', {'message': 'Доступ только для HR менеджера.'})

    hr_settings, _ = HRSettings.objects.get_or_create(user=request.user)
    default_password = hr_settings.default_password

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()
        role = request.POST.get('role', UserRole.CLEANER)

        if not password and default_password:
            password = default_password

        if not full_name or not phone or not password:
            messages.error(request, 'Заполните все обязательные поля (или установите стандартный пароль).')
            return render(request, 'hr_panel/employee_create.html', {
                'full_name': full_name,
                'phone': phone,
                'role': role,
                'default_password': default_password,
            })

        if role not in [UserRole.CLEANER, UserRole.SENIOR_CLEANER]:
            role = UserRole.CLEANER

        if User.objects.filter(phone=phone).exists():
            messages.error(request, 'Пользователь с таким телефоном уже существует.')
            return render(request, 'hr_panel/employee_create.html', {
                'full_name': full_name,
                'phone': phone,
                'role': role,
                'default_password': default_password,
            })

        user = User.objects.create_user(
            phone=phone,
            password=password,
            full_name=full_name,
            role=role,
        )

        # Создаем запись Employee для пользователя
        from apps.employees.models import Employee, EmployeeDocument, DocumentType
        employee = Employee.objects.create(
            user=user,
            status='ACTIVE',
            employee_code=None
        )

        # Обрабатываем загрузку документов
        document_files = request.FILES.getlist('documents')
        document_types = request.POST.getlist('document_types')
        document_numbers = request.POST.getlist('document_numbers')

        for i, doc_file in enumerate(document_files):
            if doc_file:
                doc_type = document_types[i] if i < len(document_types) else DocumentType.PASSPORT
                doc_number = document_numbers[i] if i < len(document_numbers) else ''
                
                # Проверяем, что тип документа валиден
                if doc_type not in [dt[0] for dt in DocumentType.choices]:
                    doc_type = DocumentType.PASSPORT
                
                EmployeeDocument.objects.create(
                    employee=employee,
                    document_type=doc_type,
                    document_number=doc_number,
                    file=doc_file
                )

        login_url = request.build_absolute_uri('/accounts/login/')

        return render(request, 'hr_panel/employee_create.html', {
            'default_password': default_password,
            'created_user': {
                'full_name': user.full_name,
                'phone': user.phone,
                'password': password,
                'role': user.get_role_display(),
                'login_url': login_url,
            },
        })

    return render(request, 'hr_panel/employee_create.html', {
        'default_password': default_password,
    })


@login_required
def hr_settings_view(request):
    """Настройки HR: стандартный пароль."""
    if not is_hr(request.user):
        return render(request, 'hr_panel/error.html', {'message': 'Доступ только для HR менеджера.'})

    hr_settings, _ = HRSettings.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        new_password = request.POST.get('default_password', '').strip()
        hr_settings.default_password = new_password
        hr_settings.save(update_fields=['default_password'])
        if new_password:
            messages.success(request, 'Стандартный пароль обновлён.')
        else:
            messages.success(request, 'Стандартный пароль удалён. Пароль нужно будет вводить вручную.')
        return redirect('hr_settings')

    return render(request, 'hr_panel/settings.html', {
        'hr_settings': hr_settings,
    })


@login_required
def hr_employee_detail(request, pk):
    """Детальная страница клинера."""
    if not is_hr(request.user):
        return render(request, 'hr_panel/error.html', {'message': 'Доступ только для HR менеджера.'})

    emp = get_object_or_404(User, pk=pk, role__in=[UserRole.CLEANER, UserRole.SENIOR_CLEANER])
    
    # Получаем документы сотрудника
    documents = []
    try:
        if hasattr(emp, 'employee'):
            documents = emp.employee.documents.all()
    except:
        pass
    
    return render(request, 'hr_panel/employee_detail.html', {'emp': emp, 'documents': documents})


@login_required
def hr_toggle_active(request, pk):
    """Активировать/деактивировать аккаунт клинера."""
    if not is_hr(request.user):
        return render(request, 'hr_panel/error.html', {'message': 'Доступ только для HR менеджера.'})

    if request.method != 'POST':
        return redirect('hr_employees')

    emp = get_object_or_404(User, pk=pk, role__in=[UserRole.CLEANER, UserRole.SENIOR_CLEANER])
    emp.is_active = not emp.is_active
    emp.save(update_fields=['is_active'])

    status_text = 'активирован' if emp.is_active else 'деактивирован'
    messages.success(request, f'Аккаунт {emp.full_name} {status_text}.')
    return redirect('hr_employee_detail', pk=pk)


@login_required
def hr_promote(request, pk):
    """Повысить клинера до старшего клинера."""
    if not is_hr(request.user):
        return render(request, 'hr_panel/error.html', {'message': 'Доступ только для HR менеджера.'})

    if request.method != 'POST':
        return redirect('hr_employees')

    emp = get_object_or_404(User, pk=pk, role__in=[UserRole.CLEANER, UserRole.SENIOR_CLEANER])

    if emp.role == UserRole.CLEANER:
        emp.role = UserRole.SENIOR_CLEANER
        msg = f'{emp.full_name} повышен до Старшего клинера.'
    else:
        emp.role = UserRole.CLEANER
        msg = f'{emp.full_name} понижен до Клинера.'

    emp.save(update_fields=['role'])
    messages.success(request, msg)
    return redirect('hr_employee_detail', pk=pk)
