#!/usr/bin/env python3
"""
Build script for creating a protected executable of PDF Harvest
"""

import os
import sys
import argparse
import subprocess

def main():
    """Main function to build the executable"""
    parser = argparse.ArgumentParser(description='Build PDF Harvest executable')
    parser.add_argument('--demo-license', action='store_true', help='Include a demo license in the build')
    parser.add_argument('--skip-clean', action='store_true', help='Skip cleaning build directories')
    parser.add_argument('--skip-deps', action='store_true', help='Skip installing dependencies')
    args = parser.parse_args()
    
    # Build command
    cmd = [sys.executable, "build_protected.py"]
    
    # Add arguments
    if args.skip_clean:
        cmd.append("--skip-clean")
    if args.skip_deps:
        cmd.append("--skip-deps")
    if args.demo_license:
        cmd.append("--demo-license")
    
    # Run the build process
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
