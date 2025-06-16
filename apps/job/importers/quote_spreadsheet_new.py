import pandas as pd
from decimal import Decimal
from .draft import DraftLine

def _d(val):
    """Safely coerce values to Decimal with 2 decimal places precision."""
    try:
        # Handle pandas NaN, None, empty strings
        if pd.isna(val) or val is None or val == "":
            return Decimal("0")
        
        # Convert to string and clean common issues
        str_val = str(val).strip()
        if str_val.lower() in ["nan", "none", "", "#n/a"]:
            return Decimal("0")
            
        # Remove any currency symbols or commas
        str_val = str_val.replace("$", "").replace(",", "").replace(" ", "")
        
        return Decimal(str_val).quantize(Decimal("0.01"))
    except (ValueError, TypeError, Exception):
        return Decimal("0")

PRIMARY_SHEET = "Primary Details"

# Column names for different workbook layouts
LABOUR_COL_OLD = "Labour /laser (inhouse)"  # older files
LABOUR_COL_NEW = "assembly"                  # new files
QUANTITY_COL = "quantity"                    # column B
TOTAL_COST_COL = "total cost"               # column N
ITEM_COST_COL = "item cost"                 # column O

# Company defaults (TODO: replace with actual company model lookup)
DEFAULT_WAGE_RATE = Decimal("30.00")        # per hour
DEFAULT_CHARGE_OUT_RATE = Decimal("45.00")  # per hour

# Columns to ignore completely (E→M plus summary columns)
IGNORE_COLS = [
    "E", "F", "G", "H", "I", "J", "K", "L", "M",  # intermediate working columns
    "Labour hours cost", "Cost before MU", "Total cost + MU"  # summary columns
]

def detect_workbook_layout(df):
    """Detect whether this is an old or new workbook layout."""
    columns = df.columns.tolist()
    if LABOUR_COL_OLD in columns:
        return LABOUR_COL_OLD
    elif LABOUR_COL_NEW in columns:
        return LABOUR_COL_NEW
    else:
        raise ValueError(f"Cannot detect workbook layout. Expected either '{LABOUR_COL_OLD}' or '{LABOUR_COL_NEW}' column")

def parse_primary_details(df, minutes_col):
    """
    Parse the Primary Details sheet and extract DraftLines.
    
    Args:
        df: DataFrame containing the Primary Details sheet
        minutes_col: Name of the minutes column (detected from layout)
        
    Returns:
        tuple: (draft_lines, total_minutes, validation_report)
    """
    draft_lines = []
    total_minutes = Decimal("0")
    validation_issues = []
    
    # Only process rows 2-46 (Excel numbering) = DataFrame rows 1-45 (0-indexed)
    for idx in range(1, min(46, len(df) + 1)):  # rows 2-46 in Excel
        if idx >= len(df):
            break
            
        row = df.iloc[idx]
        excel_row = idx + 1  # Convert to Excel row number
        
        # Skip rows without description
        description = str(row.get("Description", "")).strip()
        if not description or description.lower() in ["nan", "none", ""]:
            continue
        
        # Get key values
        quantity = _d(row.get(QUANTITY_COL, 1))
        minutes = _d(row.get(minutes_col, 0))
        total_cost = _d(row.get(TOTAL_COST_COL, 0))
        item_cost = _d(row.get(ITEM_COST_COL, 0))
        
        # Business rule: cannot have both minutes and material cost
        has_minutes = minutes > 0
        has_material = total_cost > 0 or item_cost > 0
        
        if has_minutes and has_material:
            raise ValueError(f"Row {excel_row}: cannot have both labour minutes ({minutes}) and material costs (total: {total_cost}, item: {item_cost})")
        
        # Skip rows with no relevant data
        if not has_minutes and not has_material:
            continue
        
        # Create time entry
        if has_minutes:
            hours = (minutes / Decimal("60")).quantize(Decimal("0.01"))
            total_minutes += minutes
            
            draft_lines.append(DraftLine(
                kind="time",
                desc=f"{description} - Labour",
                quantity=hours,
                unit_cost=DEFAULT_WAGE_RATE,
                unit_rev=DEFAULT_CHARGE_OUT_RATE,
                source_row=excel_row,
                source_sheet=PRIMARY_SHEET
            ))
        
        # Create material entry
        elif has_material:
            draft_lines.append(DraftLine(
                kind="material", 
                desc=f"{description} - Materials",
                quantity=quantity,
                unit_cost=total_cost,
                unit_rev=item_cost,
                source_row=excel_row,
                source_sheet=PRIMARY_SHEET
            ))
    
    return draft_lines, total_minutes, validation_issues

def validate_totals(df, lines, total_minutes, minutes_col):
    """
    Validate our computed totals against spreadsheet summary rows.
    
    Args:
        df: DataFrame containing the sheet
        lines: List of DraftLine objects we created
        total_minutes: Total minutes we computed
        minutes_col: Name of the minutes column
        
    Returns:
        list: Validation issues found
    """
    issues = []
    
    try:
        # Get validation cells (Excel rows 47, 49, 51, 52, 54 = DataFrame rows 46, 48, 50, 51, 53)
        d47 = _d(df.iloc[46].get(minutes_col, 0)) if len(df) > 46 else Decimal("0")  # sum of minutes
        d49 = _d(df.iloc[48].get(minutes_col, 0)) if len(df) > 48 else Decimal("0")  # labour revenue
        d51 = _d(df.iloc[50].get(minutes_col, 0)) if len(df) > 50 else Decimal("0")  # material cost before MU
        d52 = _d(df.iloc[51].get(minutes_col, 0)) if len(df) > 51 else Decimal("0")  # material cost + MU
        d54 = _d(df.iloc[53].get(minutes_col, 0)) if len(df) > 53 else Decimal("0")  # final cost
        
        # Compute our totals
        our_minutes = sum(line.quantity * 60 for line in lines if line.kind == "time")
        our_labour_rev = sum(line.quantity * line.unit_rev for line in lines if line.kind == "time")
        our_material_cost = sum(line.quantity * line.unit_cost for line in lines if line.kind == "material")
        
        # Validate
        if abs(our_minutes - d47) > Decimal("0.1"):
            issues.append(f"Minutes mismatch: computed {our_minutes}, spreadsheet {d47}")
        
        if abs(our_labour_rev - d49) > Decimal("1.00"):
            issues.append(f"Labour revenue mismatch: computed ${our_labour_rev}, spreadsheet ${d49}")
        
        if abs(our_material_cost - d51) > Decimal("1.00"):
            issues.append(f"Material cost mismatch: computed ${our_material_cost}, spreadsheet ${d51}")
            
        # Note: We're not validating D52/D54 here as markup calculation would require company settings
        
    except (IndexError, KeyError) as e:
        issues.append(f"Could not read validation cells: {e}")
    
    return issues

def parse_xlsx(path: str) -> list[DraftLine]:
    """
    Parse the Quoting Spreadsheet and convert Primary Details sheet
    into a list of DraftLine objects.
    
    Args:
        path: Path to the Excel file
        
    Returns:
        List of DraftLine objects representing the spreadsheet data
    """
    try:
        # Read the Primary Details sheet
        df = pd.read_excel(path, sheet_name=PRIMARY_SHEET)
        
        # Detect workbook layout
        minutes_col = detect_workbook_layout(df)
        
        # Parse the sheet
        draft_lines, total_minutes, validation_issues = parse_primary_details(df, minutes_col)
        
        # Validate totals (for debugging/logging purposes)
        validation_issues.extend(validate_totals(df, draft_lines, total_minutes, minutes_col))
        
        # Log validation issues if any (in production, you might want to use proper logging)
        if validation_issues:
            print(f"Validation issues found: {validation_issues}")
        
        return draft_lines
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Excel file not found: {path}")
    except Exception as e:
        raise Exception(f"Error parsing Excel file: {str(e)}")

def parse_xlsx_with_summary(path: str) -> dict:
    """
    Parse the Excel file and return both draft lines and summary statistics.
    
    Args:
        path: Path to the Excel file
        
    Returns:
        Dictionary containing 'draft_lines' and 'summary'
    """
    draft_lines = parse_xlsx(path)
    
    summary = {
        'total_lines': len(draft_lines),
        'time_lines': len([line for line in draft_lines if line.kind == 'time']),
        'material_lines': len([line for line in draft_lines if line.kind == 'material']),
        'adjust_lines': len([line for line in draft_lines if line.kind == 'adjust']),
        'total_cost': sum(line.total_cost for line in draft_lines),
        'total_revenue': sum(line.total_rev for line in draft_lines),
    }
    
    return {
        'draft_lines': draft_lines,
        'summary': summary
    }
