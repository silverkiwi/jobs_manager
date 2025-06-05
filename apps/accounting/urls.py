from django.urls import path

import apps.accounting.views as submit_quote_view

app_name = "accounting"

urlpatterns = [
    path(
        "api/quote/<uuid:job_id>/pdf-preview/",
        submit_quote_view.generate_quote_pdf,
        name="generate_quote_pdf",
    ),
    path(
        "api/quote/<uuid:job_id>/send-email/",
        submit_quote_view.send_quote_email,
        name="send_quote_email",
    ),
]
