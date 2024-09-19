from workflow.models import Bill, Invoice
from django.db.models import Sum
from datetime import datetime


def get_company_profit_loss_data():
    months = ["Jan 2024", "Feb 2024", "Mar 2024", "Apr 2024"]  # This should be dynamic
    categories = {
        "Income": {
            "Sales": [],
            "Other Revenue": []
        },
        "Cost of Sales": {
            "Purchases": [],
            "Wages": []
        },
        "Operating Expenses": {
            "Rent": [],
            "Utilities": []
        }
    }

    # Example data fetching logic (adjust based on your actual models)
    for month in months:
        start_date = datetime.strptime(f"01 {month}", '%d %b %Y')
        end_date = start_date.replace(day=28)  # Simplified for example

        # Replace 'amount' with 'total' (or any other correct field)
        income_sales = Invoice.objects.filter(date__range=(start_date, end_date)).aggregate(Sum('total'))['total__sum'] or 0
        categories["Income"]["Sales"].append(income_sales)

        cost_purchases = Bill.objects.filter(category="Purchases", date__range=(start_date, end_date)).aggregate(Sum('total'))['total__sum'] or 0
        categories["Cost of Sales"]["Purchases"].append(cost_purchases)

    return {
        "months": months,
        "categories": categories
    }
