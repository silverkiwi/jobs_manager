"""
Management command to test quote parsing functionality.
Tests both Google Sheets data parsing and populate functionality.
"""

import logging

import pandas as pd
from django.core.management.base import BaseCommand

from apps.job.importers.google_sheets import populate_sheet_from_costset
from apps.job.importers.quote_spreadsheet import _is_valid_item, parse_xlsx
from apps.job.models import Job

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Test quote parsing and Google Sheets functionality"

    def add_arguments(self, parser):
        parser.add_argument(
            "--test-validation",
            action="store_true",
            help="Test the _is_valid_item function with various cases",
        )
        parser.add_argument(
            "--test-parsing",
            action="store_true",
            help="Test quote parsing with simulated Google Sheets data",
        )
        parser.add_argument(
            "--test-populate",
            action="store_true",
            help="Test populating Google Sheets with CostSet data",
        )
        parser.add_argument(
            "--job-id", type=int, help="Job ID to use for testing (optional)"
        )
        parser.add_argument(
            "--sheet-id", type=str, help="Google Sheets ID to use for populate test"
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("🧪 Testing Quote Management System Fixes")
        )

        if options["test_validation"]:
            self.test_validation()

        if options["test_parsing"]:
            self.test_parsing()

        if options["test_populate"]:
            if not options["sheet_id"]:
                self.stdout.write(
                    self.style.ERROR("❌ --sheet-id required for populate test")
                )
                return
            self.test_populate(options["sheet_id"], options.get("job_id"))

    def test_validation(self):
        """Test the _is_valid_item function with various edge cases"""
        self.stdout.write("\n📋 Testing _is_valid_item validation function...")

        test_cases = [
            ({"item": "", "quantity": 5}, True, "Empty item with quantity"),
            ({"item": "1.0", "quantity": 3}, True, "Valid numeric item"),
            (
                {"item": "invalid", "quantity": 2},
                True,
                "Non-numeric item (should auto-assign)",
            ),
            ({"item": "2", "quantity": 0}, False, "Valid item but zero quantity"),
            ({"item": None, "quantity": 4}, True, "None item with quantity"),
            ({"item": "nan", "quantity": 1}, True, "NaN string item"),
            ({"item": "", "quantity": None}, False, "Empty item, no quantity"),
        ]

        passed = 0
        failed = 0

        for test_data, expected, description in test_cases:
            try:
                result = _is_valid_item(test_data)
                if result == expected:
                    self.stdout.write(f"  ✅ {description}: {test_data} → {result}")
                    passed += 1
                else:
                    self.stdout.write(
                        f"  ❌ {description}: {test_data} → {result} (expected {expected})"
                    )
                    failed += 1
            except Exception as e:
                self.stdout.write(f"  💥 {description}: ERROR - {str(e)}")
                failed += 1

        self.stdout.write(f"\n📊 Validation Tests: {passed} passed, {failed} failed")

    def test_parsing(self):
        """Test parsing with simulated Google Sheets data"""
        self.stdout.write("\n🔍 Testing quote parsing with simulated data...")

        # Create simulated DataFrame that mimics Google Sheets return data
        # This simulates the issue where Google Sheets returns empty strings for item numbers
        test_data = {
            "item": ["", "", "1.0", ""],  # Mix of empty and filled item numbers
            "quantity": [5, 3, 2, 4],  # All have valid quantities
            "description": ["Labor work", "Material A", "Service B", "Material C"],
            "kind": ["time", "material", "time", "material"],
            "unit_cost": [0, 50.00, 0, 75.00],
            "labour_minutes": [300, 0, 120, 0],
        }

        df = pd.DataFrame(test_data)
        self.stdout.write(f"📊 Created test DataFrame with {len(df)} rows")
        self.stdout.write("📋 Sample data:")
        for idx, row in df.iterrows():
            self.stdout.write(
                f'  Row {idx}: item="{row["item"]}", qty={row["quantity"]}, desc="{row["description"]}"'
            )

        try:
            # Test the parsing function
            result = parse_xlsx(df)

            self.stdout.write("\n✅ Parsing completed successfully!")
            self.stdout.write("📈 Results summary:")
            self.stdout.write(
                f"  - Draft lines created: {len(result.get('draft_lines', []))}"
            )
            self.stdout.write(
                f"  - Validation report: {result.get('validation_report', {})}"
            )

            # Show draft lines with auto-assigned item numbers
            draft_lines = result.get("draft_lines", [])
            if draft_lines:
                self.stdout.write("\n📝 Draft lines with auto-assigned item numbers:")
                for line in draft_lines:
                    self.stdout.write(
                        f"  - Item {line.get('item', '?')}: {line.get('desc', 'No description')} "
                        f"(qty: {line.get('quantity', 0)})"
                    )

        except Exception as e:
            self.stdout.write(f"❌ Parsing failed: {str(e)}")
            import traceback

            self.stdout.write(traceback.format_exc())

    def test_populate(self, sheet_id, job_id=None):
        """Test populating Google Sheets with ordered item numbers"""
        self.stdout.write(f"\n📤 Testing populate functionality for sheet: {sheet_id}")

        # Find or create a test job
        if job_id:
            try:
                job = Job.objects.get(id=job_id)
                self.stdout.write(
                    f"📋 Using existing job: {job.job_number} - {job.name}"
                )
            except Job.DoesNotExist:
                self.stdout.write(f"❌ Job with ID {job_id} not found")
                return
        else:
            # Use the first available job or create guidance
            job = Job.objects.first()
            if not job:
                self.stdout.write(
                    "❌ No jobs found. Create a job first or use --job-id"
                )
                return
            self.stdout.write(
                f"📋 Using first available job: {job.job_number} - {job.name}"
            )

        # Get or create a cost set for testing
        cost_set = job.estimate_cost_set
        if not cost_set:
            self.stdout.write("❌ Job has no estimate cost set. Cannot test populate.")
            return

        cost_lines = list(cost_set.cost_lines.all())
        if not cost_lines:
            self.stdout.write("❌ Cost set has no cost lines. Cannot test populate.")
            return

        self.stdout.write(f"💰 Found {len(cost_lines)} cost lines in estimate cost set")

        # Show current cost lines before populate
        self.stdout.write("📋 Cost lines (before populate):")
        for line in cost_lines:
            self.stdout.write(f"  - {line.desc}: qty={line.quantity}, kind={line.kind}")

        try:
            # Test the populate function
            populate_sheet_from_costset(sheet_id, cost_set)
            self.stdout.write("✅ Sheet populated successfully!")
            self.stdout.write(
                "📊 Data should now be ordered by quantity (highest first) with sequential item numbers"
            )

        except Exception as e:
            self.stdout.write(f"❌ Populate failed: {str(e)}")
            import traceback

            self.stdout.write(traceback.format_exc())

    def style_result(self, success, message):
        """Helper to style output messages"""
        if success:
            return self.style.SUCCESS(f"✅ {message}")
        else:
            return self.style.ERROR(f"❌ {message}")
