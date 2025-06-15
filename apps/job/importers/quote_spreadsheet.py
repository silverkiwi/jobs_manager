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

# Support both workbook layouts
LABOUR_COLS = ["Labour /laser (inhouse)", "assembly"]  # older and newer files
MATERIAL_TOTAL_COL = "total cost"   # column N (but may have trailing space)
MATERIAL_ITEM_COL = "item cost"     # column O
QUANTITY_COL = "quantity"           # column B

# Default values if CompanyDefaults not available
DEFAULT_WAGE_RATE = Decimal("32.00")
DEFAULT_CHARGE_OUT_RATE = Decimal("110.00")
DEFAULT_MATERIALS_MARKUP = Decimal("0.20")  # 20%

# Columns to ignore for DraftLine creation
IGNORE_COLS = ["total cost", "item cost", "Labour hours cost", "Cost before MU", "Total cost + MU"]

def detect_labour_column(df):
    """Detect which labour column is present in this workbook."""
    for col in LABOUR_COLS:
        if col in df.columns:
            return col
    # If no labour column found, we'll just process materials
    return None

def detect_material_columns(df):
    """Detect material cost columns, handling trailing spaces."""
    total_col = None
    item_col = None
    
    # Look for total cost column (may have trailing space)
    for col in df.columns:
        if col.strip().lower() == "total cost":
            total_col = col
            break
    
    # Look for item cost column
    for col in df.columns:
        if col.strip().lower() == "item cost":
            item_col = col
            break
    
    return total_col, item_col

def parse_xlsx(path: str, company=None) -> tuple[list[DraftLine], list[str]]:
    """
    Parse the Quoting Spreadsheet and convert Primary Details sheet
    into a list of DraftLine objects with validation.
    
    Args:
        path: Path to the Excel file
        company: Company object with wage_rate and charge_out_rate (optional)
        
    Returns:
        tuple: (draft_lines, validation_report)
    """
    try:
        # Read the Primary Details sheet
        df = pd.read_excel(path, sheet_name=PRIMARY_SHEET)
        
        # Read pricing details for validation
        pricing_df = None
        try:
            pricing_df = pd.read_excel(path, sheet_name="pricing details - inhouse")
        except Exception:
            pass  # Optional sheet for validation
        
        # Detect columns
        labour_col = detect_labour_column(df)
        material_total_col, material_item_col = detect_material_columns(df)# Get company rates from CompanyDefaults if available
        if company:
            wage_rate = getattr(company, 'wage_rate', DEFAULT_WAGE_RATE)
            charge_out_rate = getattr(company, 'charge_out_rate', DEFAULT_CHARGE_OUT_RATE)
            materials_markup = getattr(company, 'materials_markup', DEFAULT_MATERIALS_MARKUP)
        else:
            # Try to get from CompanyDefaults model
            try:
                from apps.workflow.models import CompanyDefaults
                defaults = CompanyDefaults.objects.first()
                if defaults:
                    wage_rate = defaults.wage_rate
                    charge_out_rate = defaults.charge_out_rate
                    materials_markup = defaults.materials_markup
                else:
                    wage_rate = DEFAULT_WAGE_RATE
                    charge_out_rate = DEFAULT_CHARGE_OUT_RATE
                    materials_markup = DEFAULT_MATERIALS_MARKUP
            except (ImportError, Exception):
                wage_rate = DEFAULT_WAGE_RATE
                charge_out_rate = DEFAULT_CHARGE_OUT_RATE
                materials_markup = DEFAULT_MATERIALS_MARKUP
        
        draft_lines = []
        total_minutes = Decimal("0")          # Process rows - only those with valid item numbers in column A
        for idx in range(0, min(45, len(df))):
            row = df.iloc[idx]
            excel_row = idx + 1  # Convert to Excel row number            # Skip rows without description
            description = str(row.get("Description", "")).strip()
            if not description or description.lower() in ["nan", "none", ""]:
                description = f"Item {row.get('item', '')}"  # Use item number as description if blank
              # Validate item: must have ALL three - item number, quantity, and description
            # Check 1: Item number (must be valid number)
            item_number = str(row.get("item", "")).strip()
            if not item_number or item_number.lower() in ["nan", "none", ""]:
                continue
            
            try:
                float(item_number)  # Accept floats like 1.0, 2.0
            except (ValueError, TypeError):
                continue  # Skip non-numeric item numbers
            
            # Check 2: Quantity (must have value and not be zero)
            quantity = _d(row.get(QUANTITY_COL, 1))
            if quantity <= 0:
                continue
                
            # Check 3: Description (must not be empty, nan, or none)
            description = str(row.get("Description", "")).strip()
            if not description or description.lower() in ["nan", "none", ""]:
                continue
              # Get values from key columns only (A, B, C, D, N, O)
            minutes = _d(row.get(labour_col, 0)) if labour_col else Decimal("0")
            material_total_cost = _d(row.get(material_total_col, 0)) if material_total_col else Decimal("0")
            material_item_cost = _d(row.get(material_item_col, 0)) if material_item_col else Decimal("0")# Business logic: 1 DraftLine per item
            # IF labour exists → kind='time'
            # ELSE IF item cost exists → kind='material'
            # VALIDATION: Cannot have both labour AND material
            has_labour = minutes > 0
            has_material = material_total_cost > 0 or material_item_cost > 0
            
            # Validation check: item cannot have both labour and material
            if has_labour and has_material:
                print(f"⚠️  WARNING: Row {excel_row} has both labour ({minutes} min) and material costs (${material_total_cost}/${material_item_cost}). Using labour only.")
            
            if has_labour:
                # Create time entry (labour minutes → hours)
                hours = (minutes / Decimal("60")).quantize(Decimal("0.01"))
                total_minutes += minutes
                
                draft_lines.append(DraftLine(
                    kind="time",
                    desc=f"{description} - Labour",
                    quantity=hours,
                    unit_cost=wage_rate,
                    unit_rev=charge_out_rate,
                    source_row=excel_row,
                    source_sheet=PRIMARY_SHEET
                ))
                
            elif has_material:
                # Create material entry
                # unit_cost comes from column O ("item cost")
                # unit_rev = unit_cost * (1 + materials_markup)
                unit_cost = material_item_cost
                unit_rev = unit_cost * (1 + materials_markup)
                
                draft_lines.append(DraftLine(
                    kind="material",
                    desc=f"{description} - Materials",
                    quantity=quantity,
                    unit_cost=unit_cost,
                    unit_rev=unit_rev,
                    source_row=excel_row,
                    source_sheet=PRIMARY_SHEET
                ))
            
            # If neither labour nor material, skip this item        # Validation - collect totals from summary rows
        validation_report = validate_totals(df, draft_lines, total_minutes, labour_col, materials_markup, pricing_df)
        
        return draft_lines, validation_report
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Excel file not found: {path}")
    except Exception as e:
        raise Exception(f"Error parsing Excel file: {str(e)}")

def find_validation_cells(df, labour_col):
    """
    Find validation cells dynamically based on content, not fixed positions.
    
    Returns:
        dict: Contains validation values found in the spreadsheet
    """
    validation_data = {
        'total_minutes': Decimal("0"),
        'labour_revenue': Decimal("0"),
        'material_cost_before_mu': Decimal("0"),
        'material_cost_with_mu': Decimal("0"),
        'final_cost': Decimal("0")
    }
    
    try:
        # Search through the dataframe for specific text patterns
        for idx in range(len(df)):
            row = df.iloc[idx]
            
            # Check Description column for key markers
            description = str(row.get("Description", "")).strip().lower()
            
            if "labour hours cost" in description:
                # Labour revenue is to the right (in labour column)
                validation_data['labour_revenue'] = _d(row.get(labour_col, 0))
                
            elif "cost before mu" in description:
                # Material cost before markup is to the right (in labour column)
                validation_data['material_cost_before_mu'] = _d(row.get(labour_col, 0))
                
            elif "total cost + mu" in description or ("total cost" in description and "mu" in description):
                # Material cost with markup is to the right (in labour column)
                validation_data['material_cost_with_mu'] = _d(row.get(labour_col, 0))
                
            elif "final cost" in description:
                # Final cost is to the right (in labour column)
                validation_data['final_cost'] = _d(row.get(labour_col, 0))
          # Find total minutes: last non-zero value in labour column before "Labour hours cost" line
        if labour_col:
            labour_hours_cost_idx = None
            
            # First, find the "Labour hours cost" line
            for idx in range(len(df)):
                row = df.iloc[idx]
                description = str(row.get("Description", "")).strip().lower()
                if "labour hours cost" in description:
                    labour_hours_cost_idx = idx
                    break
            
            # Then search backwards from that line to find the last minutes value
            if labour_hours_cost_idx is not None:
                for idx in range(labour_hours_cost_idx - 1, -1, -1):
                    row = df.iloc[idx]
                    minutes_val = _d(row.get(labour_col, 0))
                    if minutes_val > 0:
                        validation_data['total_minutes'] = minutes_val
                        break
    
    except Exception as e:
        print(f"Warning: Could not find all validation cells: {e}")
    
    return validation_data

def validate_totals(df, lines, total_minutes, labour_col, materials_markup=DEFAULT_MATERIALS_MARKUP, pricing_df=None):
    """
    Validate our computed totals against spreadsheet summary rows using dynamic content-based search.
    
    Returns:
        list[str]: Validation issues found
    """
    issues = []
    
    try:
        # Validate pricing details if available
        if pricing_df is not None and len(pricing_df) > 1:
            # Get labour cost and margin from pricing details (row 1)
            spreadsheet_labour_cost = _d(pricing_df.iloc[1].get('labour cost', 0))
            spreadsheet_margin = _d(pricing_df.iloc[1].get('margin', 1.2))
            
            # Get our company defaults for comparison
            from apps.workflow.models import CompanyDefaults
            try:
                defaults = CompanyDefaults.objects.first()
                if defaults:
                    our_charge_out_rate = defaults.charge_out_rate
                    our_materials_markup = defaults.materials_markup
                    
                    # Validate labour cost (should match charge_out_rate)
                    if abs(spreadsheet_labour_cost - our_charge_out_rate) > Decimal("0.01"):
                        issues.append(f"Labour cost mismatch: spreadsheet ${spreadsheet_labour_cost}, system ${our_charge_out_rate}")
                    
                    # Validate margin (1.2 = 20% markup)
                    spreadsheet_markup = spreadsheet_margin - 1 if spreadsheet_margin > 1 else Decimal("0")
                    if abs(spreadsheet_markup - our_materials_markup) > Decimal("0.01"):
                        issues.append(f"Material markup mismatch: spreadsheet {spreadsheet_markup:.1%}, system {our_materials_markup:.1%}")
            except Exception:
                pass  # Skip validation if can't access CompanyDefaults

        # Find validation cells dynamically based on content
        validation_data = find_validation_cells(df, labour_col)
          # Compute our totals
        our_minutes = sum(line.quantity * 60 for line in lines if line.kind == "time")
        our_labour_rev = sum(line.quantity * line.unit_rev for line in lines if line.kind == "time")
        our_material_cost = sum(line.quantity * line.unit_cost for line in lines if line.kind == "material")
        our_material_cost_mu = our_material_cost * (1 + materials_markup)
        our_final_cost = our_labour_rev + our_material_cost_mu
          # Check for mismatches using dynamic validation data
        if abs(our_minutes - validation_data['total_minutes']) > Decimal("0.1"):
            issues.append(f"Minutes mismatch: computed {our_minutes}, spreadsheet {validation_data['total_minutes']}")
        
        if abs(our_labour_rev - validation_data['labour_revenue']) > Decimal("1.00"):
            issues.append(f"Labour revenue mismatch: computed ${our_labour_rev}, spreadsheet ${validation_data['labour_revenue']}")
        
        if abs(our_material_cost - validation_data['material_cost_before_mu']) > Decimal("1.00"):
            issues.append(f"Material cost mismatch: computed ${our_material_cost}, spreadsheet ${validation_data['material_cost_before_mu']}")
        
        if abs(our_material_cost_mu - validation_data['material_cost_with_mu']) > Decimal("1.00"):
            # Check if markup percentage is different
            if validation_data['material_cost_before_mu'] > 0:  # avoid division by zero
                spreadsheet_markup = ((validation_data['material_cost_with_mu'] - validation_data['material_cost_before_mu']) / validation_data['material_cost_before_mu'])
                markup_diff = abs(spreadsheet_markup - materials_markup)
                if markup_diff > Decimal("0.01"):  # 1% tolerance
                    issues.append(f"Spreadsheet uses {spreadsheet_markup:.1%} markup, system uses {materials_markup:.1%}. Adjust markup or accept?")
                else:
                    issues.append(f"Material + MU mismatch: computed ${our_material_cost_mu}, spreadsheet ${validation_data['material_cost_with_mu']}")
        
        if abs(our_final_cost - validation_data['final_cost']) > Decimal("1.00"):
            issues.append(f"Final cost mismatch: computed ${our_final_cost}, spreadsheet ${validation_data['final_cost']}")
            
    except (IndexError, KeyError) as e:
        issues.append(f"Could not read validation cells: {e}")
    
    return issues
    
    return issues

# Backward compatibility wrapper
def parse_xlsx_old(path: str) -> list[DraftLine]:
    """Backward compatibility wrapper - returns only draft_lines."""
    draft_lines, _ = parse_xlsx(path)
    return draft_lines

def parse_xlsx_with_summary(path: str) -> dict:
    """
    Parse the Excel file and return both draft lines and summary statistics.
    
    Args:
        path: Path to the Excel file
        
    Returns:
        Dictionary containing 'draft_lines', 'summary', and 'validation_report'
    """
    draft_lines, validation_report = parse_xlsx(path)
    
    summary = {
        'total_lines': len(draft_lines),
        'time_lines': len([line for line in draft_lines if line.kind == 'time']),
        'material_lines': len([line for line in draft_lines if line.kind == 'material']),
        'adjust_lines': len([line for line in draft_lines if line.kind == 'adjust']),        'total_cost': sum(line.total_cost for line in draft_lines),
        'total_revenue': sum(line.total_rev for line in draft_lines),
    }
    
    return {
        'draft_lines': draft_lines,
        'summary': summary,
        'validation_report': validation_report
    }