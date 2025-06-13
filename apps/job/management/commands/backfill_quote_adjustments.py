from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from apps.job.models import Job, AdjustmentEntry
from apps.job.enums import JobPricingMethodology


class Command(BaseCommand):
    help = 'Backfill quote adjustments for completed/archived fixed-price jobs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Find completed or archived fixed-price jobs
        target_jobs = Job.objects.filter(
            status__in=['completed', 'archived'],
            pricing_methodology=JobPricingMethodology.FIXED_PRICE
        ).select_related('latest_quote_pricing', 'latest_reality_pricing')
        
        self.stdout.write(f'Found {target_jobs.count()} completed/archived fixed-price jobs')
        
        created_count = 0
        skipped_count = 0
        
        for job in target_jobs:
            try:
                # Check if quote adjustment already exists
                existing_adjustment = AdjustmentEntry.objects.filter(
                    job_pricing=job.latest_reality_pricing,
                    is_quote_adjustment=True
                ).exists()
                
                if existing_adjustment:
                    self.stdout.write(f'Job {job.job_number}: Quote adjustment already exists - skipping')
                    skipped_count += 1
                    continue
                
                # Get quote and reality revenues
                quote_revenue = Decimal(str(job.latest_quote_pricing.total_revenue))
                reality_revenue = Decimal(str(job.latest_reality_pricing.total_revenue))
                
                # Calculate adjustment needed
                adjustment_amount = quote_revenue - reality_revenue
                
                # Only create if there's a difference
                if abs(adjustment_amount) < Decimal('0.01'):
                    self.stdout.write(f'Job {job.job_number}: No adjustment needed (quote={quote_revenue}, reality={reality_revenue})')
                    skipped_count += 1
                    continue
                
                if dry_run:
                    self.stdout.write(
                        f'Job {job.job_number}: Would create adjustment of ${adjustment_amount} '
                        f'(quote: ${quote_revenue}, reality: ${reality_revenue})'
                    )
                    created_count += 1
                else:
                    # Create the adjustment entry
                    with transaction.atomic():
                        AdjustmentEntry.objects.create(
                            job_pricing=job.latest_reality_pricing,
                            description="Adjusted to match quote",
                            price_adjustment=adjustment_amount,
                            cost_adjustment=Decimal('0.00'),
                            accounting_date=timezone.now().date(),
                            comments=f"Backfilled adjustment. Quote: ${quote_revenue}, Reality: ${reality_revenue}",
                            is_quote_adjustment=True
                        )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Job {job.job_number}: Created adjustment of ${adjustment_amount}'
                        )
                    )
                    created_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Job {job.job_number}: Error - {str(e)}')
                )
        
        # Summary
        action = "Would create" if dry_run else "Created"
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: {action} {created_count} quote adjustments, skipped {skipped_count} jobs'
            )
        )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Run without --dry-run to actually create the adjustments'))