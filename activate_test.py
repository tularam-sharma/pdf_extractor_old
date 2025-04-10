#!/usr/bin/env python3
"""
Simple script to test license activation
"""

from license_manager import get_license_manager
import sys

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python activate_test.py <license_key>")
        return 1
        
    license_key = sys.argv[1]
    
    # Get the license manager
    license_manager = get_license_manager()
    
    # Print hardware ID
    print(f"Hardware ID: {license_manager.hardware_id}")
    
    # Activate with the license key
    print(f"\nActivating with license key: {license_key}")
    success, message = license_manager.activate_with_key(license_key)
    print(f"Activation result: {success}")
    print(f"Message: {message}")
    
    if success:
        # Verify the license
        print("\nVerifying license...")
        is_valid, verify_message = license_manager.verify_license()
        print(f"License valid: {is_valid}")
        print(f"Message: {verify_message}")
        
        # Get license info
        print("\nGetting license info...")
        license_info = license_manager.get_license_info()
        print("License info:")
        for key, value in license_info.items():
            print(f"  {key}: {value}")
        
        # Check bulk limit
        print("\nChecking bulk limits...")
        for file_count in [5, 50, 500, 1000]:
            is_allowed, limit_message = license_manager.check_bulk_limit(file_count)
            print(f"  {file_count} files: {is_allowed} - {limit_message}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
