#!/usr/bin/env python3
"""
Verification script for CLI functionality

This script verifies that the CLI scripts (load_tnved.py and search_tnved.py)
are properly implemented and can be imported/executed.
"""

import subprocess
import sys


def run_command(cmd, description, expect_success):
    """Run a command and report results"""
    print(f"\n{'='*70}")
    print(f"Testing: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"Expected: {'SUCCESS' if expect_success else 'FAILURE'}")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(f"Exit code: {result.returncode}")
        
        success = (result.returncode == 0) == expect_success
        
        if success:
            print("[PASS] Test passed")
            if result.stdout:
                print("\nOutput (first 500 chars):")
                print(result.stdout[:500])
        else:
            print("[FAIL] Test failed")
            if result.stderr:
                print("\nError output (first 500 chars):")
                print(result.stderr[:500])
            if result.stdout:
                print("\nStdout (first 500 chars):")
                print(result.stdout[:500])
        
        return success
        
    except subprocess.TimeoutExpired:
        print("[FAIL] TIMEOUT")
        return False
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        return False


def main():
    """Main verification function"""
    print("="*70)
    print("CLI Scripts Verification")
    print("="*70)
    
    tests = [
        # Test load_tnved.py help (should succeed)
        (
            ["python", "load_tnved.py", "--help"],
            "load_tnved.py --help",
            True  # expect success
        ),
        
        # Test search_tnved.py help (should succeed)
        (
            ["python", "search_tnved.py", "--help"],
            "search_tnved.py --help",
            True  # expect success
        ),
        
        # Test load_tnved.py dry-run (should succeed)
        (
            ["python", "load_tnved.py", "tnved_full10_new.xlsx", "--dry-run"],
            "load_tnved.py dry-run mode",
            True  # expect success
        ),
        
        # Test load_tnved.py with config (should succeed)
        (
            ["python", "load_tnved.py", "tnved_full10_new.xlsx", "--config", "config.yaml", "--dry-run"],
            "load_tnved.py with config file",
            True  # expect success
        ),
        
        # Test search_tnved.py error handling (should fail with exit code 1)
        (
            ["python", "search_tnved.py"],
            "search_tnved.py error handling",
            False  # expect failure
        ),
    ]
    
    results = []
    for cmd, description, expect_success in tests:
        success = run_command(cmd, description, expect_success)
        results.append((description, success))
    
    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    for description, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status}: {description}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[OK] All CLI scripts are working correctly!")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
