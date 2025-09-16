from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_protect

def redirect_user_by_role(user):
    if user.role == 'MANAGER':
        return redirect('manager:index')
    elif user.role == 'CLEANER':
        return redirect('cleaner:index')
    elif user.role == 'SMM':
        return redirect('smm:index')
    elif user.role == 'OPERATOR':
        return redirect('operator:index')
    elif user.role == 'IT':
        return redirect('it:index')
    elif user.role == 'FOUNDER':
        return redirect('founder:index')
    elif user.role == 'SENIOR_CLEANER':
        return redirect('senior_cleaner:index')
    else:
        return redirect('default:index')  # если что-то не так

@csrf_protect
def login_view(request):
    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect_user_by_role(user)
        else:
            messages.error(request, 'Неверный логин или пароль')

    return render(request, 'users/login.html')
