#!/usr/bin/env python3
"""
Test script for the license generator and manager
"""

from license_generator import LicenseGenerator
from license_manager import get_license_manager
import sys

def test_license_generation():
    """Test license generation and decoding"""
    print("=== Testing License Generation ===")

    # Create a license generator
    generator = LicenseGenerator()

    # Generate a basic license
    print("\nGenerating Basic license...")
    basic_data = generator.generate_license_data(
        edition="basic",
        expiry_days=365,
        file_limit=50
    )
    basic_key = generator.generate_license_key(basic_data)
    print(f"Basic license key: {basic_key}")

    # Decode the basic license
    print("\nDecoding Basic license...")
    decoded_basic = generator.decode_license_key(basic_key)
    print("Decoded data:")
    for key, value in decoded_basic.items():
        print(f"  {key}: {value}")

    # Generate a professional license with hardware ID
    print("\nGenerating Professional license with hardware ID...")
    # Get the current hardware ID from the license manager
    from license_manager import get_license_manager
    license_manager = get_license_manager()
    hardware_id = license_manager.hardware_id
    print(f"Using current hardware ID: {hardware_id}")

    pro_data = generator.generate_license_data(
        edition="professional",
        hardware_id=hardware_id,
        expiry_days=90,
        file_limit=500
    )
    pro_key = generator.generate_license_key(pro_data)
    print(f"Professional license key: {pro_key}")

    # Decode the professional license
    print("\nDecoding Professional license...")
    decoded_pro = generator.decode_license_key(pro_key)
    print("Decoded data:")
    for key, value in decoded_pro.items():
        print(f"  {key}: {value}")

    # Generate a demo license
    print("\nGenerating Demo license...")
    demo_key = generator.generate_demo_key(days=30, file_limit=10)
    print(f"Demo license key: {demo_key}")

    # Decode the demo license
    print("\nDecoding Demo license...")
    decoded_demo = generator.decode_license_key(demo_key)
    print("Decoded data:")
    for key, value in decoded_demo.items():
        print(f"  {key}: {value}")

    return basic_key, pro_key, demo_key

def test_license_manager(license_key):
    """Test the license manager with a generated key"""
    print("\n=== Testing License Manager ===")

    # Get the license manager
    license_manager = get_license_manager()

    # Activate with the license key
    print(f"\nActivating with license key: {license_key}")
    success, message = license_manager.activate_with_key(license_key)
    print(f"Activation result: {success}")
    print(f"Message: {message}")

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
    for file_count in [5, 50, 500]:
        is_allowed, limit_message = license_manager.check_bulk_limit(file_count)
        print(f"  {file_count} files: {is_allowed} - {limit_message}")

    # Remove the license
    print("\nRemoving license...")
    removed, remove_message = license_manager.remove_license()
    print(f"License removed: {removed}")
    print(f"Message: {remove_message}")

    # Verify after removal
    print("\nVerifying after removal...")
    is_valid, verify_message = license_manager.verify_license()
    print(f"License valid: {is_valid}")
    print(f"Message: {verify_message}")

if __name__ == "__main__":
    # Test license generation
    basic_key, pro_key, demo_key = test_license_generation()

    # Test license manager with one of the keys
    if len(sys.argv) > 1 and sys.argv[1] == "--activate":
        # Use the professional key for testing the manager
        test_license_manager(pro_key)
