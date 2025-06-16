"""
Quote Import Service

Service layer for importing quotes from spreadsheets into the CostSet system.
Follows clean code principles:
- Single Responsibility Principle
- Early return and guard clauses
- Delegation pattern
- Transaction management
"""

import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal
from django.db import transaction, models
from django.core.exceptions import ValidationError

from apps.job.models import Job, CostSet, CostLine
from apps.job.importers.draft import DraftLine
from apps.job.importers.quote_spreadsheet import (
    parse_xlsx_with_validation, 
    parse_xlsx,
    ValidationReport
)
from apps.job.diff import diff_costset, apply_diff, DiffResult

logger = logging.getLogger(__name__)


class QuoteImportError(Exception):
    """Custom exception for quote import errors"""
    pass


class QuoteImportResult:
    """Result object for quote import operations"""
    
    def __init__(self, success: bool, cost_set: Optional[CostSet] = None, 
                 diff_result: Optional[DiffResult] = None, 
                 validation_report: Optional[ValidationReport] = None,
                 error_message: Optional[str] = None):
        self.success = success
        self.cost_set = cost_set
        self.diff_result = diff_result
        self.validation_report = validation_report
        self.error_message = error_message


def import_quote_from_file(job: Job, file_path: str, 
                          skip_validation: bool = False) -> QuoteImportResult:
    """
    Import a quote from an Excel spreadsheet file.
    
    Args:
        job: Job instance to import the quote for
        file_path: Path to the Excel spreadsheet
        skip_validation: Whether to skip pre-import validation
        
    Returns:
        QuoteImportResult with operation details
        
    Raises:
        QuoteImportError: If import fails due to validation or processing errors
    """
    # Early return: validate inputs
    if not job:
        raise QuoteImportError("Job instance is required")
    if not file_path:
        raise QuoteImportError("File path is required")
    
    logger.info(f"Starting quote import for job {job.id} from {file_path}")
    
    try:
        # Step 1: Parse and validate the spreadsheet
        if skip_validation:
            # Use simple parser without validation
            draft_lines, validation_issues = parse_xlsx(file_path, skip_validation=True)
            validation_report = None
        else:
            # Use full validation
            result = parse_xlsx_with_validation(file_path)
            
            # Early return: check if validation failed
            if not result['success'] or not result['can_proceed']:
                return QuoteImportResult(
                    success=False,
                    validation_report=result['validation_report'],
                    error_message="Spreadsheet validation failed - see validation report"
                )
            
            draft_lines = result['draft_lines']
            validation_report = result['validation_report']
        
        # Early return: check if we have any lines to import
        if not draft_lines:
            return QuoteImportResult(
                success=False,
                error_message="No valid lines found in spreadsheet"
            )
        
        # Step 2: Import the quote using the draft lines
        import_result = import_quote_from_drafts(job, draft_lines)
        
        # Combine validation report with import result
        import_result.validation_report = validation_report
        
        logger.info(f"Quote import completed for job {job.id}: success={import_result.success}")
        return import_result
        
    except Exception as e:
        logger.error(f"Unexpected error during quote import for job {job.id}: {str(e)}")
        raise QuoteImportError(f"Import failed: {str(e)}") from e


def import_quote_from_drafts(job: Job, draft_lines: List[DraftLine]) -> QuoteImportResult:
    """
    Import a quote from a list of DraftLine objects.
    
    This is the core business logic for quote importing:
    1. Get existing quote CostSet (if any)
    2. Calculate diff between old and new
    3. Create new CostSet with incremented revision
    4. Apply diff and update job pointers
    
    Args:
        job: Job instance to import the quote for
        draft_lines: List of DraftLine objects from spreadsheet parsing
        
    Returns:
        QuoteImportResult with operation details
    """
    # Early return: validate inputs
    if not job:
        raise QuoteImportError("Job instance is required")
    if not draft_lines:
        return QuoteImportResult(
            success=False,
            error_message="No draft lines provided"        )
    
    logger.info(f"Importing quote from {len(draft_lines)} draft lines for job {job.id}")
    
    try:
        with transaction.atomic():
            # Step 1: Hybrid approach to get the actual latest revision
            # Query the database directly for the actual maximum revision
            db_latest_rev = job.cost_sets.filter(kind='quote').aggregate(
                max_rev=models.Max('rev')
            )['max_rev']
            
            # Get the revision from the job pointer (may be stale)
            pointer_cost_set = job.get_latest('quote')
            pointer_rev = pointer_cost_set.rev if pointer_cost_set else None
            
            # Determine the most reliable latest revision
            actual_latest_rev = None
            old_cost_set = None
            
            if db_latest_rev is not None and pointer_rev is not None:
                # Both exist - compare and log discrepancy if found
                if db_latest_rev != pointer_rev:
                    logger.warning(
                        f"Job {job.id}: Revision discrepancy detected! "
                        f"Database max revision: {db_latest_rev}, "
                        f"Pointer revision: {pointer_rev}. Using database value."
                    )
                # Always trust the database value
                actual_latest_rev = db_latest_rev
                old_cost_set = job.cost_sets.filter(kind='quote', rev=actual_latest_rev).first()
                
            elif db_latest_rev is not None:
                # Only database has data - pointer is missing or outdated
                logger.warning(
                    f"Job {job.id}: Database has quote rev {db_latest_rev} but pointer is None. "
                    f"Pointer may be stale."
                )
                actual_latest_rev = db_latest_rev
                old_cost_set = job.cost_sets.filter(kind='quote', rev=actual_latest_rev).first()
                
            elif pointer_rev is not None:
                # Only pointer has data - verify it exists in database
                if job.cost_sets.filter(kind='quote', rev=pointer_rev).exists():
                    actual_latest_rev = pointer_rev
                    old_cost_set = pointer_cost_set
                    logger.info(f"Job {job.id}: Using pointer revision {pointer_rev}")
                else:
                    logger.error(
                        f"Job {job.id}: Pointer references non-existent revision {pointer_rev}. "
                        f"Treating as no existing quote."
                    )
                    actual_latest_rev = None
                    old_cost_set = None
            else:
                # No existing quotes
                actual_latest_rev = None
                old_cost_set = None
            
            # Calculate next revision
            if actual_latest_rev is not None:
                next_rev = actual_latest_rev + 1
                logger.info(f"Job {job.id}: Creating new quote rev {next_rev} "
                           f"(previous rev was {actual_latest_rev})")
            else:
                next_rev = 1
                logger.info(f"Job {job.id}: Creating first quote rev 1")
            
            # Step 3: Calculate diff if there's an existing cost set
            if old_cost_set:
                diff_result = diff_costset(old_cost_set, draft_lines)
                logger.info(f"Diff calculated: {len(diff_result.to_add)} additions, "
                           f"{len(diff_result.to_update)} updates, "
                           f"{len(diff_result.to_delete)} deletions")
            else:
                # All lines are new
                diff_result = DiffResult(
                    to_add=draft_lines,
                    to_update=[],
                    to_delete=[]
                )
                logger.info(f"No existing quote - all {len(draft_lines)} lines will be added")
            
            # Step 4: Create new CostSet
            new_cost_set = CostSet.objects.create(
                job=job,
                kind='quote',
                rev=next_rev,
                summary={'cost': 0, 'rev': 0, 'hours': 0}  # Will be updated by apply_diff
            )
            logger.info(f"Created new quote CostSet rev {next_rev} (ID: {new_cost_set.id})")
            
            # Step 5: Apply diff to create cost lines
            apply_diff(new_cost_set, diff_result)
              # Step 6: Update job's latest_quote pointer to maintain consistency
            # This ensures the pointer stays in sync with the database
            job.set_latest('quote', new_cost_set)
            
            logger.info(f"Successfully imported quote for job {job.id} - "
                       f"CostSet ID: {new_cost_set.id}, Rev: {new_cost_set.rev}. "
                       f"Job pointer updated to maintain consistency.")
            
            return QuoteImportResult(
                success=True,
                cost_set=new_cost_set,
                diff_result=diff_result
            )
            
    except Exception as e:
        logger.error(f"Error importing quote for job {job.id}: {str(e)}")
        raise QuoteImportError(f"Failed to import quote: {str(e)}") from e


def preview_quote_import(job: Job, file_path: str) -> Dict[str, Any]:
    """
    Preview what changes would be made by importing a quote without actually importing it.
    
    Args:
        job: Job instance
        file_path: Path to Excel spreadsheet
        
    Returns:
        Dictionary with preview information including:
        - validation_report: Validation issues found
        - draft_lines: Parsed draft lines  
        - diff_preview: What changes would be made
        - can_proceed: Whether import can proceed
    """
    logger.info(f"Previewing quote import for job {job.id} from {file_path}")
    
    try:
        # Parse with validation
        result = parse_xlsx_with_validation(file_path)
        
        preview_data = {
            'validation_report': result['validation_report'],
            'can_proceed': result['can_proceed'],
            'draft_lines': result['draft_lines'],
            'diff_preview': None
        }
          # If parsing succeeded, calculate diff preview using hybrid approach
        if result['success'] and result['draft_lines']:
            # Use same hybrid logic as import function for consistency
            db_latest_rev = job.cost_sets.filter(kind='quote').aggregate(
                max_rev=models.Max('rev')
            )['max_rev']
            
            pointer_cost_set = job.get_latest('quote')
            pointer_rev = pointer_cost_set.rev if pointer_cost_set else None
            
            # Determine the most reliable latest revision and cost set
            actual_latest_rev = None
            old_cost_set = None
            
            if db_latest_rev is not None and pointer_rev is not None:
                if db_latest_rev != pointer_rev:
                    logger.warning(
                        f"Job {job.id} preview: Revision discrepancy detected! "
                        f"Database: {db_latest_rev}, Pointer: {pointer_rev}"
                    )
                actual_latest_rev = db_latest_rev
                old_cost_set = job.cost_sets.filter(kind='quote', rev=actual_latest_rev).first()
            elif db_latest_rev is not None:
                actual_latest_rev = db_latest_rev
                old_cost_set = job.cost_sets.filter(kind='quote', rev=actual_latest_rev).first()
            elif pointer_rev is not None:
                if job.cost_sets.filter(kind='quote', rev=pointer_rev).exists():
                    actual_latest_rev = pointer_rev
                    old_cost_set = pointer_cost_set
                else:
                    actual_latest_rev = None
                    old_cost_set = None
            
            if old_cost_set:
                diff_result = diff_costset(old_cost_set, result['draft_lines'])
                next_revision = actual_latest_rev + 1
                preview_data['diff_preview'] = {
                    'additions_count': len(diff_result.to_add),
                    'updates_count': len(diff_result.to_update),
                    'deletions_count': len(diff_result.to_delete),
                    'total_changes': (len(diff_result.to_add) + 
                                    len(diff_result.to_update) + 
                                    len(diff_result.to_delete)),
                    'next_revision': next_revision,
                    'current_revision': actual_latest_rev
                }
            else:
                preview_data['diff_preview'] = {
                    'additions_count': len(result['draft_lines']),
                    'updates_count': 0,
                    'deletions_count': 0,
                    'total_changes': len(result['draft_lines']),
                    'next_revision': 1,
                    'current_revision': None
                }
        
        return preview_data
        
    except Exception as e:
        logger.error(f"Error previewing quote import for job {job.id}: {str(e)}")
        return {
            'validation_report': None,
            'can_proceed': False,
            'draft_lines': [],
            'diff_preview': None,
            'error': str(e)
        }
