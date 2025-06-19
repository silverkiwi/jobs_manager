#!/usr/bin/env python
"""
Test script to verify quote parsing functionality
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jobs_manager.settings.development')
django.setup()

from apps.job.importers.quote_spreadsheet import parse_xlsx
import pandas as pd

def test_quote_parsing():
    print("=== Testing Quote Parsing with Google Sheets Data ===")
    
    # Create test data that simulates Google Sheets with empty item numbers
    test_data = pd.DataFrame({
        'item': ['', '', '1.0', ''],  # Mixed empty and valid item numbers
        'quantity': [5, 3, 2, 1],    # Valid quantities (sorted desc for testing)
        'description': ['Item A', 'Item B', 'Item C', 'Item D'],
        'labour_minutes': [120, 60, 90, 30],
        'material_cost': [100, 50, 75, 25]
    })

    print("Input DataFrame:")
    print(test_data)
    print()

    try:
        result = parse_xlsx(test_data)
        print("✅ Parse successful!")
        
        if 'draft_lines' in result:
            print(f"📋 Number of draft lines created: {len(result['draft_lines'])}")
            for i, line in enumerate(result['draft_lines']):
                print(f"  Line {i+1}: item={line.get('item', 'N/A')}, qty={line.get('quantity', 'N/A')}, desc={line.get('desc', 'N/A')}")
        else:
            print("❌ No draft_lines in result")
            
        if 'validation_report' in result:
            validation = result['validation_report']
            print(f"📊 Validation report: {validation.get('total_issues', 0)} issues")
            if validation.get('issues'):
                for issue in validation['issues']:
                    print(f"  - {issue}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_quote_parsing()
    sys.exit(0 if success else 1)
