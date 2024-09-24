from typing import Any, Dict

from django.views.generic import TemplateView


class DashboardView(TemplateView):
    template_name: str = "general/dashboard.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        # You can add any additional context data here if needed
        return context
