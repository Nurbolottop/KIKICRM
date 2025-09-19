from django.contrib.auth import authenticate, login
from django.contrib.messages import get_messages
from django.shortcuts import render, redirect
from apps.cms import models as cms_models
from django.contrib import messages

def redirect_user_by_role(request, user):
    if user.role == 'FOUNDER':
        return redirect('founder:index')
    elif user.role == 'SMM':
        return redirect('smm:index')
    elif user.role == 'MANAGER':
        return redirect('manager:index')
    elif user.role == 'SENIOR_CLEANER':
        return redirect('senior_cleaner:index')
    elif user.role == 'CLEANER':
        return redirect('cleaner:index')
    elif user.role == 'CANDIDATE':
        return redirect('candidate:index')
    elif user.role == 'IT':
        return redirect('/admin/')  # отправляем в админку
    else:
        if not get_messages(request):
            messages.error(request, 'Недопустимая роль. Обратитесь к администратору.')
        return redirect('login')

def login_view(request):
    settings = cms_models.Settings.objects.first()
    if request.user.is_authenticated:
        if hasattr(request.user, 'role'):
            return redirect_user_by_role(request, request.user)
        else:
            logout(request)  # сбрасываем сессию, если нет роли
            messages.error(request, 'Недопустимая роль. Обратитесь к администратору.')
            return redirect('login')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if hasattr(user, 'role'):
                return redirect_user_by_role(request, user)
            else:
                logout(request)
                messages.error(request, 'Недопустимая роль. Обратитесь к администратору.')
                return redirect('login')
        else:
            messages.error(request, 'Неверный логин или пароль')

    return render(request, 'pages/users/forms/auth-signin.html',locals())
