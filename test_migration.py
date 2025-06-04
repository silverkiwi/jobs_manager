#!/usr/bin/env python
"""
Test script to verify the purchase models migration worked correctly.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jobs_manager.settings')
django.setup()

def test_imports():
    """Test that both old and new import paths work."""
    print("🧪 Testing import paths...")
    
    try:
        # Test new purchasing app imports
        from apps.purchasing.models import PurchaseOrder as PurchasingPO
        from apps.purchasing.models import PurchaseOrderLine as PurchasingPOL
        from apps.purchasing.models import PurchaseOrderSupplierQuote as PurchasingPOSQ
        print("✅ Purchasing app imports - SUCCESS")
    except ImportError as e:
        print(f"❌ Purchasing app imports - FAILED: {e}")
        return False
    
    try:
        # Test backward compatibility - workflow imports (proxy models)
        from apps.workflow.models import PurchaseOrder as WorkflowPO
        from apps.workflow.models import PurchaseOrderLine as WorkflowPOL
        from apps.workflow.models import PurchaseOrderSupplierQuote as WorkflowPOSQ
        print("✅ Workflow app imports (proxy) - SUCCESS")
    except ImportError as e:
        print(f"❌ Workflow app imports (proxy) - FAILED: {e}")
        return False
    
    return True

def test_model_equivalency():
    """Test that proxy models point to the same database tables."""
    print("\n🔍 Testing model equivalency...")
    
    from apps.purchasing.models import PurchaseOrder as PurchasingPO
    from apps.workflow.models import PurchaseOrder as WorkflowPO
    
    # Check table names
    purchasing_table = PurchasingPO._meta.db_table
    workflow_table = WorkflowPO._meta.db_table
    
    print(f"Purchasing model table: {purchasing_table}")
    print(f"Workflow proxy table: {workflow_table}")
    
    if purchasing_table == workflow_table:
        print("✅ Table names match - SUCCESS")
        return True
    else:
        print("❌ Table names don't match - FAILED")
        return False

def test_database_operations():
    """Test basic database operations."""
    print("\n💾 Testing database operations...")
    
    from apps.purchasing.models import PurchaseOrder
    from apps.workflow.models import PurchaseOrder as WorkflowPO
    
    try:
        # Count records using both models
        purchasing_count = PurchaseOrder.objects.count()
        workflow_count = WorkflowPO.objects.count()
        
        print(f"Records via purchasing model: {purchasing_count}")
        print(f"Records via workflow proxy: {workflow_count}")
        
        if purchasing_count == workflow_count:
            print("✅ Record counts match - SUCCESS")
            return True
        else:
            print("❌ Record counts don't match - FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Database operations - FAILED: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Purchase Models Migration Tests\n")
    
    all_tests_passed = True
    
    # Run tests
    all_tests_passed &= test_imports()
    all_tests_passed &= test_model_equivalency()
    all_tests_passed &= test_database_operations()
    
    # Summary
    print("\n" + "="*50)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED! Migration successful!")
    else:
        print("❌ SOME TESTS FAILED! Check the output above.")
    print("="*50)
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
