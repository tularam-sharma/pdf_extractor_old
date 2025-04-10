# PDF Harvest Security Guide

This document explains the security features implemented in PDF Harvest and how to build and distribute the protected version.

## Security Features

PDF Harvest includes several security features to protect your intellectual property and sensitive data:

1. **Code Protection**
   - Python code is compiled and packaged into a standalone executable
   - Obfuscation techniques are applied to make reverse engineering difficult

2. **Hardware-Based Licensing**
   - The application is locked to specific hardware
   - Each installation requires a unique license key
   - License keys are tied to hardware identifiers

3. **Database Encryption**
   - The user_management.db file is encrypted when the application is not running
   - Encryption uses hardware-specific keys
   - Prevents unauthorized access to user credentials and permissions

4. **Admin-Only License Management**
   - Only administrators can manage licenses
   - Admins can remove licenses for transfer to new hardware
   - License operations are protected by permission checks

## Building the Protected Application

### Prerequisites

- Python 3.8 or higher
- Required packages (automatically installed by the build script):
  - PyInstaller
  - Cryptography

### Build Process

1. **Prepare Your Environment**
   ```bash
   # Clone or download the source code
   # Navigate to the project directory
   cd pdf_extractor
   ```

2. **Run the Build Script**
   ```bash
   python build_protected.py
   ```

   This script will:
   - Install required dependencies
   - Encrypt the user database
   - Create an obfuscated spec file
   - Package the application with PyInstaller

3. **Optional Arguments**
   - `--skip-clean`: Skip cleaning build directories
   - `--skip-deps`: Skip installing dependencies

   Example:
   ```bash
   python build_protected.py --skip-deps
   ```

4. **Output**
   The protected application will be available in the `dist/PDFHarvest` directory.

## Distribution and Licensing

### Preparing for Distribution

1. **Create a Default Admin Account**
   - Ensure there's at least one admin account in the user_management.db
   - This account will be used for initial setup and license management

2. **Encrypt the Database**
   - The build process automatically encrypts the database
   - Only the encrypted version (user_management.db.enc) should be distributed

3. **Package the Application**
   - Include all files from the `dist/PDFHarvest` directory
   - Create an installer if desired (using tools like NSIS, Inno Setup, etc.)

### License Management

1. **License Generation**
   - When users run the application, they can generate a license request
   - The request contains their hardware ID
   - You generate a license key specific to their hardware ID

2. **License Activation**
   - Users enter the license key in the activation dialog
   - The application validates the key against their hardware
   - If valid, the application is activated on their machine

3. **License Transfer**
   - Admin users can access License Management from the Admin menu
   - They can remove the current license
   - A new license request can be generated for the new hardware

## Security Best Practices

1. **Protect Your License Generation Process**
   - Keep your license generation algorithm secure
   - Consider implementing an online activation server

2. **Regular Updates**
   - Release regular updates to improve security
   - Each update can include enhanced protection measures

3. **Monitor for Unauthorized Use**
   - Consider implementing phone-home functionality
   - Track activations to detect potential piracy

4. **Secure Distribution**
   - Use secure channels to distribute your application
   - Implement code signing to prevent tampering

## Troubleshooting

### Common Issues

1. **Database Encryption Errors**
   - Ensure the cryptography package is installed
   - Check file permissions for the database files

2. **License Activation Issues**
   - Verify the hardware hasn't changed significantly
   - Check that the license key format is correct

3. **Build Failures**
   - Ensure all dependencies are installed
   - Check for any error messages in the build output

### Getting Help

For additional assistance, contact the development team at [your contact information].

---

**Note**: While these security measures significantly increase the difficulty of unauthorized use, no protection system is 100% secure. The goal is to make unauthorized use sufficiently difficult that most potential users will choose to purchase a legitimate license instead.
