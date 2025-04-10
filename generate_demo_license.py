#!/usr/bin/env python3
"""
Generate and activate a demo license for PDF Harvest
"""

import sys
import datetime
import hashlib
import argparse
from license_manager import get_license_manager

def generate_demo_key(days=30, file_limit=10):
    """Generate a simple demo license key"""
    expiry_date = datetime.datetime.now() + datetime.timedelta(days=days)
    date_str = expiry_date.strftime("%Y%m%d")
    key = f"DEMO{date_str}{file_limit:04d}"
    # Pad the key to ensure it's long enough
    key = key.ljust(24, '0')
    checksum = hashlib.md5(key.encode()).hexdigest()[:8]
    return f"{checksum}-{key[:8]}-{key[8:16]}-{key[16:24]}"

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate and activate a demo license for PDF Harvest")
    parser.add_argument("--days", type=int, default=30, help="Days until license expires")
    parser.add_argument("--file-limit", type=int, default=10, help="File limit for bulk processing")
    parser.add_argument("--activate", action="store_true", help="Activate the license after generating")

    args = parser.parse_args()

    # Generate the demo license key
    demo_key = generate_demo_key(days=args.days, file_limit=args.file_limit)
    print(f"\nDemo license key generated: {demo_key}")
    print(f"Valid for {args.days} days with a limit of {args.file_limit} files for bulk processing")

    # Activate the license if requested
    if args.activate:
        try:
            license_manager = get_license_manager()
            success, message = license_manager.activate_with_key(demo_key)

            if success:
                print(f"\nLicense activated successfully: {message}")

                # Verify the license
                is_valid, verify_message = license_manager.verify_license()
                if is_valid:
                    print(f"License verification: {verify_message}")

                    # Get license info
                    license_info = license_manager.get_license_info()
                    if "expiry_date" in license_info:
                        try:
                            expiry_date = datetime.datetime.fromisoformat(license_info["expiry_date"])
                            print(f"Expiration date: {expiry_date.strftime('%Y-%m-%d')}")
                        except (ValueError, TypeError):
                            pass
                else:
                    print(f"License verification failed: {verify_message}")
            else:
                print(f"\nFailed to activate license: {message}")
        except Exception as e:
            print(f"\nError activating license: {str(e)}")
    else:
        print("\nTo activate this license, run:")
        print(f"python generate_demo_license.py --days {args.days} --file-limit {args.file_limit} --activate")

    return 0

if __name__ == "__main__":
    sys.exit(main())
