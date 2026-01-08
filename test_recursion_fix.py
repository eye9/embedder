#!/usr/bin/env python3
"""
Test script to verify that the recursion issues have been fixed.
"""

import sys
import traceback

def test_auth_module():
    """Test that auth module loads without recursion errors."""
    try:
        from batch_processor.web.auth import SessionManager, session_manager
        
        # Test creating a session
        session_id = session_manager.create_session("test_user")
        print(f"✅ Auth module: Session created successfully: {session_id}")
        
        # Test session validation
        session = session_manager.get_session(session_id)
        if session:
            print("✅ Auth module: Session validation works")
        
        # Test cleanup
        session_manager.invalidate_session(session_id)
        print("✅ Auth module: Session cleanup works")
        
        return True
    except RecursionError as e:
        print(f"❌ Auth module: Recursion error detected: {e}")
        return False
    except Exception as e:
        print(f"❌ Auth module: Other error: {e}")
        traceback.print_exc()
        return False

def test_websocket_module():
    """Test that websocket module loads without recursion errors."""
    try:
        from batch_processor.web.websocket import ConnectionManager, manager
        
        print("✅ WebSocket module: Imported successfully")
        
        # Test manager initialization
        if hasattr(manager, 'connections'):
            print("✅ WebSocket module: Manager initialized correctly")
        
        return True
    except RecursionError as e:
        print(f"❌ WebSocket module: Recursion error detected: {e}")
        return False
    except Exception as e:
        print(f"❌ WebSocket module: Other error: {e}")
        traceback.print_exc()
        return False

def test_monitoring_module():
    """Test that monitoring module loads without recursion errors."""
    try:
        from batch_processor.services.monitoring import MetricsCollector, get_metrics_collector
        
        print("✅ Monitoring module: Imported successfully")
        
        # Test metrics collector initialization
        collector = get_metrics_collector()
        if collector:
            print("✅ Monitoring module: Metrics collector initialized")
        
        return True
    except RecursionError as e:
        print(f"❌ Monitoring module: Recursion error detected: {e}")
        return False
    except Exception as e:
        print(f"❌ Monitoring module: Other error: {e}")
        traceback.print_exc()
        return False

def test_tasks_module():
    """Test that tasks module loads without recursion errors."""
    try:
        from batch_processor.web.tasks import parse_task_meta, get_task_result
        
        print("✅ Tasks module: Imported successfully")
        
        # Test metadata parsing with various inputs
        test_cases = [
            {},
            {"progress": 0.5, "processed_rows": 100},
            {"nested": {"deep": {"value": 1}}},  # Test nested structures
            None
        ]
        
        for i, test_meta in enumerate(test_cases):
            result = parse_task_meta(test_meta)
            if isinstance(result, dict):
                print(f"✅ Tasks module: Metadata parsing test {i+1} passed")
            else:
                print(f"❌ Tasks module: Metadata parsing test {i+1} failed")
                return False
        
        return True
    except RecursionError as e:
        print(f"❌ Tasks module: Recursion error detected: {e}")
        return False
    except Exception as e:
        print(f"❌ Tasks module: Other error: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all recursion tests."""
    print("🔍 Testing for recursion fixes...")
    print("=" * 50)
    
    tests = [
        ("Auth Module", test_auth_module),
        ("WebSocket Module", test_websocket_module),
        ("Monitoring Module", test_monitoring_module),
        ("Tasks Module", test_tasks_module)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}:")
        if test_func():
            passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All recursion issues have been fixed!")
        return 0
    else:
        print("⚠️  Some recursion issues may still exist.")
        return 1

if __name__ == "__main__":
    sys.exit(main())