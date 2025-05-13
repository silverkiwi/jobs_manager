import inspect
import sys
import logging
from django.core.management.base import BaseCommand


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Detects references to the Staff proxy model to determine if it can be safely removed'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about each reference found'
        )
        parser.add_argument(
            '--modules',
            nargs='+',
            default=['workflow', 'accounts'],
            help='Modules to scan for references (default: workflow accounts)'
        )

    def handle(self, *args, **options):
        verbose = options['verbose']
        modules_to_check = options['modules']
        
        self.stdout.write(self.style.WARNING(
            f"Scanning {', '.join(modules_to_check)} for references to workflow.Staff proxy model..."
        ))
        
        try:
            # Import the Staff proxy model
            from workflow.models.staff import Staff as WorkflowStaff
            
            references = []
            
            # Get all loaded modules
            for name, module in list(sys.modules.items()):
                # Skip modules not in our target list
                if not any(name.startswith(module_name) for module_name in modules_to_check):
                    continue
                    
                try:
                    # Inspect module attributes
                    for attr_name, attr_value in inspect.getmembers(module):
                        # Check if attribute references WorkflowStaff
                        if attr_value is WorkflowStaff:
                            references.append((name, attr_name))
                except Exception as e:
                    if verbose:
                        self.stdout.write(self.style.ERROR(
                            f"Error inspecting module {name}: {str(e)}"
                        ))
            
            # Display results
            if references:
                self.stdout.write(self.style.ERROR(
                    f"\nFound {len(references)} references to workflow.Staff:"
                ))
                
                for module_name, attr_name in references:
                    self.stdout.write(self.style.ERROR(
                        f" - {module_name}.{attr_name}"
                    ))
                    
                self.stdout.write(self.style.WARNING(
                    "\nThese references must be updated before removing the proxy model."
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    "\nNo references found! It appears safe to remove the proxy model."
                ))
                
            # Provide next steps guidance
            self.stdout.write("\nRecommended next steps:")
            if references:
                self.stdout.write(
                    "1. Update these references to use 'accounts.models.Staff' directly\n"
                    "2. Run this command again to verify all references are updated\n"
                    "3. Only then remove the proxy model from workflow/models/staff.py"
                )
            else:
                self.stdout.write(
                    "1. Make a backup of your current code\n"
                    "2. Comment out the proxy model in workflow/models/staff.py\n"
                    "3. Run tests to verify everything works\n"
                    "4. Remove the proxy model completely"
                )
                
        except ImportError as e:
            self.stdout.write(self.style.ERROR(
                f"Could not import workflow.models.staff.Staff: {str(e)}"
            ))
            return
        except Exception as e:
            logger.error(f"Unexpected error in detect_proxy_references command: {str(e)}")
            self.stdout.write(self.style.ERROR(
                f"An unexpected error occurred: {str(e)}"
            ))
            return
        