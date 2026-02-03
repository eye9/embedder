"""
Test script to verify admin upload setup is complete.
"""

import yaml
from datetime import datetime

# Test 1: Import all admin models
print("Test 1: Importing admin models...")
try:
    from batch_processor.web.models.admin_models import (
        AdminUploadResponse,
        UploadSummary,
        AdminProgressUpdate,
        AdminValidationResult
    )
    print("✓ All admin models imported successfully")
except Exception as e:
    print(f"✗ Failed to import admin models: {e}")
    exit(1)

# Test 2: Import from package
print("\nTest 2: Importing from models package...")
try:
    from batch_processor.web.models import (
        AdminUploadResponse,
        UploadSummary,
        AdminProgressUpdate,
        AdminValidationResult
    )
    print("✓ Models imported from package successfully")
except Exception as e:
    print(f"✗ Failed to import from package: {e}")
    exit(1)

# Test 3: Import admin router
print("\nTest 3: Importing admin upload router...")
try:
    from batch_processor.web.admin_upload import router
    print(f"✓ Admin router imported successfully (prefix: {router.prefix})")
except Exception as e:
    print(f"✗ Failed to import admin router: {e}")
    exit(1)

# Test 4: Validate AdminUploadResponse model
print("\nTest 4: Validating AdminUploadResponse model...")
try:
    response = AdminUploadResponse(
        upload_id="test-upload-123",
        filename="test_data.xlsx",
        file_size=2048,
        upload_type="tnved",
        source_name="test_source",
        total_records=100,
        message="Upload initiated successfully"
    )
    assert response.upload_type == "tnved"
    assert response.total_records == 100
    print(f"✓ AdminUploadResponse validated: {response.filename}")
except Exception as e:
    print(f"✗ AdminUploadResponse validation failed: {e}")
    exit(1)

# Test 5: Validate UploadSummary model
print("\nTest 5: Validating UploadSummary model...")
try:
    summary = UploadSummary(
        upload_id="test-upload-123",
        upload_type="urls",
        source_name="test_source",
        total_records=100,
        successful_records=95,
        failed_records=5,
        invalid_urls=3,
        invalid_codes=2,
        duplicate_records=5,
        processing_time_seconds=10.5,
        records_per_second=9.52,
        database_total_records=1000,
        errors=["Error 1", "Error 2"],
        warnings=["Warning 1"]
    )
    assert summary.successful_records == 95
    assert summary.failed_records == 5
    print(f"✓ UploadSummary validated: {summary.successful_records}/{summary.total_records} successful")
except Exception as e:
    print(f"✗ UploadSummary validation failed: {e}")
    exit(1)

# Test 6: Validate AdminProgressUpdate model
print("\nTest 6: Validating AdminProgressUpdate model...")
try:
    progress = AdminProgressUpdate(
        upload_id="test-upload-123",
        processed=50,
        total=100,
        progress_pct=50.0,
        records_per_sec=10.0,
        eta_seconds=5.0,
        current_batch=2,
        status="processing"
    )
    assert progress.progress_pct == 50.0
    assert progress.processed <= progress.total
    print(f"✓ AdminProgressUpdate validated: {progress.progress_pct}% complete")
except Exception as e:
    print(f"✗ AdminProgressUpdate validation failed: {e}")
    exit(1)

# Test 7: Validate AdminValidationResult model
print("\nTest 7: Validating AdminValidationResult model...")
try:
    validation = AdminValidationResult(
        is_valid=True,
        upload_type="tnved",
        total_records=100,
        missing_columns=[],
        file_info={"format": "xlsx", "sheets": 1},
        warnings=["Large file detected"]
    )
    assert validation.is_valid == True
    assert validation.upload_type == "tnved"
    print(f"✓ AdminValidationResult validated: valid={validation.is_valid}")
except Exception as e:
    print(f"✗ AdminValidationResult validation failed: {e}")
    exit(1)

# Test 8: Validate invalid upload_type is rejected
print("\nTest 8: Testing upload_type validation...")
try:
    invalid_response = AdminUploadResponse(
        upload_id="test",
        filename="test.xlsx",
        file_size=100,
        upload_type="invalid_type",  # Should fail
        source_name="test",
        total_records=10,
        message="test"
    )
    print("✗ Invalid upload_type was not rejected!")
    exit(1)
except ValueError as e:
    print(f"✓ Invalid upload_type correctly rejected: {e}")
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    exit(1)

# Test 9: Check config.yaml has admin_upload section
print("\nTest 9: Checking config.yaml for admin_upload section...")
try:
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    assert "admin_upload" in config, "admin_upload section not found in config.yaml"
    assert config["admin_upload"]["enabled"] == True
    assert config["admin_upload"]["max_file_size_mb"] == 100
    assert config["admin_upload"]["batch_size"] == 5000
    assert ".xlsx" in config["admin_upload"]["supported_formats"]
    assert ".parquet" in config["admin_upload"]["supported_formats"]
    
    print(f"✓ config.yaml validated:")
    print(f"  - Enabled: {config['admin_upload']['enabled']}")
    print(f"  - Max file size: {config['admin_upload']['max_file_size_mb']}MB")
    print(f"  - Batch size: {config['admin_upload']['batch_size']}")
    print(f"  - Supported formats: {', '.join(config['admin_upload']['supported_formats'])}")
except Exception as e:
    print(f"✗ config.yaml validation failed: {e}")
    exit(1)

# Test 10: Verify router endpoints exist
print("\nTest 10: Checking router endpoints...")
try:
    from batch_processor.web.admin_upload import router
    
    routes = [route.path for route in router.routes]
    expected_routes = [
        "/admin/upload/",
        "/admin/upload/tnved",
        "/admin/upload/urls",
        "/admin/upload/validate",
        "/admin/upload/progress/{upload_id}"
    ]
    
    for expected in expected_routes:
        if expected not in routes:
            print(f"✗ Expected route not found: {expected}")
            exit(1)
    
    print(f"✓ All expected router endpoints found:")
    for route in router.routes:
        print(f"  - {route.path} [{', '.join(route.methods)}]")
except Exception as e:
    print(f"✗ Router endpoint check failed: {e}")
    exit(1)

print("\n" + "="*60)
print("✓ ALL TESTS PASSED!")
print("="*60)
print("\nTask 1 implementation complete:")
print("  ✓ Created batch_processor/web/models/ directory")
print("  ✓ Created batch_processor/web/models/admin_models.py")
print("  ✓ Created batch_processor/web/admin_upload.py router")
print("  ✓ Updated config.yaml with admin_upload settings")
print("  ✓ All models validate correctly")
print("  ✓ All router endpoints defined")
