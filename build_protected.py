#!/usr/bin/env python3
"""
Build script for PDF Harvest application with protection
This script:
1. Packages the application using PyInstaller with obfuscation
2. Includes hardware locking
"""

import os
import sys
import shutil
import subprocess
import platform
import argparse
import random
import string
import datetime
import hashlib

def run_command(command, description=None):
    """Run a shell command and print output"""
    if description:
        print(f"\n=== {description} ===")

    print(f"Running: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: Command failed with code {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        return False

    print(f"Success: {result.stdout.strip()}")
    return True

def clean_build_dirs():
    """Clean up build directories"""
    print("\n=== Cleaning build directories ===")
    dirs_to_clean = ['build', 'dist', '__pycache__']

    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Removing {dir_name}/")
            shutil.rmtree(dir_name)

def generate_random_name(length=8):
    """Generate a random name for obfuscation"""
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))

def create_obfuscated_spec():
    """Create an obfuscated PyInstaller spec file"""
    print("\n=== Creating obfuscated spec file ===")

    # Generate random names for obfuscation
    random_names = {
        'pyz': generate_random_name(),
        'exe': generate_random_name(),
        'coll': generate_random_name(),
        'a': generate_random_name(),
    }

    # List of data files to include
    added_files = [
        ('invoice_templates.db', '.'),  # Include the database
        ('*.json', '.'),  # Include any JSON files
        ('user_management.db.enc', '.'),  # Include the encrypted user database
        ('.db_salt', '.'),  # Include the salt file for database decryption
    ]

    # Add license files if they exist
    if os.path.exists('license.dat'):
        added_files.append(('license.dat', '.'))
    if os.path.exists('.license_salt'):
        added_files.append(('.license_salt', '.'))

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

{random_names['a']} = Analysis(
    ['main.py'],  # Main script
    pathex=[],
    binaries=[],
    datas={added_files},
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'pandas',
        'numpy',
        'fitz',
        'pypdf_table_extraction',
        'sqlite3',
        'json',
        'datetime',
        'uuid',
        'hashlib',
        'platform',
        'socket',
        'requests',
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'base64',
        'shutil',
        'zlib',
        'binascii',
        'activation_dialog',
        'license_manager',
        'db_protection',
        'license_generator'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

{random_names['pyz']} = PYZ({random_names['a']}.pure, {random_names['a']}.zipped_data, cipher=block_cipher)

{random_names['exe']} = EXE(
    {random_names['pyz']},
    {random_names['a']}.scripts,
    [],
    exclude_binaries=True,
    name='PDFHarvest',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to False for GUI applications
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

{random_names['coll']} = COLLECT(
    {random_names['exe']},
    {random_names['a']}.binaries,
    {random_names['a']}.zipfiles,
    {random_names['a']}.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PDFHarvest',
)
"""

    # Write the spec file
    spec_file = 'pdfharvest_protected.spec'
    with open(spec_file, 'w') as f:
        f.write(spec_content)

    print(f"Created obfuscated spec file: {spec_file}")
    return spec_file

def package_with_pyinstaller(spec_file):
    """Package the application using PyInstaller"""
    return run_command(
        ['pyinstaller', spec_file, '--clean'],
        "Packaging with PyInstaller"
    )

def prepare_database():
    """Prepare the user database for packaging by encrypting it"""
    print("\n=== Preparing user database for packaging ===")

    # Check if db_protection module is available
    try:
        import db_protection

        # Check if user_management.db exists
        if os.path.exists("user_management.db"):
            print("Encrypting user_management.db for packaging...")

            # Encrypt the database
            if db_protection.encrypt_database():
                print("Database encrypted successfully.")
                return True
            else:
                print("Failed to encrypt database.")
                return False
        else:
            print("Warning: user_management.db not found. Skipping encryption.")
            return True

    except ImportError:
        print("Warning: db_protection module not found. Skipping database encryption.")
        return True

def prepare_license_system():
    """Prepare the license system for packaging"""
    print("\n=== Preparing license system for packaging ===")

    # Create a demo license generator if it doesn't exist
    if not os.path.exists("license_generator.py"):
        print("Warning: license_generator.py not found. Creating a basic version...")
        try:
            with open("license_generator.py", "w") as f:
                f.write("""#!/usr/bin/env python3 Basic License Generator for PDF Harvest""")
            print("Created basic license_generator.py")
        except Exception as e:
            print(f"Failed to create license_generator.py: {str(e)}")
            return False

    # Check if license_manager.py exists
    if not os.path.exists("license_manager.py"):
        print("Warning: license_manager.py not found. License system may not work properly.")

    # Create a salt file for license encryption if it doesn't exist
    if not os.path.exists(".license_salt"):
        print("Creating license salt file...")
        try:
            # Generate a random salt
            salt = os.urandom(16).hex()
            with open(".license_salt", "w") as f:
                f.write(salt)
            print("License salt file created successfully.")
        except Exception as e:
            print(f"Failed to create license salt file: {str(e)}")
            return False

    return True

# Basic license generator implementation
# This is a placeholder - the actual implementation should be more sophisticated
class LicenseGenerator:
    def generate_demo_key(self, days=30, file_limit=10):
        """Generate a simple demo license key"""
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=days)
        date_str = expiry_date.strftime("%Y%m%d")
        key = f"DEMO{date_str}{file_limit:04d}"
        checksum = hashlib.md5(key.encode()).hexdigest()[:8]
        return f"{checksum}-{key[:8]}-{key[8:16]}-{key[16:]}"

def license_generator_main():
    parser = argparse.ArgumentParser(description="Generate license keys for PDF Harvest")
    parser.add_argument("--demo", action="store_true", help="Generate a demo license")
    parser.add_argument("--days", type=int, default=30, help="Days until license expires")
    parser.add_argument("--file-limit", type=int, default=10, help="File limit for bulk processing")

    args = parser.parse_args()

    generator = LicenseGenerator()

    if args.demo:
        key = generator.generate_demo_key(days=args.days, file_limit=args.file_limit)
        print(f"Demo license key: {key}")
    else:
        print("Please use --demo to generate a demo license")

    return 0

def install_dependencies():
    """Install required dependencies for building"""
    print("\n=== Installing required dependencies ===")

    # List of required packages
    required_packages = [
        "pyinstaller",
        "cryptography",
        "requests",
        "pyside6",
        "pandas",
        "numpy",
        "pymupdf",  # fitz
        "pypdf-table-extraction"
    ]

    for package in required_packages:
        print(f"Checking/installing {package}...")
        try:
            # Try to import the package to check if it's installed
            __import__(package)
            print(f"{package} is already installed.")
        except ImportError:
            # If not installed, install it
            print(f"Installing {package}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"Failed to install {package}: {result.stderr}")
                return False
            else:
                print(f"Successfully installed {package}.")

    return True

# Main function definition
def main():
    """Main build function"""
    parser = argparse.ArgumentParser(description='Build protected PDF Harvest application')
    parser.add_argument('--skip-clean', action='store_true', help='Skip cleaning build directories')
    parser.add_argument('--skip-deps', action='store_true', help='Skip installing dependencies')
    parser.add_argument('--skip-license', action='store_true', help='Skip license system preparation')
    parser.add_argument('--skip-db', action='store_true', help='Skip database encryption')
    parser.add_argument('--demo-license', action='store_true', help='Include a demo license in the build')
    args = parser.parse_args()

    print(f"=== Building Protected PDF Harvest for {platform.system()} ===")

    # Install dependencies if needed
    if not args.skip_deps:
        if not install_dependencies():
            print("Failed to install required dependencies. Exiting.")
            return 1

    # Prepare the license system
    if not args.skip_license:
        if not prepare_license_system():
            print("Failed to prepare the license system. Exiting.")
            return 1

        # Generate a demo license if requested
        if args.demo_license:
            print("\n=== Generating demo license ===")
            try:
                generator = LicenseGenerator()
                demo_key = generator.generate_demo_key(days=30, file_limit=10)

                # Save the demo license
                from license_manager import get_license_manager
                license_manager = get_license_manager()
                success, message = license_manager.activate_with_key(demo_key)

                if success:
                    print(f"Demo license generated and activated: {demo_key}")
                    print(f"License message: {message}")
                else:
                    print(f"Failed to activate demo license: {message}")
            except Exception as e:
                print(f"Error generating demo license: {str(e)}")

    # Prepare the user database
    if not args.skip_db:
        if not prepare_database():
            print("Failed to prepare the user database. Exiting.")
            return 1

    # Clean build directories
    if not args.skip_clean:
        clean_build_dirs()

    # Create obfuscated spec file
    spec_file = create_obfuscated_spec()

    # Package with PyInstaller
    if not package_with_pyinstaller(spec_file):
        print("PyInstaller packaging failed. Exiting.")
        return 1

    print("\n=== Build completed successfully ===")
    print(f"Protected application package is available in: {os.path.abspath('dist/PDFHarvest')}")

    # Print license information
    if args.demo_license:
        print("\nDemo license included in the build:")
        print("  - Valid for 30 days")
        print("  - Limited to 10 files for bulk processing")
        print("  - Basic features only")
    else:
        print("\nNo license included. Users will need to activate the software.")
        print("Use the license_generator.py tool to create license keys for your users.")

    return 0

if __name__ == "__main__":
    # Check if we're being called to generate a license or build the application
    if len(sys.argv) > 1 and sys.argv[1] == "--license-only":
        # Remove the first argument so argparse works correctly
        sys.argv.pop(1)
        sys.exit(license_generator_main())
    else:
        sys.exit(main())

