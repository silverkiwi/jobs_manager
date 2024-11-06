import os

import django
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from workflow.models import Job, JobPricing, MaterialEntry, TimeEntry, AdjustmentEntry
from dotenv import load_dotenv


django.setup()  # Force initialization
load_dotenv()


class SimpleTest(TestCase):
    def test_basic(self) -> None:
        self.assertTrue(True)


class JobApiTests(TestCase):
    def setUp(self):
        # Log in with the new test user (corrin+autotest)
        self.client = Client()
        login_successful = self.client.login(
            email="corrin+testing@morrissheetmetal.co.nz",
            password=os.getenv("DB_PASSWORD", "abcde"),
        )
        assert login_successful, "Test user login failed in setUp."

        # Create a job for testing
        self.job = Job.objects.create()

        # Create job pricing entries for estimate, quote, and reality
        self.estimate_pricing = JobPricing.objects.create(
            job=self.job, pricing_stage="estimate", pricing_type="time_and_materials"
        )
        self.quote_pricing = JobPricing.objects.create(
            job=self.job, pricing_stage="quote", pricing_type="fixed"
        )
        self.reality_pricing = JobPricing.objects.create(
            job=self.job, pricing_stage="reality", pricing_type="time_and_materials"
        )

        # Create related adjustment entries for the estimate pricing
        self.adjustment_entry = AdjustmentEntry.objects.create(
            job_pricing=self.estimate_pricing,
            description="Test adjustment description",
            cost_adjustment=100,
            price_adjustment=150,
        )

        # Create related material and time entries if necessary for testing
        self.material_entry = MaterialEntry.objects.create(
            job_pricing=self.quote_pricing,
            item_code="MAT1",
            description="Material A",
            quantity=3.0,
            unit_cost=30.0,
            unit_revenue=36.0,
        )

        self.time_entry = TimeEntry.objects.create(
            job_pricing=self.reality_pricing,
            description="Time entry description",
            items=2,
            mins_per_item=60,
            wage_rate=32.0,
            charge_out_rate=105.0,
        )

        self.client = Client()

    def test_job_has_estimate_pricing(self):
        # Test if the job correctly returns the estimate pricing
        self.assertEqual(self.job.latest_estimate_pricing, self.estimate_pricing)

    def test_job_has_quote_pricing(self):
        # Test if the job correctly returns the quote pricing
        self.assertEqual(self.job.latest_quote_pricing, self.quote_pricing)

    def test_job_has_reality_pricing(self):
        # Test if the job correctly returns the reality pricing
        self.assertEqual(self.job.latest_reality_pricing, self.reality_pricing)

    def test_get_job_api_success(self):
        # Simulate an API request to get job details
        response = self.client.get(reverse("get_job_api"), {"job_id": self.job.id})
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue("estimate_pricing" in response_data)
        self.assertTrue("quote_pricing" in response_data)
        self.assertTrue("reality_pricing" in response_data)

    def test_get_job_api_not_found(self):
        # Test with a non-existent job_id
        response = self.client.get(
            reverse("get_job_api"), {"job_id": "non-existent-id"}
        )
        self.assertEqual(response.status_code, 404)
