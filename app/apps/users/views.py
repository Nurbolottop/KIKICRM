from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from apps.cms import models as cms_models
from django.contrib import messages

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

    return render(request, 'pages/users/forms/auth-signin.html', {"settings": settings})
