from rest_framework.views import APIView
from rest_framework.response import Response
from reports.company_profit_loss import get_company_profit_loss_data

class CompanyProfitAndLossReport(APIView):
    def get(self, request):
        data = get_company_profit_loss_data()
        return Response(data)
