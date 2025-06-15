from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from apps.job.importers.quote_spreadsheet import parse_xlsx
from apps.job.importers.draft import DraftLine


class Command(BaseCommand):
    help = 'Test the quote spreadsheet parser with the Quoting Spreadsheet 2025.xlsx fixture'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='Quoting Spreadsheet 2025.xlsx',
            help='Path to the Excel file (default: Quoting Spreadsheet 2025.xlsx in project root)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output of parsed lines'
        )

    def handle(self, *args, **options):
        # Determine the file path
        file_path = options['file']
        if not Path(file_path).is_absolute():
            # If relative path, assume it's from project root (jobs_manager directory)
            project_root = Path(settings.BASE_DIR)
            file_path = project_root / file_path

        file_path = Path(file_path)
        
        self.stdout.write(f"Testing quote spreadsheet parser with: {file_path}")
        
        # Check if file exists
        if not file_path.exists():
            raise CommandError(f"Spreadsheet not found at {file_path}")

        try:            # Parse the spreadsheet with new function signature
            draft_lines, validation_report = parse_xlsx(str(file_path))
            
            # Create summary from draft_lines
            summary = {
                'total_lines': len(draft_lines),
                'time_lines': len([line for line in draft_lines if line.kind == 'time']),
                'material_lines': len([line for line in draft_lines if line.kind == 'material']),
                'adjust_lines': len([line for line in draft_lines if line.kind == 'adjust']),
                'total_cost': sum(line.total_cost for line in draft_lines),
                'total_revenue': sum(line.total_rev for line in draft_lines),
            }
            lines = draft_lines  # for backward compatibility              # Basic sanity checks
            self.stdout.write(self.style.SUCCESS(f"✓ Successfully parsed {len(lines)} lines"))
            
            # Show validation report
            if validation_report:
                self.stdout.write(self.style.WARNING(f"⚠ Validation issues found:"))
                for issue in validation_report:
                    self.stdout.write(f"  - {issue}")
            else:
                self.stdout.write(self.style.SUCCESS("✓ No validation issues"))
              # Check we have both time and material lines (be flexible about counts)
            if summary['time_lines'] == 0:
                self.stdout.write(self.style.WARNING("⚠ No time lines found"))
            else:
                self.stdout.write(self.style.SUCCESS(f"✓ Found {summary['time_lines']} time lines"))
                
            if summary['material_lines'] == 0:
                self.stdout.write(self.style.WARNING("⚠ No material lines found"))
            else:
                self.stdout.write(self.style.SUCCESS(f"✓ Found {summary['material_lines']} material lines"))
              # Calculate breakdown of costs and revenues
            material_cost = sum(line.total_cost for line in lines if line.kind == 'material')
            time_cost = sum(line.total_cost for line in lines if line.kind == 'time')  # wage cost
            material_revenue = sum(line.total_rev for line in lines if line.kind == 'material')
            time_revenue = sum(line.total_rev for line in lines if line.kind == 'time')
            
            self.stdout.write(f"  Material cost total: ${material_cost:.2f}")
            self.stdout.write(f"  Time cost total: ${time_cost:.2f} (wages)")
            self.stdout.write(f"  Material revenue total: ${material_revenue:.2f}")
            self.stdout.write(f"  Time revenue total: ${time_revenue:.2f}")
            
            # Basic sanity check - should have some reasonable values
            if material_cost > 0 and time_revenue > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Both material costs and time revenue present")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠ Missing material costs or time revenue")
                )
            
            # Validate each line
            issues = []
            for i, line in enumerate(lines):
                if not isinstance(line, DraftLine):
                    issues.append(f"Line {i}: Not a DraftLine object")
                elif not line.desc.strip():
                    issues.append(f"Line {i}: Empty description")
                elif line.quantity <= 0:
                    issues.append(f"Line {i}: Invalid quantity: {line.quantity}")
                elif line.unit_cost < 0:
                    issues.append(f"Line {i}: Negative unit cost: {line.unit_cost}")
            
            if issues:
                self.stdout.write(self.style.ERROR("✗ Issues found:"))
                for issue in issues:
                    self.stdout.write(f"  {issue}")
            else:
                self.stdout.write(self.style.SUCCESS("✓ All lines are valid"))
              # Show summary with detailed breakdown
            self.stdout.write(f"\n📊 Summary:")
            self.stdout.write(f"  Total lines: {summary['total_lines']}")
            self.stdout.write(f"  Time lines: {summary['time_lines']}")
            self.stdout.write(f"  Material lines: {summary['material_lines']}")
            self.stdout.write(f"  Adjust lines: {summary['adjust_lines']}")
            self.stdout.write(f"")
            self.stdout.write(f"  💰 Cost Breakdown:")
            self.stdout.write(f"    Material costs: ${material_cost:.2f}")
            self.stdout.write(f"    Time costs (wages): ${time_cost:.2f}")
            self.stdout.write(f"    Total cost: ${summary['total_cost']:.2f}")
            self.stdout.write(f"")
            self.stdout.write(f"  💸 Revenue Breakdown:")
            self.stdout.write(f"    Material revenue: ${material_revenue:.2f}")
            self.stdout.write(f"    Time revenue: ${time_revenue:.2f}")
            self.stdout.write(f"    Total revenue: ${summary['total_revenue']:.2f}")
            self.stdout.write(f"")
            self.stdout.write(f"  📈 Profit Analysis:")
            material_profit = material_revenue - material_cost
            time_profit = time_revenue - time_cost
            total_profit = summary['total_revenue'] - summary['total_cost']
            
            # Protect against division by zero
            material_markup = (material_profit/material_cost*100) if material_cost > 0 else 0
            time_markup = (time_profit/time_cost*100) if time_cost > 0 else 0
            total_margin = (total_profit/summary['total_cost']*100) if summary['total_cost'] > 0 else 0
            
            self.stdout.write(f"    Material profit: ${material_profit:.2f} ({material_markup:,.1f}% markup)")
            self.stdout.write(f"    Time profit: ${time_profit:.2f} ({time_markup:,.1f}% markup)")
            self.stdout.write(f"    Total profit: ${total_profit:.2f} ({total_margin:,.1f}% margin)")
            
            # Show detailed output if requested
            if options['verbose']:
                self.stdout.write(f"\n📝 Detailed lines:")
                for i, line in enumerate(lines):
                    self.stdout.write(
                        f"  {i+1:3d}. [{line.kind:8s}] {line.desc[:50]:50s} "
                        f"qty={line.quantity:>6} cost=${line.unit_cost:>8} "
                        f"rev=${line.unit_rev:>8} (row {line.source_row})"                    )
              # Final verdict
            has_time_lines = summary['time_lines'] > 0
            has_material_lines = summary['material_lines'] > 0
            has_reasonable_data = material_cost > 0 and time_revenue > 0
            
            if has_time_lines and has_material_lines and not issues and has_reasonable_data:
                self.stdout.write(
                    self.style.SUCCESS(f"\n🎉 Parser test PASSED! All checks successful.")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"\n❌ Parser test FAILED. Please review issues above.")
                )
        
        except Exception as e:
            raise CommandError(f"Error parsing spreadsheet: {e}")
