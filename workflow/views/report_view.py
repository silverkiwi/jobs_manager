from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from workflow.api.reports.company_profit_loss import get_company_profit_loss_data

class ReportCompanyProfitAndLoss(APIView):
    def get(self, request):
        data = get_company_profit_loss_data()
        return Response(data)


class CompanyProfitAndLossView(TemplateView):
    template_name = 'reports/report_company_profit_and_loss.html'
