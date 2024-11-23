from datetime import datetime, timedelta
import calendar

from django.db.models import Sum
from django.views.generic import TemplateView
from rest_framework.response import Response
from rest_framework.views import APIView

from workflow.models import BillLineItem, InvoiceLineItem


def format_period_label(period_start, period_end):
    # If it's a single day
    if period_start == period_end:
        return period_start.strftime("%d %b %Y")

    # If it's a whole month (1st to last day)
    if (period_start.day == 1 and
        period_end.day == calendar.monthrange(period_end.year, period_end.month)[1]):
        return period_start.strftime("%b %Y")

    # If it's a fiscal year (assuming April 1 to March 31)
    if (period_start.month == 4 and period_start.day == 1 and
            period_end.month == 3 and period_end.day == 31):
        return f"FY {period_end.year}"

    # Otherwise show date range
    return f"{period_start.strftime('%d %b %Y')} - {period_end.strftime('%d %b %Y')}"


# Then use it:
class ReportCompanyProfitAndLoss(APIView):
    def get(self, request):
        # Input parameters
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        compare_periods = int(request.query_params.get("compare", 0))
        days_delta = request.query_params.get("period_days_delta",30)

        # Generate date ranges
        date_ranges = []
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        for i in range(compare_periods + 1):
            period_start = start_date - timedelta(days=days_delta * i)
            period_end = end_date - timedelta(days=days_delta * i)
            date_ranges.append((period_start, period_end))

        # Initialize report structure
        report = {
            "periods": [],
            "income": {},
            "cost_of_sales": {},
            "expenses": {},
            "ird_included": {},
            "irrelevant": {},
            "unclassified": {},
            "unexpected": {},
            "totals": {"gross_profit": []},
        }

        for i, (period_start, period_end) in enumerate(date_ranges):
            report["periods"].append(format_period_label(period_start, period_end))

            # Invoice rollup aggregation
            invoice_rollup = (
                InvoiceLineItem.objects.filter(
                    invoice__date__range=[period_start, period_end]
                )
                .values("account__account_name", "account__account_type")
                .annotate(total=Sum("line_amount_excl_tax"))
            )

            # Bill rollup aggregation
            bill_rollup = (
                BillLineItem.objects.filter(
                    bill__date__range=[period_start, period_end]
                )
                .values("account__account_name", "account__account_type")
                .annotate(total=Sum("line_amount_excl_tax"))
            )

            # Initialize period arrays for all accounts
            for item in invoice_rollup:
                account_name = item["account__account_name"]
                if account_name not in report["income"]:
                    report["income"][account_name] = [0] * (compare_periods + 1)

            for item in bill_rollup:
                account_name = item["account__account_name"]
                if account_name not in report["cost_of_sales"]:
                    report["cost_of_sales"][account_name] = [0] * (compare_periods + 1)
                if account_name not in report["expenses"]:
                    report["expenses"][account_name] = [0] * (compare_periods + 1)

            # Categorize invoice and bill rollups
            def categorize_transaction(transaction_type: str, item):
                account_type = item.get("account__account_type")
                account_name = item["account__account_name"]
                total = item["total"]

                # Special cases first
                if account_name == "Amortisation":
                    report.setdefault("irrelevant", {}).setdefault(account_name, [0] * (
                                compare_periods + 1))[i] = total
                    return

                if account_name.startswith(("Opening Stock", "Closing Stock")):
                    report.setdefault("ird_included", {}).setdefault(account_name,
                                                                     [0] * (
                                                                                 compare_periods + 1))[
                        i] = total
                    return

                # Regular categorization
                match account_type:
                    case "AccountType.REVENUE":
                        report["income"][account_name][i] = total
                    case "AccountType.DIRECTCOSTS":
                        report["cost_of_sales"][account_name][i] = total
                    case "AccountType.EXPENSE" | "AccountType.OVERHEADS":
                        report["expenses"][account_name][i] = total
                    case None:
                        report["unclassified"].setdefault(transaction_type, []).append(
                            {"name": account_name, "total": total}
                        )
                    case _:
                        report["unexpected"].setdefault(transaction_type, []).append(
                            {"name": account_name, "type": account_type, "total": total}
                        )


            # Process all transactions
            for item in invoice_rollup:
                categorize_transaction("Invoices", item)

            for item in bill_rollup:
                categorize_transaction("Bills", item)

            # Calculate Gross Profit
            total_income = sum(
                report["income"].get(account, [0] * (compare_periods + 1))[i]
                for account in report["income"]
            )
            total_cogs = sum(
                report["cost_of_sales"].get(account, [0] * (compare_periods + 1))[i]
                for account in report["cost_of_sales"]
            )
            gross_profit = total_income - total_cogs
            report["totals"]["gross_profit"].append(gross_profit)

        return Response(report)

class CompanyProfitAndLossView(TemplateView):
    template_name = "reports/report_company_profit_and_loss.html"
