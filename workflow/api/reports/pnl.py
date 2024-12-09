from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, F
from workflow.models.invoice import BillLineItem, InvoiceLineItem, CreditNoteLineItem
from workflow.models.xero_journal import XeroJournalLineItem
from workflow.api.reports.utils import format_period_label
class CompanyProfitAndLossReport(APIView):
    equity_movement_accounts = {
        "Opening Stock",
        "Opening Stock - Work in Progress",
        "Closing Stock",
        "Closing Stock - Work in Progress",
        "Amortisation",
    }

    def categorize_transaction(self, transaction_type: str, item, report: dict, compare_periods: int, period_index: int):
        """
        Categorize a single transaction based on its account name.
        """
        account_name = item["account__account_name"]
        total = item["total"]

        if account_name in self.equity_movement_accounts:
            report["equity_movements"].setdefault(account_name,
                                                  [0] * (compare_periods + 1))[
                period_index] += total
        elif transaction_type == "income":
            report["income"].setdefault(account_name, [0] * (compare_periods + 1))[
                period_index] += total
        elif transaction_type == "expense":
            report["expenses"].setdefault(account_name, [0] * (compare_periods + 1))[
                period_index] += total
        elif transaction_type == "cost_of_sales":
            report["cost_of_sales"].setdefault(account_name,
                                               [0] * (compare_periods + 1))[
                period_index] += total
        else:
            report["unclassified"].setdefault(transaction_type, []).append({
                "name": account_name, "total": total
            })

    def rollup_line_items(self, period_start, period_end):
        """
        Roll up line items for all document types into a single dictionary.
        """
        # Roll up for each document type
        invoice_rollup = InvoiceLineItem.objects.filter(
            invoice__date__range=[period_start, period_end]
        ).values("account__account_type", "account__account_name").annotate(total=Sum("line_amount_excl_tax"))

        bill_rollup = BillLineItem.objects.filter(
            bill__date__range=[period_start, period_end]
        ).values("account__account_type", "account__account_name").annotate(total=Sum("line_amount_excl_tax"))

        credit_note_rollup = CreditNoteLineItem.objects.filter(
            credit_note__date__range=[period_start, period_end]
        ).values("account__account_type", "account__account_name").annotate(total=Sum(F("line_amount_excl_tax") * -1))

        journal_rollup = XeroJournalLineItem.objects.filter(
            journal__journal_date__range=[period_start, period_end]
        ).values("account__account_type", "account__account_name").annotate(total=Sum("net_amount"))

        # Consolidate all rollups
        consolidated_rollup = {}

        def merge_rollup(source):
            for item in source:
                key = (item["account__account_type"], item["account__account_name"])
                consolidated_rollup[key] = consolidated_rollup.get(key, 0) + item["total"]

        # Only roll up journals as every invoice is also a journal!
        # merge_rollup(invoice_rollup)
        # merge_rollup(bill_rollup)
        # merge_rollup(credit_note_rollup)
        merge_rollup(journal_rollup)

        return consolidated_rollup

    def calculate_totals(self, report, compare_periods, period_index):
        """
        Calculate sales, COGS, gross profit, operating expenses, equity movements, and profits.
        """
        total_sales = sum(
            report["income"].get(account, [0] * (compare_periods + 1))[period_index]
            for account in report["income"]
        )
        total_cogs = sum(
            report["cost_of_sales"].get(account, [0] * (compare_periods + 1))[
                period_index]
            for account in report["cost_of_sales"]
        )
        gross_profit = total_sales - total_cogs
        total_expenses = sum(
            report["expenses"].get(account, [0] * (compare_periods + 1))[period_index]
            for account in report["expenses"]
        )
        total_equity_movements = sum(
            report["equity_movements"].get(account, [0] * (compare_periods + 1))[
                period_index]
            for account in report["equity_movements"]
        )
        net_profit = gross_profit - total_expenses
        accounting_profit = net_profit - total_equity_movements

        return {
            "sales": total_sales,
            "cogs": total_cogs,
            "gross_profit": gross_profit,
            "operating_expenses": total_expenses,
            "equity_movements": total_equity_movements,
            "net_profit": net_profit,
            "accounting_profit": accounting_profit,
        }

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
            "equity_movements": {},
            "unclassified": {},
            "unexpected": {},
            "totals": {
                "sales": [],
                "cogs": [],
                "gross_profit": [],
                "operating_expenses": [],
                "equity_movements": [],
                "net_profit": [],
                "accounting_profit": [],
            },
        }

        for i, (period_start, period_end) in enumerate(date_ranges):
            report["periods"].append(format_period_label(period_start, period_end))

            # Get consolidated rollup for the period
            consolidated_rollup = self.rollup_line_items(period_start, period_end)

            # Categorize transactions
            for (account_type, account_name), total in consolidated_rollup.items():
                self.categorize_transaction(
                    "Combined",
                    {"account__account_type": account_type, "account__account_name": account_name, "total": total},
                    report,
                    compare_periods,
                    i
                )

            # Calculate totals and append to report
            totals = self.calculate_totals(report, compare_periods, i)
            for key, value in totals.items():
                report["totals"][key].append(value)

        return Response(report)
