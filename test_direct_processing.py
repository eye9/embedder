#!/usr/bin/env python3
"""
Test direct file processing to isolate recursion issue.
"""

import sys
import traceback
import uuid
from pathlib import Path

# Set recursion limit to catch errors earlier
sys.setrecursionlimit(300)

def test_direct_processing():
    """Test process_file_sync directly."""
    print("🔍 Testing direct file processing...")
    
    try:
        from batch_processor.workers.processing_task import process_file_sync
        
        print("✅ Import successful")
        
        # Test parameters
        session_id = str(uuid.uuid4())
        file_path = "GUOO-Manifest--777Bags.xlsx"
        process_mode = "empty_only"
        algorithm = "similarity_top1"
        user = "test_user"
        
        if not Path(file_path).exists():
            print(f"❌ Test file not found: {file_path}")
            return False
        
        print(f"📤 Processing file: {file_path}")
        print(f"Session: {session_id}")
        print(f"Mode: {process_mode}, Algorithm: {algorithm}")
        
        # Call process_file_sync directly
        result = process_file_sync(
            session_id=session_id,
            file_path=file_path,
            process_mode=process_mode,
            algorithm=algorithm,
            user=user
        )
        
        print(f"✅ Processing completed!")
        print(f"Result: {result}")
        
        return True
        
    except RecursionError as e:
        print(f"\n🚨 RECURSION ERROR in direct processing!")
        print(f"Error: {e}")
        print("\n📋 Full traceback:")
        traceback.print_exc()
        
        # Analyze call stack
        print("\n📊 Call stack analysis:")
        tb = traceback.extract_tb(e.__traceback__)
        call_counts = {}
        
        for frame in tb:
            key = f"{Path(frame.filename).name}:{frame.name}:{frame.lineno}"
            call_counts[key] = call_counts.get(key, 0) + 1
        
        print("Most frequent calls:")
        for call, count in sorted(call_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
            if count > 1:
                print(f"  {call}: {count} times")
        
        return False
        
    except Exception as e:
        print(f"❌ Other error: {e}")
        print(f"Error type: {type(e)}")
        traceback.print_exc()
        return False

def test_tnved_integration_direct():
    """Test TNVED integration directly."""
    print("\n🔍 Testing TNVED integration directly...")
    
    try:
        from batch_processor.services.tnved_integration import get_tnved_integration
        
        print("✅ Import successful")
        
        # Try to get integration
        integration = get_tnved_integration()
        print("✅ Integration created")
        
        return True
        
    except RecursionError as e:
        print(f"\n🚨 RECURSION ERROR in TNVED integration!")
        print(f"Error: {e}")
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"❌ Other error: {e}")
        print(f"Error type: {type(e)}")
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("🐛 Direct Processing Debug")
    print("=" * 50)
    
    tests = [
        ("TNVED Integration", test_tnved_integration_direct),
        ("Direct Processing", test_direct_processing)
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
            # Stop on first failure to isolate the issue
            break
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Direct processing works!")
        return 0
    else:
        print("⚠️  Direct processing has recursion issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())