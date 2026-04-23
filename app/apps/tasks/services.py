"""
Service layer для управления чеклистами задач (Task Checklist System).
"""
from typing import List, Optional
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.orders.models import Order
from apps.employees.models import Employee
from .models import ChecklistTemplate, ChecklistTemplateTask, OrderTask, OrderTaskStatus


User = get_user_model()


class TaskChecklistService:
    """Сервис для генерации и управления задачами заказов."""
    
    @staticmethod
    def generate_order_tasks(order: Order) -> List[OrderTask]:
        """
        Генерирует задачи для заказа из шаблона услуги.
        
        Args:
            order: Заказ для которого нужно сгенерировать задачи
        
        Returns:
            Список созданных OrderTask
        """
        # Проверяем, есть ли уже задачи у заказа
        if order.tasks.exists():
            return list(order.tasks.all())
        
        # Ищем активный шаблон для услуги
        template = ChecklistTemplate.objects.filter(
            service=order.service,
            is_active=True
        ).first()
        
        if not template:
            return []
        
        # Получаем активные задачи из шаблона
        template_tasks = template.tasks.filter(is_active=True).order_by('order')
        
        created_tasks = []
        for template_task in template_tasks:
            order_task = OrderTask.objects.create(
                order=order,
                title=template_task.title,
                description=template_task.description,
                order_position=template_task.order,
                status=OrderTaskStatus.PENDING
            )
            created_tasks.append(order_task)
        
        return created_tasks
    
    @staticmethod
    @transaction.atomic
    def regenerate_order_tasks(order: Order) -> List[OrderTask]:
        """
        Перегенерирует задачи заказа (удаляет старые, создает новые из шаблона).
        Используется когда меняется услуга заказа.
        
        Args:
            order: Заказ для которого нужно перегенерировать задачи
        
        Returns:
            Список созданных OrderTask
        """
        # Удаляем существующие задачи
        order.tasks.all().delete()
        
        # Генерируем новые
        return TaskChecklistService.generate_order_tasks(order)
    
    @staticmethod
    def assign_task_to_employee(
        task: OrderTask,
        employee: Employee,
        assigned_by: Optional[User] = None
    ) -> OrderTask:
        """
        Назначает задачу сотруднику.
        
        Args:
            task: Задача заказа
            employee: Сотрудник для назначения
            assigned_by: Кто назначил задачу
        
        Returns:
            Обновленная задача
        """
        task.assigned_employees.add(employee)
        return task
    
    @staticmethod
    def start_task(task: OrderTask, user: Optional[User] = None) -> OrderTask:
        """
        Начать выполнение задачи.
        
        Args:
            task: Задача заказа
            user: Пользователь который начал задачу
        
        Returns:
            Обновленная задача
        """
        task.start(user)
        return task
    
    @staticmethod
    def complete_task(task: OrderTask, user: Optional[User] = None) -> OrderTask:
        """
        Отметить задачу как выполненную.
        
        Args:
            task: Задача заказа
            user: Пользователь который завершил задачу
        
        Returns:
            Обновленная задача
        """
        task.complete(user)
        return task
    
    @staticmethod
    def skip_task(task: OrderTask, user: Optional[User] = None) -> OrderTask:
        """
        Пропустить задачу.
        
        Args:
            task: Задача заказа
            user: Пользователь который пропустил задачу
        
        Returns:
            Обновленная задача
        """
        task.skip(user)
        return task
    
    @staticmethod
    def reset_task(task: OrderTask) -> OrderTask:
        """
        Сбросить задачу в начальное состояние.
        
        Args:
            task: Задача заказа
        
        Returns:
            Обновленная задача
        """
        task.reset()
        return task
    
    @staticmethod
    def get_order_task_stats(order: Order) -> dict:
        """
        Получает статистику выполнения задач заказа.
        
        Args:
            order: Заказ для анализа
        
        Returns:
            Словарь со статистикой
        """
        tasks = order.tasks.all()
        total = tasks.count()
        
        if total == 0:
            return {
                'total': 0,
                'pending': 0,
                'in_progress': 0,
                'done': 0,
                'skipped': 0,
                'completion_percentage': 0,
                'is_fully_done': False
            }
        
        pending = tasks.filter(status=OrderTaskStatus.PENDING).count()
        in_progress = tasks.filter(status=OrderTaskStatus.IN_PROGRESS).count()
        done = tasks.filter(status=OrderTaskStatus.DONE).count()
        skipped = tasks.filter(status=OrderTaskStatus.SKIPPED).count()
        
        # Процент выполнения (DONE + SKIPPED считается выполненным)
        completed = done + skipped
        completion_percentage = (completed / total) * 100
        
        return {
            'total': total,
            'pending': pending,
            'in_progress': in_progress,
            'done': done,
            'skipped': skipped,
            'completion_percentage': round(completion_percentage, 1),
            'is_fully_done': done == total  # Все задачи выполнены
        }
    
    @staticmethod
    def get_employee_tasks(
        employee: Employee,
        status: Optional[str] = None,
        order: Optional[Order] = None
    ) -> List[OrderTask]:
        """
        Получает задачи назначенные сотруднику.
        
        Args:
            employee: Сотрудник
            status: Фильтр по статусу (опционально)
            order: Фильтр по заказу (опционально)
        
        Returns:
            Список задач
        """
        tasks = OrderTask.objects.filter(assigned_employees=employee)
        
        if status:
            tasks = tasks.filter(status=status)
        
        if order:
            tasks = tasks.filter(order=order)
        
        return list(tasks.order_by('order__scheduled_date', 'order_position'))
    
    @staticmethod
    def create_checklist_template(
        service,
        name: str,
        description: str = "",
        is_active: bool = True
    ) -> ChecklistTemplate:
        """
        Создает новый шаблон чеклиста для услуги.
        
        Args:
            service: Услуга
            name: Название шаблона
            description: Описание
            is_active: Активен ли шаблон
        
        Returns:
            Созданный шаблон
        """
        return ChecklistTemplate.objects.create(
            service=service,
            name=name,
            description=description,
            is_active=is_active
        )
    
    @staticmethod
    def add_task_to_template(
        template: ChecklistTemplate,
        title: str,
        description: str = "",
        order: int = 0,
        is_active: bool = True
    ) -> ChecklistTemplateTask:
        """
        Добавляет задачу в шаблон.
        
        Args:
            template: Шаблон чеклиста
            title: Название задачи
            description: Описание
            order: Порядок
            is_active: Активна ли задача
        
        Returns:
            Созданная задача шаблона
        """
        return ChecklistTemplateTask.objects.create(
            template=template,
            title=title,
            description=description,
            order=order,
            is_active=is_active
        )
    
    @staticmethod
    def copy_template(
        source_template: ChecklistTemplate,
        target_service,
        new_name: Optional[str] = None
    ) -> ChecklistTemplate:
        """
        Копирует шаблон чеклиста для другой услуги.
        
        Args:
            source_template: Исходный шаблон
            target_service: Целевая услуга
            new_name: Новое название (опционально)
        
        Returns:
            Созданный шаблон
        """
        with transaction.atomic():
            # Создаем новый шаблон
            new_template = ChecklistTemplate.objects.create(
                service=target_service,
                name=new_name or f"{source_template.name} (копия)",
                description=source_template.description,
                is_active=source_template.is_active
            )
            
            # Копируем задачи
            for task in source_template.tasks.filter(is_active=True):
                ChecklistTemplateTask.objects.create(
                    template=new_template,
                    title=task.title,
                    description=task.description,
                    order=task.order,
                    is_active=task.is_active
                )
            
            return new_template


# Глобальная функция для использования в signals/views
def generate_order_tasks_on_creation(order: Order) -> List[OrderTask]:
    """
    Утилитарная функция для генерации задач при создании заказа.
    Может быть использована в post_save signal или в view.
    """
    return TaskChecklistService.generate_order_tasks(order)
