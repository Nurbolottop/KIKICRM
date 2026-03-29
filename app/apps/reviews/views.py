from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator

from apps.accounts.models import UserRole
from apps.orders.models import Order
from .models import Review


def can_manage_reviews(user):
    """Проверка что пользователь может управлять отзывами."""
    if not user.is_authenticated:
        return False
    return user.role in [UserRole.MANAGER, UserRole.OPERATOR, UserRole.FOUNDER]


@login_required
def reviews_list(request):
    """Список отзывов."""
    if not can_manage_reviews(request.user):
        return render(request, 'reviews/error.html', {'message': 'Доступ запрещен.'})

    queryset = Review.objects.select_related('order', 'created_by').all()

    # Фильтр по типу отзыва
    review_type = request.GET.get('type', '')
    if review_type:
        queryset = queryset.filter(review_type=review_type)

    # Фильтр по заказу
    order_code = request.GET.get('order', '')
    if order_code:
        queryset = queryset.filter(order__order_code__icontains=order_code)

    # Поиск по описанию
    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(description__icontains=search) |
            Q(order__order_code__icontains=search) |
            Q(order__client__full_name__icontains=search)
        )

    # Пагинация
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'reviews/list.html', {
        'page_obj': page_obj,
        'review_type': review_type,
        'order_code': order_code,
        'search': search,
        'total': queryset.count(),
    })


@login_required
def review_create(request):
    """Создание нового отзыва."""
    if not can_manage_reviews(request.user):
        return render(request, 'reviews/error.html', {'message': 'Доступ запрещен.'})

    # Получаем список заказов для выбора
    orders = Order.objects.filter(
        operator_status='SUCCESS'
    ).select_related('client').order_by('-created_at')[:100]

    if request.method == 'POST':
        order_id = request.POST.get('order')
        review_type = request.POST.get('review_type', 'POSITIVE')
        description = request.POST.get('description', '').strip()
        photo = request.FILES.get('photo')

        if not order_id:
            messages.error(request, 'Выберите заказ.')
            return render(request, 'reviews/create.html', {
                'orders': orders,
                'review_type': review_type,
                'description': description,
            })

        order = get_object_or_404(Order, id=order_id)

        review = Review.objects.create(
            order=order,
            created_by=request.user,
            review_type=review_type,
            description=description,
            photo=photo
        )

        # Отправляем уведомление в Telegram
        try:
            from apps.telegram_bot.services.telegram_service import notify_new_review
            notify_new_review(review)
        except Exception:
            pass

        messages.success(request, 'Отзыв успешно добавлен.')
        return redirect('reviews_list')

    return render(request, 'reviews/create.html', {
        'orders': orders,
    })


@login_required
def review_detail(request, pk):
    """Детальная страница отзыва."""
    if not can_manage_reviews(request.user):
        return render(request, 'reviews/error.html', {'message': 'Доступ запрещен.'})

    review = get_object_or_404(Review, pk=pk)
    return render(request, 'reviews/detail.html', {'review': review})


@login_required
def review_delete(request, pk):
    """Удаление отзыва."""
    if not can_manage_reviews(request.user):
        return render(request, 'reviews/error.html', {'message': 'Доступ запрещен.'})

    review = get_object_or_404(Review, pk=pk)

    if request.method == 'POST':
        review.delete()
        messages.success(request, 'Отзыв удален.')
        return redirect('reviews_list')

    return render(request, 'reviews/delete_confirm.html', {'review': review})
