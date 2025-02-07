import decimal
import json
import os
from decimal import Decimal

from jobs_manager.settings import DROPBOX_WORKFLOW_FOLDER
from workflow.models.company_defaults import CompanyDefaults


def get_company_defaults():
    """Retrieve the single CompanyDefaults instance, or create if it doesn't exist."""
    defaults, created = CompanyDefaults.objects.get_or_create(
        defaults={
            "time_markup": 0.0,
            "materials_markup": 0.0,
            "charge_out_rate": 105.00,
            "wage_rate": 32.00,
        }
    )
    return defaults


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def decimal_to_float(value):
    return float(value) if isinstance(value, Decimal) else value


def get_job_folder_path(job_number):
    """Get the absolute filesystem path for a job's folder."""
    return os.path.join(DROPBOX_WORKFLOW_FOLDER, f"Job-{job_number}")
