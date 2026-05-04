#!/usr/bin/env python3
"""
Test script for monitoring and logging functionality.

This script tests the new monitoring and logging services to ensure they work correctly.
"""

import time
import tempfile
import logging
from pathlib import Path

# Setup basic logging
logging.basicConfig(level=logging.INFO)

def test_monitoring_service():
    """Test the monitoring service functionality."""
    print("Testing monitoring service...")
    
    try:
        from batch_processor.services.monitoring import MetricsCollector, ProcessingMetrics
        
        # Create metrics collector
        collector = MetricsCollector(retention_hours=1)
        
        # Test processing metrics
        task_id = "test_task_123"
        collector.start_processing_metrics(
            task_id=task_id,
            session_id="test_session",
            user="test_user",
            file_size_bytes=1024000,
            total_rows=1000,
            algorithm="similarity_top1",
            process_mode="all",
            chunk_size=100
        )
        
        # Simulate progress updates
        collector.update_processing_progress(
            task_id=task_id,
            processed_rows=500,
            successful_rows=480,
            error_count=20,
            confidence_scores=[0.8, 0.9, 0.7, 0.6, 0.85]
        )
        
        # Complete processing
        collector.complete_processing_metrics(
            task_id=task_id,
            success=True
        )
        
        # Get metrics
        metrics = collector.get_processing_metrics(task_id)
        assert metrics is not None, "Processing metrics should be available"
        assert metrics.processed_rows == 500, f"Expected 500 processed rows, got {metrics.processed_rows}"
        
        # Get system metrics
        system_metrics = collector.get_system_metrics()
        assert system_metrics.cpu_percent >= 0, "CPU percentage should be non-negative"
        assert system_metrics.memory_percent >= 0, "Memory percentage should be non-negative"
        
        # Get performance summary
        summary = collector.get_performance_summary(hours=1)
        assert summary['total_tasks'] >= 1, "Should have at least one task in summary"
        
        print("✓ Monitoring service tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Monitoring service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_logging_service():
    """Test the logging service functionality."""
    print("Testing logging service...")
    
    try:
        from batch_processor.services.logging_service import get_structured_logger, LogLevel, LogCategory
        
        # Get structured logger
        logger = get_structured_logger("test_module")
        
        # Test different log types
        logger.log_authentication("test_user", True, "127.0.0.1", "test-agent")
        logger.log_authentication("bad_user", False, "192.168.1.1", "malicious-agent")
        
        logger.log_file_upload(
            user="test_user",
            session_id="test_session",
            filename="test.xlsx",
            file_size=1024,
            success=True
        )
        
        logger.log_processing_start(
            task_id="test_task",
            session_id="test_session",
            user="test_user",
            filename="test.xlsx",
            total_rows=100,
            algorithm="similarity_top1",
            process_mode="all"
        )
        
        logger.log_processing_complete(
            task_id="test_task",
            session_id="test_session",
            user="test_user",
            success=True,
            processed_rows=100,
            error_count=5,
            duration_ms=5000.0,
            output_file="/tmp/output.xlsx"
        )
        
        logger.log_api_request(
            method="POST",
            endpoint="/upload",
            user="test_user",
            status_code=200,
            duration_ms=150.0
        )
        
        logger.log_performance_metric(
            operation="file_processing",
            duration_ms=2500.0,
            memory_mb=128.5,
            cpu_percent=45.2
        )
        
        # Test error logging
        try:
            raise ValueError("Test error for logging")
        except Exception as e:
            logger.log_error(e, {"context": "test_context"}, user="test_user")
        
        # Get error summary
        error_summary = logger.get_error_summary(hours=1)
        assert error_summary['total_errors'] >= 1, "Should have at least one error logged"
        
        # Get performance summary
        perf_summary = logger.get_performance_summary(LogCategory.PROCESSING, hours=1)
        assert perf_summary['total_operations'] >= 1, "Should have processing operations logged"
        
        print("✓ Logging service tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Logging service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_health_endpoints():
    """Test health check functionality."""
    print("Testing health check functionality...")
    
    try:
        from batch_processor.web.health import ServiceHealth
        
        # Create health checker
        health_checker = ServiceHealth()
        
        # Test individual health checks
        redis_health = health_checker.check_redis_health()
        print(f"Redis health: {redis_health['status']}")
        
        disk_health = health_checker.check_disk_health()
        print(f"Disk health: {disk_health['status']}")
        
        memory_health = health_checker.check_memory_health()
        print(f"Memory health: {memory_health['status']}")
        
        cpu_health = health_checker.check_cpu_health()
        print(f"CPU health: {cpu_health['status']}")
        
        # Test overall health
        overall_health = health_checker.get_overall_health()
        assert 'status' in overall_health, "Overall health should have status"
        assert 'checks' in overall_health, "Overall health should have individual checks"
        
        print("✓ Health check tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Health check test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all monitoring and logging tests."""
    print("=" * 60)
    print("Testing Monitoring and Logging Implementation")
    print("=" * 60)
    
    # Set up temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set environment variable for temp directory
        import os
        os.environ['TEMP_DIR'] = temp_dir
        
        # Run tests
        tests = [
            test_monitoring_service,
            test_logging_service,
            test_health_endpoints
        ]
        
        passed = 0
        total = len(tests)
        
        for test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                print(f"✗ Test {test_func.__name__} failed with exception: {e}")
        
        print("=" * 60)
        print(f"Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All monitoring and logging tests passed!")
            return True
        else:
            print("❌ Some tests failed. Check the output above for details.")
            return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)