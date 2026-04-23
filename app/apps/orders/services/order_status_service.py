"""
Сервис управления статусами заказа.

Предоставляет методы для управления переходами между статусами
в соответствии с бизнес-логикой CRM KIKI.
"""

from django.utils import timezone
from django.core.exceptions import PermissionDenied

from apps.orders.models import Order


class OrderStatusService:
    """Сервис для управления статусами заказа."""

    @staticmethod
    def _send_status_notification(order: Order, status_name: str, user, old_status: str = None):
        """
        Отправляет уведомление в Telegram об изменении статуса.
        
        Args:
            order: Заказ
            status_name: Название нового статуса
            user: Пользователь, выполнивший действие
            old_status: Предыдущий статус (опционально)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from apps.notifications.services.telegram_service import TelegramService
            
            service = TelegramService()
            logger.info(f"[DEBUG _send_status_notification] token={bool(service.token)}, chat_id={bool(service.chat_id)}, status_changes_thread_id={getattr(service.settings, 'status_changes_thread_id', None) if service.settings else 'NO SETTINGS'}")
            
            if not service.token or not service.chat_id:
                logger.warning("[DEBUG] Telegram not configured: missing token or chat_id")
                return
            
            old_status_text = f" (было: {old_status})" if old_status else ""
            
            message = (
                f"🔔 <b>Изменение статуса заказа</b>\n\n"
                f"📋 Заказ: <b>#{order.order_code or order.id}</b>\n"
                f"👤 Клиент: {order.client.get_full_name() if order.client else '—'}\n"
                f"📍 Адрес: {order.address or '—'}\n\n"
                f"🔄 Статус: <b>{status_name}</b>{old_status_text}\n"
                f"👨‍💻 Пользователь: {getattr(user, 'full_name', '') or getattr(user, 'phone', str(user))}"
            )
            
            result = service.send_cleaner_message(message)
            logger.info(f"[DEBUG] Telegram notification result: {result}")
        except Exception as e:
            logger.exception(f"[DEBUG] Failed to send Telegram notification: {e}")
            # Не прерываем выполнение при ошибке отправки уведомления

    @staticmethod
    def transfer_to_manager(order: Order, user) -> None:
        """
        Оператор передаёт заказ менеджеру.
        
        Args:
            order: Заказ для обработки
            user: Пользователь, выполняющий действие (оператор)
            
        Raises:
            PermissionDenied: Если пользователь не может выполнить это действие
        """
        # Проверяем права
        if not OrderStatusService._can_change_operator_status(user):
            raise PermissionDenied('Только оператор может передавать заказ менеджеру.')
        
        # Проверяем текущий статус
        if order.operator_status != Order.OperatorStatus.IN_PROGRESS:
            raise ValueError('Заказ должен быть в статусе "В обработке" для передачи.')
        
        # Обновляем статус оператора
        order.operator_status = Order.OperatorStatus.TRANSFERRED
        
        # Обновляем флаг передачи
        order.handed_to_manager = True
        order.handed_to_manager_at = timezone.now()
        
        # Сохраняем
        order.save()
        
        # Отправляем уведомление
        OrderStatusService._send_status_notification(
            order, 
            "📤 Передан менеджеру", 
            user,
            "В обработке"
        )

    @staticmethod
    def reject_by_operator(order: Order, user, reason: str = None) -> None:
        """
        Оператор отклоняет заказ.
        
        Args:
            order: Заказ для отклонения
            user: Пользователь, выполняющий действие
            reason: Причина отклонения
        """
        if not OrderStatusService._can_change_operator_status(user):
            raise PermissionDenied('Только оператор может отменить заказ.')
        
        if order.operator_status != Order.OperatorStatus.IN_PROGRESS:
            raise ValueError('Заказ должен быть в статусе "В обработке" для отмены.')
        
        order.operator_status = Order.OperatorStatus.REJECTED
        order.manager_status = Order.ManagerStatus.REJECTED
        order.senior_cleaner_status = Order.SeniorCleanerStatus.REJECTED
        order.operator_closed_at = timezone.now()
        
        if reason:
            order.comment = f"{order.comment}\n\nПричина отклонения: {reason}" if order.comment else f"Причина отклонения: {reason}"
        
        order.save()
        
        # Отправляем уведомление
        OrderStatusService._send_status_notification(
            order, 
            f"❌ Отменён оператором{' (Причина: ' + reason + ')' if reason else ''}", 
            user,
            "В обработке"
        )

    @staticmethod
    def operator_mark_success(order: Order, user) -> None:
        """
        Оператор подтверждает завершение заказа.
        
        Args:
            order: Заказ для подтверждения
            user: Пользователь, выполняющий действие
        """
        if not OrderStatusService._can_change_operator_status(user):
            raise PermissionDenied('Только оператор может подтвердить завершение.')
        
        if order.operator_status != Order.OperatorStatus.TRANSFERRED:
            raise ValueError('Заказ должен быть передан менеджеру.')
        
        if order.manager_status != Order.ManagerStatus.DELIVERED:
            raise ValueError('Менеджер должен сдать заказ перед подтверждением.')
        
        order.operator_status = Order.OperatorStatus.SUCCESS
        order.operator_closed_at = timezone.now()
        order.save()
        
        # Отправляем уведомление
        OrderStatusService._send_status_notification(
            order, 
            "✅ Завершён оператором", 
            user,
            "Передан менеджеру"
        )

    @staticmethod
    def manager_accept(order: Order, user) -> None:
        """
        Менеджер принимает заказ в работу.
        
        Args:
            order: Заказ для принятия
            user: Пользователь, выполняющий действие
        """
        if not OrderStatusService._can_change_manager_status(user):
            raise PermissionDenied('Только менеджер может принять заказ.')
        
        if order.operator_status != Order.OperatorStatus.TRANSFERRED:
            raise ValueError('Заказ должен быть передан оператором.')
        
        if order.manager_status != Order.ManagerStatus.WAITING:
            raise ValueError('Заказ должен быть в ожидании.')
        
        order.manager_status = Order.ManagerStatus.IN_PROGRESS
        order.assigned_manager = user
        order.save()
        
        # Отправляем уведомление
        OrderStatusService._send_status_notification(
            order, 
            "📋 Принят менеджером", 
            user,
            "Ожидает"
        )

    @staticmethod
    def manager_move_to_process(order: Order, user) -> None:
        """
        Менеджер переводит заказ в процесс (назначены клинеры).
        
        Args:
            order: Заказ для перевода
            user: Пользователь, выполняющий действие
        """
        import logging
        logger = logging.getLogger(__name__)
        user_role = getattr(user, 'role', 'NO ROLE')
        logger.info(f"[DEBUG manager_move_to_process] user={user}, role={user_role}, order.manager_status={order.manager_status}")
        
        if not OrderStatusService._can_change_manager_status(user):
            logger.error(f"[DEBUG] PermissionDenied: user role={user_role} not in allowed roles")
            raise PermissionDenied('Только менеджер может перевести заказ в процесс.')
        
        if order.manager_status != Order.ManagerStatus.IN_PROGRESS:
            raise ValueError('Заказ должен быть в обработке у менеджера.')
        
        order.manager_status = Order.ManagerStatus.PROCESS
        order.save()
        
        # Генерируем задачи из шаблона чеклиста
        try:
            from apps.tasks.services import TaskChecklistService
            TaskChecklistService.generate_order_tasks(order)
        except Exception as e:
            logger.error(f"[ERROR] Failed to generate order tasks: {e}")
        
        # Отправляем уведомление
        OrderStatusService._send_status_notification(
            order, 
            "🔄 В процессе (назначены клинеры)", 
            user,
            "В обработке"
        )

    @staticmethod
    def manager_mark_review(order: Order, user) -> None:
        """
        Менеджер переводит заказ в статус проверки.
        
        Args:
            order: Заказ для перевода
            user: Пользователь, выполняющий действие
        """
        if not OrderStatusService._can_change_manager_status(user):
            raise PermissionDenied('Только менеджер может перевести заказ на проверку.')
        
        if order.manager_status != Order.ManagerStatus.PROCESS:
            raise ValueError('Заказ должен быть в процессе.')
        
        order.manager_status = Order.ManagerStatus.REVIEW
        order.save()
        
        # Отправляем уведомление
        OrderStatusService._send_status_notification(
            order, 
            "🔍 На проверке", 
            user,
            "В процессе"
        )

    @staticmethod
    def manager_mark_delivered(order: Order, user) -> None:
        """
        Менеджер сдаёт проект.
        
        Args:
            order: Заказ для сдачи
            user: Пользователь, выполняющий действие
        """
        if not OrderStatusService._can_change_manager_status(user):
            raise PermissionDenied('Только менеджер может сдать проект.')
        
        if order.manager_status not in [Order.ManagerStatus.REVIEW, Order.ManagerStatus.PROCESS]:
            raise ValueError('Заказ должен быть на проверке или в процессе.')

        now = timezone.now()

        order.manager_status = Order.ManagerStatus.DELIVERED
        order.manager_closed_at = now

        if order.operator_status != Order.OperatorStatus.SUCCESS:
            order.operator_status = Order.OperatorStatus.SUCCESS
            order.operator_closed_at = now
        order.save()

        from apps.orders.models import OrderEmployee
        from apps.employees.models import EmployeeEarning

        order_employees = OrderEmployee.objects.filter(
            order=order,
            finished_at__isnull=True,
            role_on_order__in=['cleaner', 'senior_cleaner'],
        )
        for oe in order_employees:
            oe.finished_at = now
            oe.save(update_fields=['finished_at'])
        
        # Начисляем оплату клинерам за выполненный заказ
        if order.service:
            from collections import defaultdict
            
            # Словарь для накопления оплаты каждому сотруднику
            employee_earnings = defaultdict(float)
            
            # Начисляем старшему клинеру базовую оплату + бонус
            senior_oe = order.order_employees.filter(role_on_order='senior_cleaner').first()
            if senior_oe and senior_oe.employee:
                base_amount = order.service.senior_cleaner_salary + order.service.senior_cleaner_bonus
                employee_earnings[senior_oe.employee.id] += float(base_amount or 0)
            
            # Начисляем оплату за комнаты на основе того, кто выполнял задачи
            if order.service.checklist:
                for room in order.service.checklist:
                    if not isinstance(room, dict):
                        continue
                    
                    room_name = room.get('name', '').strip()
                    payment = room.get('payment', 0)
                    
                    try:
                        payment = float(payment or 0)
                    except (ValueError, TypeError):
                        payment = 0
                    
                    if payment <= 0:
                        continue
                    
                    # Находим задачи этой комнаты
                    room_description = f'Комната: {room_name}' if room_name else ''
                    room_tasks = order.tasks.filter(description=room_description)
                    
                    # Находим всех уникальных клинеров, назначенных на задачи этой комнаты
                    assigned_employee_ids = list(
                        room_tasks.filter(
                            assigned_employees__isnull=False
                        ).values_list('assigned_employees__id', flat=True).distinct()
                    )
                    
                    # Делим оплату комнаты между всеми назначенными клинерами
                    if assigned_employee_ids:
                        payment_per_employee = payment / len(assigned_employee_ids)
                        for emp_id in assigned_employee_ids:
                            employee_earnings[emp_id] += payment_per_employee
            
            # Создаем записи начислений для каждого сотрудника
            from apps.employees.models import Employee
            for emp_id, total_amount in employee_earnings.items():
                if total_amount > 0:
                    employee = Employee.objects.filter(id=emp_id).first()
                    if employee:
                        # Определяем роль сотрудника в заказе
                        oe = order.order_employees.filter(employee_id=emp_id).first()
                        role = oe.role_on_order if oe else 'cleaner'
                        
                        EmployeeEarning.objects.get_or_create(
                            employee=employee,
                            order=order,
                            defaults={
                                'role_on_order': role,
                                'amount': total_amount,
                                'earned_at': now,
                                'is_paid': False
                            }
                        )
        
        # Отправляем уведомление
        OrderStatusService._send_status_notification(
            order, 
            "📦 Сдан менеджером", 
            user,
            "На проверке"
        )

    @staticmethod
    def senior_accept(order: Order, user) -> None:
        """
        Старший клинер принимает заказ.
        
        Args:
            order: Заказ для принятия
            user: Пользователь, выполняющий действие
        """
        if not OrderStatusService._can_change_senior_status(user):
            raise PermissionDenied('Только старший клинер может принять заказ.')
        
        if order.senior_cleaner_status != Order.SeniorCleanerStatus.WAITING:
            raise ValueError('Заказ должен быть в ожидании.')
        
        order.senior_cleaner_status = Order.SeniorCleanerStatus.ACCEPTED
        order.save()
        
        # Отправляем уведомление
        OrderStatusService._send_status_notification(
            order, 
            "✋ Принят старшим клинером", 
            user,
            "Ожидает"
        )

    @staticmethod
    def senior_start_work(order: Order, user) -> None:
        """
        Старший клинер начинает работу.
        
        Args:
            order: Заказ для начала работы
            user: Пользователь, выполняющий действие
        """
        if not OrderStatusService._can_change_senior_status(user):
            raise PermissionDenied('Только старший клинер может начать работу.')
        
        if order.senior_cleaner_status != Order.SeniorCleanerStatus.ACCEPTED:
            raise ValueError('Заказ должен быть принят.')
        
        order.senior_cleaner_status = Order.SeniorCleanerStatus.WORKING
        order.save()
        
        # Отправляем уведомление
        OrderStatusService._send_status_notification(
            order, 
            "🧹 Начата работа клинером", 
            user,
            "Принят"
        )

    @staticmethod
    def senior_send_for_review(order: Order, user) -> None:
        """
        Старший клинер отправляет заказ на проверку менеджеру.
        
        Args:
            order: Заказ для отправки на проверку
            user: Пользователь, выполняющий действие
        """
        if not OrderStatusService._can_change_senior_status(user):
            raise PermissionDenied('Только старший клинер может отправить на проверку.')
        
        if order.senior_cleaner_status != Order.SeniorCleanerStatus.WORKING:
            raise ValueError('Заказ должен быть в работе.')
        
        now = timezone.now()
        
        order.senior_cleaner_status = Order.SeniorCleanerStatus.SENT_FOR_REVIEW
        order.ready_for_review_at = now
        order.ready_for_review_by = user
        order.save()
        
        # Останавливаем таймер — устанавливаем finished_at для старшего клинера
        from apps.orders.models import OrderEmployee
        senior_oe = OrderEmployee.objects.filter(
            order=order,
            role_on_order='senior_cleaner',
            finished_at__isnull=True
        ).first()
        if senior_oe:
            senior_oe.finished_at = now
            senior_oe.save(update_fields=['finished_at'])
        
        # Автоматически переводим менеджера на проверку
        if order.manager_status == Order.ManagerStatus.PROCESS:
            order.manager_status = Order.ManagerStatus.REVIEW
            order.save()
        
        # Отправляем уведомление
        OrderStatusService._send_status_notification(
            order, 
            "📤 Отправлен на проверку", 
            user,
            "В работе"
        )

    @staticmethod
    def recalculate_main_status(order: Order) -> None:
        """
        Пересчитывает главный статус заказа.
        
        Этот метод вызывается автоматически при сохранении заказа,
        но может быть вызван и вручную при необходимости.
        
        Args:
            order: Заказ для пересчёта статуса
        """
        order._recalculate_main_status()
        order.save(update_fields=['status'])

    @staticmethod
    def _can_change_operator_status(user) -> bool:
        """Проверяет, может ли пользователь изменять статус оператора."""
        if user.is_superuser:
            return True
        if hasattr(user, 'role'):
            return user.role in ['OPERATOR', 'FOUNDER', 'SUPER_ADMIN']
        return False

    @staticmethod
    def _can_change_manager_status(user) -> bool:
        """Проверяет, может ли пользователь изменять статус менеджера."""
        if user.is_superuser:
            return True
        if hasattr(user, 'role'):
            return user.role in ['MANAGER', 'FOUNDER', 'SUPER_ADMIN']
        return False

    @staticmethod
    def _can_change_senior_status(user) -> bool:
        """Проверяет, может ли пользователь изменять статус старшего клинера."""
        if user.is_superuser:
            return True
        if hasattr(user, 'role'):
            return user.role in ['SENIOR_CLEANER', 'FOUNDER', 'SUPER_ADMIN']
        return False


class OrderStatusChecker:
    """Утилиты для проверки доступных действий по статусам."""

    @staticmethod
    def get_operator_actions(order: Order, user) -> dict:
        """
        Возвращает доступные действия для оператора.
        
        Returns:
            dict с булевыми значениями для каждого действия:
            - can_reject: Может ли отменить
            - can_transfer: Может ли передать менеджеру
            - can_confirm_success: Может ли подтвердить завершение
        """
        if not OrderStatusService._can_change_operator_status(user):
            return {'can_reject': False, 'can_transfer': False, 'can_confirm_success': False}
        
        return {
            'can_reject': order.operator_status == Order.OperatorStatus.IN_PROGRESS,
            'can_transfer': order.operator_status == Order.OperatorStatus.IN_PROGRESS,
            'can_confirm_success': (
                order.operator_status == Order.OperatorStatus.TRANSFERRED and
                order.manager_status == Order.ManagerStatus.DELIVERED
            ),
        }

    @staticmethod
    def get_manager_actions(order: Order, user) -> dict:
        """
        Возвращает доступные действия для менеджера.
        
        Returns:
            dict с булевыми значениями для каждого действия:
            - can_accept: Может ли принять
            - can_assign: Может ли назначить сотрудников
            - can_move_to_process: Может ли перевести в процесс
            - can_deliver: Может ли сдать проект
        """
        if not OrderStatusService._can_change_manager_status(user):
            return {
                'can_accept': False,
                'can_assign': False,
                'can_move_to_process': False,
                'can_deliver': False,
            }
        
        return {
            'can_accept': (
                order.operator_status == Order.OperatorStatus.TRANSFERRED and
                order.manager_status == Order.ManagerStatus.WAITING
            ),
            'can_assign': order.manager_status in [
                Order.ManagerStatus.IN_PROGRESS,
                Order.ManagerStatus.PROCESS
            ],
            'can_move_to_process': order.manager_status == Order.ManagerStatus.IN_PROGRESS,
            'can_deliver': order.manager_status in [Order.ManagerStatus.REVIEW, Order.ManagerStatus.PROCESS],
        }

    @staticmethod
    def get_senior_actions(order: Order, user) -> dict:
        """
        Возвращает доступные действия для старшего клинера.
        
        Returns:
            dict с булевыми значениями для каждого действия:
            - can_accept: Может ли принять
            - can_start_work: Может ли начать работу
            - can_send_for_review: Может ли отправить на проверку
        """
        if not OrderStatusService._can_change_senior_status(user):
            return {
                'can_accept': False,
                'can_start_work': False,
                'can_send_for_review': False,
            }
        
        return {
            'can_accept': order.senior_cleaner_status == Order.SeniorCleanerStatus.WAITING,
            'can_start_work': order.senior_cleaner_status == Order.SeniorCleanerStatus.ACCEPTED,
            'can_send_for_review': order.senior_cleaner_status == Order.SeniorCleanerStatus.WORKING,
        }
