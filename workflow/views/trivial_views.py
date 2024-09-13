from django.views.generic import TemplateView


class IndexView(TemplateView):
    template_name: str = "workflow/index.html"


class AboutView(TemplateView):
    template_name: str = "workflow/about.html"
