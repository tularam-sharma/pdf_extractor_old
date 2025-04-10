#!/usr/bin/env python3
"""
Build script for PDF Harvest application
This script:
1. Compiles Python code to C using Cython
2. Packages the application using PyInstaller
"""

import os
import sys
import shutil
import subprocess
import platform
import argparse

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
    
    # Clean up .c and .so files
    for file in os.listdir('.'):
        if file.endswith('.c') or file.endswith('.so') or file.endswith('.pyd'):
            if os.path.isfile(file):
                print(f"Removing {file}")
                os.remove(file)

def compile_with_cython():
    """Compile Python code to C using Cython"""
    return run_command(
        [sys.executable, 'setup_cython.py', 'build_ext', '--inplace'],
        "Compiling with Cython"
    )

def package_with_pyinstaller():
    """Package the application using PyInstaller"""
    return run_command(
        ['pyinstaller', 'pdfharvest.spec', '--clean'],
        "Packaging with PyInstaller"
    )

def main():
    """Main build function"""
    parser = argparse.ArgumentParser(description='Build PDF Harvest application')
    parser.add_argument('--skip-cython', action='store_true', help='Skip Cython compilation')
    parser.add_argument('--skip-clean', action='store_true', help='Skip cleaning build directories')
    args = parser.parse_args()
    
    print(f"=== Building PDF Harvest for {platform.system()} ===")
    
    # Clean build directories
    if not args.skip_clean:
        clean_build_dirs()
    
    # Compile with Cython
    if not args.skip_cython:
        if not compile_with_cython():
            print("Cython compilation failed. Exiting.")
            return 1
    
    # Package with PyInstaller
    if not package_with_pyinstaller():
        print("PyInstaller packaging failed. Exiting.")
        return 1
    
    print("\n=== Build completed successfully ===")
    print(f"Application package is available in: {os.path.abspath('dist/PDFHarvest')}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
