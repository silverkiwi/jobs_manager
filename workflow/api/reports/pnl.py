from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum

from workflow.models import BillLineItem, InvoiceLineItem
from .utils import format_period_label


class CompanyProfitAndLossReport(APIView):
    """
    API endpoint for company-wide profit and loss report.
    A separate endpoint will handle job-specific P&L reports.
    """

    def categorize_transaction(self, transaction_type: str, item, report: dict,
                               compare_periods: int, period_index: int):
        """
        Categorize a transaction into the appropriate report category.

        Args:
            transaction_type: Type of transaction ("Invoices" or "Bills")
            item: Transaction item containing account details and total
            report: Report dictionary to update
            compare_periods: Number of comparison periods
            period_index: Current period index
        """
        account_type = item.get("account__account_type")
        account_name = item["account__account_name"]
        total = item["total"]

        # Special cases first
        if account_name == "Amortisation":
            report.setdefault("irrelevant", {}).setdefault(account_name,
                                                           [0] * (compare_periods + 1))[
                period_index] = total
            return

        if account_name.startswith(("Opening Stock", "Closing Stock")):
            report.setdefault("ird_included", {}).setdefault(account_name, [0] * (
                        compare_periods + 1))[period_index] = total
            return

        # Regular categorization
        match account_type:
            case "AccountType.REVENUE":
                report["income"][account_name][period_index] = total
            case "AccountType.DIRECTCOSTS":
                report["cost_of_sales"][account_name][period_index] = total
            case "AccountType.EXPENSE" | "AccountType.OVERHEADS":
                report["expenses"][account_name][period_index] = total
            case None:
                report["unclassified"].setdefault(transaction_type, []).append(
                    {"name": account_name, "total": total}
                )
            case _:
                report["unexpected"].setdefault(transaction_type, []).append(
                    {"name": account_name, "type": account_type, "total": total}
                )

    def get(self, request):
        # Input parameters
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        compare_periods = int(request.query_params.get("compare", 0))
        period_type = request.query_params.get("period_type",
                                               "month")  # default to month

        # Generate date ranges
        date_ranges = []
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")

        for i in range(compare_periods + 1):
            if period_type == "day":
                period_start = start_date - timedelta(days=i)
                period_end = end_date - timedelta(days=i)
            elif period_type == "month":
                period_start = (start_date - relativedelta(months=i)).replace(day=1)
                period_end = (start_date - relativedelta(months=i - 1)).replace(
                    day=1) - timedelta(days=1)
            elif period_type == "quarter":
                period_start = (start_date - relativedelta(months=3 * i)).replace(day=1)
                period_end = (start_date - relativedelta(months=3 * (i - 1))).replace(
                    day=1) - timedelta(days=1)
            elif period_type == "year":
                period_start = (start_date - relativedelta(years=i))
                period_end = (end_date - relativedelta(years=i))

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

            # Process all transactions
            for item in invoice_rollup:
                self.categorize_transaction("Invoices", item, report, compare_periods,
                                            i)

            for item in bill_rollup:
                self.categorize_transaction("Bills", item, report, compare_periods, i)

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