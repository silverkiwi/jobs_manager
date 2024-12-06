from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, F
from workflow.models.invoice import BillLineItem, InvoiceLineItem, CreditNoteLineItem
from .utils import format_period_label


class CompanyProfitAndLossReport(APIView):
    def categorize_transaction(self, transaction_type: str, item, report: dict,
                               compare_periods: int, period_index: int):
        account_type = item.get("account__account_type")
        account_name = item["account__account_name"]
        total = item["total"]

        match account_type:
            case "AccountType.REVENUE":
                report["income"].setdefault(account_name, [0] * (compare_periods + 1))[period_index] += total
            case "AccountType.DIRECTCOSTS":
                report["cost_of_sales"].setdefault(account_name, [0] * (compare_periods + 1))[period_index] += total
            case "AccountType.EXPENSE" | "AccountType.OVERHEADS":
                report["expenses"].setdefault(account_name, [0] * (compare_periods + 1))[period_index] += total
            case None:
                report["unclassified"].setdefault(transaction_type, []).append(
                    {"name": account_name, "total": total}
                )
            case _:
                report["unexpected"].setdefault(transaction_type, []).append(
                    {"name": account_name, "type": account_type, "total": total}
                )

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        compare_periods = int(request.query_params.get("compare", 0))
        period_type = request.query_params.get("period_type", "month")

        date_ranges = []
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")

        for i in range(compare_periods + 1):
            if period_type == "day":
                period_start = start_date - timedelta(days=i)
                period_end = end_date - timedelta(days=i)
            elif period_type == "month":
                period_start = (start_date - relativedelta(months=i)).replace(day=1)
                period_end = (start_date - relativedelta(months=i - 1)).replace(day=1) - timedelta(days=1)
            elif period_type == "quarter":
                period_start = (start_date - relativedelta(months=3 * i)).replace(day=1)
                period_end = (start_date - relativedelta(months=3 * (i - 1))).replace(day=1) - timedelta(days=1)
            elif period_type == "year":
                period_start = start_date - relativedelta(years=i)
                period_end = end_date - relativedelta(years=i)

            date_ranges.append((period_start, period_end))

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

            # Invoice and credit note rollup
            invoice_rollup = (
                InvoiceLineItem.objects.filter(
                    invoice__date__range=[period_start, period_end]
                )
                .values("account__account_type", "account__account_name")
                .annotate(total=Sum("line_amount_excl_tax"))
            )

            credit_note_rollup = (
                CreditNoteLineItem.objects.filter(
                    credit_note__date__range=[period_start, period_end]
                )
                .values("account__account_type", "account__account_name")
                .annotate(total=Sum(F("line_amount_excl_tax") * -1))
            )

            trading_income_rollup = {}
            for item in invoice_rollup:
                key = (item["account__account_type"], item["account__account_name"])
                trading_income_rollup[key] = item["total"]

            for item in credit_note_rollup:
                key = (item["account__account_type"], item["account__account_name"])
                trading_income_rollup[key] = trading_income_rollup.get(key, 0) + item["total"]

            for (account_type, account_name), total in trading_income_rollup.items():
                self.categorize_transaction("Invoices", {"account__account_type": account_type, "account__account_name": account_name, "total": total}, report, compare_periods, i)

            # Bill and supplier credit note rollup
            bill_rollup = (
                BillLineItem.objects.filter(
                    bill__date__range=[period_start, period_end]
                )
                .values("account__account_name", "account__account_type")
                .annotate(total=Sum("line_amount_excl_tax"))
            )

            supplier_credit_rollup = (
                CreditNoteLineItem.objects.filter(
                    credit_note__date__range=[period_start, period_end]
                )
                .values("account__account_name", "account__account_type")
                .annotate(total=Sum(F("line_amount_excl_tax") * -1))
            )

            combined_bill_rollup = {}
            for item in bill_rollup:
                key = (item["account__account_type"], item["account__account_name"])
                combined_bill_rollup[key] = item["total"]

            for item in supplier_credit_rollup:
                key = (item["account__account_type"], item["account__account_name"])
                combined_bill_rollup[key] = combined_bill_rollup.get(key, 0) + item["total"]

            for (account_type, account_name), total in combined_bill_rollup.items():
                self.categorize_transaction("Bills", {"account__account_type": account_type, "account__account_name": account_name, "total": total}, report, compare_periods, i)

            # Gross Profit Calculation
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
