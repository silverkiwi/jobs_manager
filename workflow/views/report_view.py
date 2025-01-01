from django.views.generic import TemplateView


class ReportsIndexView(TemplateView):
    template_name = "reports/reports_index.html"


class CompanyProfitAndLossView(TemplateView):
    template_name = "reports/report_company_profit_and_loss.html"
