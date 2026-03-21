"""View для отмены проверки старшим клинером."""
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from apps.orders.models import Order
from .views_cl import is_cleaner, _get_employee, _is_senior, _is_senior_on_order, _notify_order_event


@login_required
@require_POST
def cancel_senior_review_cl(request, order_id):
    """Отменить проверку заказа старшим клинером (вернуть в работу)."""
    if not is_cleaner(request.user):
        return redirect('dashboard')

    order = get_object_or_404(Order, id=order_id)
    employee = _get_employee(request)
    
    if not employee or not _is_senior(request.user) or not _is_senior_on_order(order, employee):
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Только старший клинер может отменить проверку.'
        })

    # Проверяем что заказ действительно на проверке
    if order.senior_cleaner_status != 'SENT_FOR_REVIEW':
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Заказ не находится на проверке.'
        })

    # Сбрасываем статус старшего клинера и возобновляем таймер
    order.senior_cleaner_status = Order.SeniorCleanerStatus.WORKING
    order.save(update_fields=['senior_cleaner_status'])
    
    # Возобновляем таймер — сбрасываем finished_at для старшего клинера
    from apps.orders.models import OrderEmployee
    senior_oe = OrderEmployee.objects.filter(
        order=order,
        role_on_order='senior_cleaner'
    ).first()
    if senior_oe and senior_oe.finished_at:
        senior_oe.finished_at = None
        senior_oe.save(update_fields=['finished_at'])
    
    _notify_order_event(order, "↩️ Отменена отправка на проверку", request.user)

    return redirect('order_detail_cl', order_id=order.id)
