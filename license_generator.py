#!/usr/bin/env python3
"""
License Generator for PDF Harvest

This tool generates license keys for PDF Harvest with various features and limitations.
"""

import argparse
import json
import datetime
import hashlib
import binascii
import sys
import os
import zlib
import base64
from typing import Dict, Any, Optional, List

class LicenseGenerator:
    """
    License Generator for PDF Harvest
    """
    def __init__(self):
        self.editions = {
            "demo": {
                "description": "Demo Edition - Limited features and expiration",
                "features": ["basic_extraction"],
                "default_file_limit": 10,
                "default_expiry_days": 30
            },
            "basic": {
                "description": "Basic Edition - Core features only",
                "features": ["basic_extraction", "export_data", "view_templates"],
                "default_file_limit": 50,
                "default_expiry_days": 365
            },
            "professional": {
                "description": "Professional Edition - Advanced features",
                "features": ["basic_extraction", "export_data", "view_templates",
                             "advanced_extraction", "batch_processing"],
                "default_file_limit": 500,
                "default_expiry_days": 365
            },
            "enterprise": {
                "description": "Enterprise Edition - All features",
                "features": ["basic_extraction", "export_data", "view_templates",
                             "advanced_extraction", "batch_processing",
                             "api_access", "custom_templates"],
                "default_file_limit": -1,  # Unlimited
                "default_expiry_days": 365
            }
        }

    def generate_license_data(self,
                             edition: str,
                             hardware_id: Optional[str] = None,
                             expiry_days: Optional[int] = None,
                             file_limit: Optional[int] = None,
                             custom_features: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate license data with the specified parameters
        """
        # Validate edition
        edition = edition.lower()
        if edition not in self.editions:
            raise ValueError(f"Invalid edition: {edition}. Valid editions are: {', '.join(self.editions.keys())}")

        # Get edition defaults
        edition_info = self.editions[edition]

        # Set expiry date
        if expiry_days is None:
            expiry_days = edition_info["default_expiry_days"]

        expiry_date = (datetime.datetime.now() + datetime.timedelta(days=expiry_days)).isoformat()

        # Set file limit
        if file_limit is None:
            file_limit = edition_info["default_file_limit"]

        # Set features
        if custom_features is None:
            features = edition_info["features"]
        else:
            features = custom_features

        # Create license data
        license_data = {
            "edition": edition.capitalize(),
            "expiry_date": expiry_date,
            "file_limit": file_limit,
            "features": features,
            "creation_date": datetime.datetime.now().isoformat()
        }

        # Add hardware ID if provided
        if hardware_id:
            license_data["hardware_id"] = hardware_id

        return license_data

    def generate_license_key(self, license_data: Dict[str, Any]) -> str:
        """
        Generate a license key from the license data
        """
        # For simplicity, let's use a more reliable approach
        # We'll use a fixed format for the license key

        # Create a compact representation of the license data
        compact_data = {
            # Use short keys to save space
            "e": license_data.get("edition", "Basic"),  # Edition
            "f": license_data.get("file_limit", 10),    # File limit
        }

        # Add expiry date in compact form
        if "expiry_date" in license_data:
            try:
                date_obj = datetime.datetime.fromisoformat(license_data["expiry_date"])
                compact_data["d"] = date_obj.strftime("%Y%m%d")
            except (ValueError, TypeError):
                compact_data["d"] = "20991231"  # Far future date as fallback
        else:
            # Default to 1 year from now
            compact_data["d"] = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%Y%m%d")

        # Add features in compact form
        if "features" in license_data and license_data["features"]:
            # Use first letter of each feature to save space
            compact_data["ft"] = [f[0] for f in license_data["features"]]
        else:
            # Default features
            compact_data["ft"] = ["b", "e", "v"]  # basic, export, view

        # Add hardware ID if present (truncated to save space)
        if "hardware_id" in license_data and license_data["hardware_id"]:
            compact_data["h"] = license_data["hardware_id"][:16]

        # Add creation timestamp
        compact_data["t"] = int(datetime.datetime.now().timestamp())

        # Convert to JSON with minimal whitespace
        license_json = json.dumps(compact_data, separators=(',', ':'))

        # Compress the data
        compressed_bytes = zlib.compress(license_json.encode('utf-8'), level=9)

        # Convert to base64 (standard, not URL-safe, to avoid padding issues)
        b64_data = base64.b64encode(compressed_bytes).decode('ascii')

        # Calculate checksum
        checksum = hashlib.md5(b64_data.encode()).hexdigest()[:8]

        # Split the base64 data into chunks of 32 characters
        chunks = [b64_data[i:i+32] for i in range(0, len(b64_data), 32)]

        # Create the license key format: checksum-chunk1-chunk2-...
        parts = [checksum] + chunks
        license_key = "-".join(parts)

        # Log the key length
        print(f"Generated license key with {len(parts)} parts ({len(license_key)} characters)")

        return license_key

    def generate_demo_key(self, days: int = 30, file_limit: int = 10) -> str:
        """
        Generate a simple demo key with the specified expiration and file limit
        """
        # Format: DEMO + YYYYMMDD (expiry date) + NNNN (file limit)
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=days)
        date_str = expiry_date.strftime("%Y%m%d")
        limit_str = f"{file_limit:04d}"

        # Create the encoded data
        encoded_data = f"DEMO{date_str}{limit_str}"

        # Pad to ensure it's long enough
        encoded_data = encoded_data.ljust(24, '0')

        # Calculate checksum
        checksum = hashlib.md5(encoded_data.encode()).hexdigest()[:8]

        # Format the key
        key = f"{checksum}-{encoded_data[:8]}-{encoded_data[8:16]}-{encoded_data[16:24]}"

        return key

    def decode_license_key(self, key: str) -> Dict[str, Any]:
        """
        Decode a license key to view its contents
        """
        # Remove hyphens
        clean_key = key.replace("-", "")

        # Extract checksum and data
        checksum = clean_key[:8]
        encoded_data = clean_key[8:]

        # Verify checksum
        calculated_checksum = hashlib.md5(encoded_data.encode()).hexdigest()[:8]
        if calculated_checksum.lower() != checksum.lower():
            print("Warning: Checksum verification failed. The license key may be invalid.")

        # Try to decode using our new method (base64 + zlib)
        try:
            import base64
            import zlib

            # Add padding if needed
            padding_needed = len(encoded_data) % 4
            if padding_needed:
                encoded_data += "=" * (4 - padding_needed)

            # Convert from base64 to bytes
            try:
                # First try standard base64
                compressed_data = base64.b64decode(encoded_data)
            except Exception:
                # Fall back to URL-safe base64
                compressed_data = base64.urlsafe_b64decode(encoded_data)

            # Decompress
            json_bytes = zlib.decompress(compressed_data)

            # Decode JSON
            compact_data = json.loads(json_bytes.decode('utf-8'))

            # Convert compact data back to full license data
            license_data = {}

            # Edition
            if "e" in compact_data:
                license_data["edition"] = compact_data["e"]

            # Expiry date
            if "d" in compact_data:
                date_str = compact_data["d"]
                if len(date_str) == 8:  # YYYYMMDD format
                    try:
                        year = int(date_str[:4])
                        month = int(date_str[4:6])
                        day = int(date_str[6:8])
                        license_data["expiry_date"] = datetime.datetime(year, month, day).isoformat()
                    except ValueError:
                        license_data["expiry_date"] = date_str
                else:
                    license_data["expiry_date"] = date_str

            # File limit
            if "f" in compact_data:
                license_data["file_limit"] = compact_data["f"]

            # Features
            if "ft" in compact_data:
                # Convert compact features back to full names
                feature_map = {
                    "b": "basic_extraction",
                    "e": "export_data",
                    "v": "view_templates",
                    "a": "advanced_extraction",
                    "p": "batch_processing",
                    "i": "api_access",
                    "c": "custom_templates"
                }
                license_data["features"] = [feature_map.get(f, f) for f in compact_data["ft"]]

            # Hardware ID
            if "h" in compact_data:
                license_data["hardware_id"] = compact_data["h"]

            # Creation timestamp
            if "t" in compact_data:
                creation_time = datetime.datetime.fromtimestamp(compact_data["t"])
                license_data["creation_date"] = creation_time.isoformat()

            return license_data

        except Exception as e:
            print(f"Error decoding with new method: {str(e)}")

            # Try the old hex method as fallback
            try:
                # Convert hex to bytes
                data_bytes = bytes.fromhex(encoded_data)
                # Decode as JSON
                decoded_str = data_bytes.decode('utf-8')
                license_data = json.loads(decoded_str)
                return license_data
            except Exception:
                pass

            # If that fails, try our fallback method for demo keys
            if encoded_data.startswith("DEMO"):
                # Demo license format
                edition = "Demo"
                # Extract expiry date (YYYYMMDD format)
                date_str = encoded_data[4:12]
                try:
                    year = int(date_str[:4])
                    month = int(date_str[4:6])
                    day = int(date_str[6:8])
                    expiry_date = datetime.datetime(year, month, day).isoformat()
                except ValueError:
                    # Default to 30 days from now if date is invalid
                    expiry_date = (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()

                # Extract file limit if present
                file_limit = 10  # Default
                if len(encoded_data) > 12:
                    try:
                        file_limit = int(encoded_data[12:16])
                    except ValueError:
                        pass

                return {
                    "edition": edition,
                    "expiry_date": expiry_date,
                    "file_limit": file_limit,
                    "features": ["basic_extraction"],
                    "is_demo": True
                }

            print("Error: Could not decode license key.")
            return {}

def main():
    """Main function for the license generator"""
    parser = argparse.ArgumentParser(description="Generate license keys for PDF Harvest")

    # Command subparsers
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate a license key")
    generate_parser.add_argument("--edition", "-e", choices=["demo", "basic", "professional", "enterprise"],
                               default="basic", help="License edition")
    generate_parser.add_argument("--hardware-id", "-hw", help="Hardware ID to bind the license to")
    generate_parser.add_argument("--expiry-days", "-d", type=int, help="Days until license expires")
    generate_parser.add_argument("--file-limit", "-f", type=int, help="Maximum number of files for bulk processing")
    generate_parser.add_argument("--features", "-ft", nargs="+", help="Custom features to include")
    generate_parser.add_argument("--output", "-o", help="Output file for the license key")

    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Generate a demo license key")
    demo_parser.add_argument("--days", "-d", type=int, default=30, help="Days until demo expires")
    demo_parser.add_argument("--file-limit", "-f", type=int, default=10, help="Maximum number of files for bulk processing")
    demo_parser.add_argument("--output", "-o", help="Output file for the license key")

    # Decode command
    decode_parser = subparsers.add_parser("decode", help="Decode a license key")
    decode_parser.add_argument("key", help="License key to decode")

    # List editions command
    subparsers.add_parser("list-editions", help="List available license editions")

    # Parse arguments
    args = parser.parse_args()

    # Create license generator
    generator = LicenseGenerator()

    # Execute command
    if args.command == "generate":
        try:
            # Generate license data
            license_data = generator.generate_license_data(
                edition=args.edition,
                hardware_id=args.hardware_id,
                expiry_days=args.expiry_days,
                file_limit=args.file_limit,
                custom_features=args.features
            )

            # Generate license key
            license_key = generator.generate_license_key(license_data)

            # Print license information
            print("\nLicense Information:")
            print(f"Edition: {license_data['edition']}")

            # Format expiry date
            try:
                expiry_date = datetime.datetime.fromisoformat(license_data['expiry_date'])
                print(f"Expiry Date: {expiry_date.strftime('%Y-%m-%d')} ({(expiry_date - datetime.datetime.now()).days} days)")
            except (ValueError, TypeError):
                print(f"Expiry Date: {license_data['expiry_date']}")

            # Print file limit
            if license_data['file_limit'] == -1:
                print("File Limit: Unlimited")
            else:
                print(f"File Limit: {license_data['file_limit']} files")

            # Print features
            print("Features:")
            for feature in license_data['features']:
                print(f"  - {feature}")

            # Print hardware ID if present
            if 'hardware_id' in license_data:
                print(f"Hardware ID: {license_data['hardware_id']}")

            # Print license key
            print("\nLicense Key:")
            print(license_key)

            # Save to file if requested
            if args.output:
                with open(args.output, "w") as f:
                    f.write(license_key)
                print(f"\nLicense key saved to {args.output}")

        except Exception as e:
            print(f"Error generating license: {str(e)}")
            return 1

    elif args.command == "demo":
        try:
            # Generate demo key
            license_key = generator.generate_demo_key(days=args.days, file_limit=args.file_limit)

            # Print license information
            print("\nDemo License Information:")
            print(f"Edition: Demo")

            # Calculate expiry date
            expiry_date = datetime.datetime.now() + datetime.timedelta(days=args.days)
            print(f"Expiry Date: {expiry_date.strftime('%Y-%m-%d')} ({args.days} days)")
            print(f"File Limit: {args.file_limit} files")
            print("Features: basic_extraction")

            # Print license key
            print("\nLicense Key:")
            print(license_key)

            # Save to file if requested
            if args.output:
                with open(args.output, "w") as f:
                    f.write(license_key)
                print(f"\nLicense key saved to {args.output}")

        except Exception as e:
            print(f"Error generating demo license: {str(e)}")
            return 1

    elif args.command == "decode":
        try:
            # Decode license key
            license_data = generator.decode_license_key(args.key)

            if not license_data:
                print("Could not decode license key.")
                return 1

            # Print license information
            print("\nDecoded License Information:")
            for key, value in license_data.items():
                if key == "expiry_date":
                    try:
                        expiry_date = datetime.datetime.fromisoformat(value)
                        days_remaining = (expiry_date - datetime.datetime.now()).days
                        status = "Valid" if days_remaining > 0 else "Expired"
                        print(f"Expiry Date: {expiry_date.strftime('%Y-%m-%d')} ({days_remaining} days remaining) - {status}")
                    except (ValueError, TypeError):
                        print(f"Expiry Date: {value}")
                elif key == "features":
                    print("Features:")
                    for feature in value:
                        print(f"  - {feature}")
                elif key == "file_limit":
                    if value == -1:
                        print("File Limit: Unlimited")
                    else:
                        print(f"File Limit: {value} files")
                else:
                    print(f"{key.replace('_', ' ').title()}: {value}")

        except Exception as e:
            print(f"Error decoding license key: {str(e)}")
            return 1

    elif args.command == "list-editions":
        print("\nAvailable License Editions:")
        for edition, info in generator.editions.items():
            print(f"\n{edition.upper()}")
            print(f"  {info['description']}")
            print(f"  Default File Limit: {info['default_file_limit'] if info['default_file_limit'] != -1 else 'Unlimited'}")
            print(f"  Default Expiry: {info['default_expiry_days']} days")
            print("  Features:")
            for feature in info['features']:
                print(f"    - {feature}")

    else:
        parser.print_help()

    return 0

if __name__ == "__main__":
    sys.exit(main())


