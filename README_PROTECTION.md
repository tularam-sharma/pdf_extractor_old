# PDF Harvest Protection System

This document explains how to build and distribute the protected version of PDF Harvest.

## Protection Features

The PDF Harvest application is protected using multiple layers of security:

1. **Hardware Locking**: The application is locked to specific hardware and requires activation.
2. **Code Obfuscation**: Python code is compiled to C using Cython, making it difficult to reverse engineer.
3. **Executable Packaging**: The application is packaged into a standalone executable using PyInstaller.

## Prerequisites

Before building the protected version, ensure you have the following installed:

- Python 3.8 or higher
- PySide6
- Cython
- PyInstaller
- All other dependencies required by PDF Harvest

You can install the required packages with:

```bash
pip install cython pyinstaller pyside6 pandas pymupdf requests
```

## Building the Protected Application

### 1. Compile with Cython

Cython compiles Python code to C, which is then compiled to machine code. This makes the code much harder to reverse engineer.

```bash
python setup_cython.py build_ext --inplace
```

### 2. Package with PyInstaller

PyInstaller packages the application into a standalone executable.

```bash
pyinstaller pdfharvest.spec --clean
```

### 3. Automated Build

For convenience, you can use the provided build script to automate the entire process:

```bash
python build.py
```

The packaged application will be available in the `dist/PDFHarvest` directory.

## License Management System

### How It Works

1. **Hardware ID Generation**: The application generates a unique hardware ID based on the user's system.
2. **License Request**: Users can generate a license request file containing their hardware ID.
3. **License Key**: You (the vendor) generate a license key specific to the user's hardware.
4. **Activation**: The user enters the license key to activate the software.

### Managing Licenses

As the vendor, you need to:

1. Receive license request files from users
2. Generate license keys for valid users
3. Distribute license keys to users

You can implement a license server or manually generate keys based on the hardware IDs.

### License Key Format

The license key should be at least 32 characters long and include at least one hyphen (-). You can use any format you prefer, such as:

```
XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
```

## Distribution

When distributing the application:

1. Provide the packaged executable to users
2. Instruct users to run the application and generate a license request
3. Process their license request and provide a license key
4. Have users enter the license key to activate the software

## Security Considerations

- The hardware locking is based on system characteristics that could change if the user upgrades their hardware
- Consider implementing an online activation system for more robust protection
- Regularly update the protection system to address any vulnerabilities

## Troubleshooting

If users encounter activation issues:

1. Verify they are using the correct license key
2. Check if their hardware has changed significantly
3. Have them generate a new license request if needed
4. Provide a new license key if appropriate
