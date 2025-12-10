from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_GET, require_POST
from django.utils.crypto import constant_time_compare
from urllib.parse import parse_qsl
import hmac
import hashlib
import json

from apps.orders import models as orders_models
from .models import TelegramUser

# --- Helpers ---

def verify_init_data(init_data: str) -> dict | None:
    """Verify Telegram WebApp initData using bot token per TG spec.
    Returns parsed data dict if valid, else None.
    """
    if not init_data:
        return None
    try:
        parts = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        return None
    hash_ = parts.pop('hash', None)
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parts.items()))
    secret_key = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode()).digest()
    check_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if hash_ and constant_time_compare(hash_, check_hash):
        return parts
    return None


def get_cleaner_from_init(init_data_dict):
    """Map Telegram user to system user (cleaner) via TelegramUser model if linked."""
    try:
        user_str = init_data_dict.get('user')
        tg_user = json.loads(user_str) if isinstance(user_str, str) else user_str
        tg_id = int(tg_user.get('id'))
    except Exception:
        return None
    try:
        tu = TelegramUser.objects.select_related('user').get(id_user=tg_id, is_active=True)
        return tu.user
    except TelegramUser.DoesNotExist:
        return None


# --- Pages ---

@require_GET
def app_home(request):
    init_data = request.GET.get('tgWebAppData') or request.GET.get('initData') or request.META.get('HTTP_TELEGRAM_INIT_DATA', '')
    data = verify_init_data(init_data)
    if not data:
        return HttpResponseForbidden("Invalid Telegram init data")
    user = get_cleaner_from_init(data)
    if not user or user.role != 'CLEANER':
        return HttpResponseForbidden("Unauthorized")
    return render(request, 'tg/app_home.html', { 'initData': init_data })


@require_GET
def task_page(request, pk: int):
    init_data = request.GET.get('tgWebAppData') or request.GET.get('initData') or request.META.get('HTTP_TELEGRAM_INIT_DATA', '')
    data = verify_init_data(init_data)
    if not data:
        return HttpResponseForbidden("Invalid Telegram init data")
    user = get_cleaner_from_init(data)
    if not user or user.role != 'CLEANER':
        return HttpResponseForbidden("Unauthorized")
    task = get_object_or_404(orders_models.Task, pk=pk)
    if task.cleaner_id != user.id:
        return HttpResponseForbidden("Not your task")
    return render(request, 'tg/task_page.html', { 'initData': init_data, 'task': task })


# --- APIs ---

@require_GET
def api_tasks(request):
    init_data = request.GET.get('tgWebAppData') or request.GET.get('initData') or request.META.get('HTTP_TELEGRAM_INIT_DATA', '')
    data = verify_init_data(init_data)
    if not data:
        return JsonResponse({'ok': False, 'error': 'bad_init'}, status=403)
    user = get_cleaner_from_init(data)
    if not user or user.role != 'CLEANER':
        return JsonResponse({'ok': False, 'error': 'unauthorized'}, status=403)
    tasks = orders_models.Task.objects.filter(cleaner_id=user.id).order_by('status', 'id')
    result = [
        {
            'id': t.id,
            'description': t.description,
            'status': t.status,
            'order_code': t.order.code,
        } for t in tasks
    ]
    return JsonResponse({'ok': True, 'tasks': result})


@require_POST
def api_task_submit(request, pk: int):
    init_data = request.POST.get('tgWebAppData') or request.POST.get('initData') or request.META.get('HTTP_TELEGRAM_INIT_DATA', '')
    data = verify_init_data(init_data)
    if not data:
        return JsonResponse({'ok': False, 'error': 'bad_init'}, status=403)
    user = get_cleaner_from_init(data)
    if not user or user.role != 'CLEANER':
        return JsonResponse({'ok': False, 'error': 'unauthorized'}, status=403)
    task = get_object_or_404(orders_models.Task, pk=pk)
    if task.cleaner_id != user.id:
        return JsonResponse({'ok': False, 'error': 'not_your_task'}, status=403)
    task.status = 'PENDING_REVIEW'
    task.save(update_fields=["status"])
    return JsonResponse({'ok': True})
