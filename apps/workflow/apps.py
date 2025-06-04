from django.apps import AppConfig


class WorkflowConfig(AppConfig):
    """Configuration for the Workflow application."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.workflow'
    verbose_name = 'Workflow'
