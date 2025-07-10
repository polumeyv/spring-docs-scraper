#!/usr/bin/env python3
"""
Test runner for async scraper tests
"""
import sys
import subprocess
import os

def run_tests():
    """Run all tests with coverage"""
    # Change to backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    print("Running async scraper tests...")
    print("=" * 60)
    
    # Run pytest with coverage
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/',
        '-v',  # Verbose output
        '--cov=src',  # Coverage for src directory
        '--cov-report=term-missing',  # Show missing lines
        '--cov-report=html',  # Generate HTML report
        '-x',  # Stop on first failure
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
        print("\nCoverage report generated in htmlcov/index.html")
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()