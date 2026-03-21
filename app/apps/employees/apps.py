from django.apps import AppConfig


class EmployeesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.employees'
    verbose_name = 'Сотрудники'

    def ready(self):
        from . import signals  # noqa: F401
