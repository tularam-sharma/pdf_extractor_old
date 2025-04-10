#!/usr/bin/env python3
"""
Database Protection Module

This module provides functions to encrypt and decrypt the user_management.db file
to protect it from unauthorized access or tampering.
"""

import os
import sys
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import sqlite3
import platform
import uuid

# Constants
DB_FILENAME = "user_management.db"
ENCRYPTED_EXTENSION = ".enc"
SALT_FILE = ".db_salt"

def get_machine_key():
    """
    Generate a machine-specific key based on hardware identifiers.
    This ensures the database can only be decrypted on the same machine.
    """
    # Get system information
    system_info = {
        "machine_id": str(uuid.getnode()),  # MAC address as integer
        "platform": platform.platform(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "system": platform.system(),
        "version": platform.version(),
    }
    
    # Create a stable hardware ID by hashing system information
    hardware_id_str = f"{system_info['machine_id']}:{system_info['platform']}:{system_info['system']}"
    hardware_id = hashlib.sha256(hardware_id_str.encode()).digest()
    
    return hardware_id

def get_encryption_key():
    """
    Get or create the encryption key based on machine-specific information.
    Uses a salt file to ensure the key is consistent across runs but unique to the installation.
    """
    # Get machine-specific key
    machine_key = get_machine_key()
    
    # Check if salt file exists
    if os.path.exists(SALT_FILE):
        with open(SALT_FILE, "rb") as f:
            salt = f.read()
    else:
        # Generate a new salt and save it
        salt = os.urandom(16)
        with open(SALT_FILE, "wb") as f:
            f.write(salt)
    
    # Derive key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    # Derive the key from the machine key
    key = base64.urlsafe_b64encode(kdf.derive(machine_key))
    
    return key

def encrypt_database():
    """
    Encrypt the user_management.db file to protect it from unauthorized access.
    """
    # Check if database exists
    if not os.path.exists(DB_FILENAME):
        print(f"Error: {DB_FILENAME} not found.")
        return False
    
    # Check if database is already encrypted
    encrypted_filename = f"{DB_FILENAME}{ENCRYPTED_EXTENSION}"
    if os.path.exists(encrypted_filename):
        print(f"Database is already encrypted as {encrypted_filename}")
        return True
    
    try:
        # Get encryption key
        key = get_encryption_key()
        fernet = Fernet(key)
        
        # Read the database file
        with open(DB_FILENAME, "rb") as f:
            db_data = f.read()
        
        # Encrypt the data
        encrypted_data = fernet.encrypt(db_data)
        
        # Write the encrypted data
        with open(encrypted_filename, "wb") as f:
            f.write(encrypted_data)
        
        print(f"Database encrypted successfully as {encrypted_filename}")
        
        # Keep the original for now, but you can remove it in production
        # os.remove(DB_FILENAME)
        
        return True
    
    except Exception as e:
        print(f"Error encrypting database: {str(e)}")
        return False

def decrypt_database():
    """
    Decrypt the encrypted user_management.db file for use by the application.
    """
    # Check if encrypted database exists
    encrypted_filename = f"{DB_FILENAME}{ENCRYPTED_EXTENSION}"
    if not os.path.exists(encrypted_filename):
        print(f"Error: {encrypted_filename} not found.")
        return False
    
    try:
        # Get encryption key
        key = get_encryption_key()
        fernet = Fernet(key)
        
        # Read the encrypted database file
        with open(encrypted_filename, "rb") as f:
            encrypted_data = f.read()
        
        # Decrypt the data
        decrypted_data = fernet.decrypt(encrypted_data)
        
        # Write the decrypted data
        with open(DB_FILENAME, "wb") as f:
            f.write(decrypted_data)
        
        print(f"Database decrypted successfully as {DB_FILENAME}")
        
        # Verify the database is valid
        try:
            conn = sqlite3.connect(DB_FILENAME)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            conn.close()
            
            if not tables:
                print("Warning: Decrypted database appears to be empty or invalid.")
                return False
                
            print(f"Database verified successfully. Found {len(tables)} tables.")
            return True
            
        except sqlite3.Error as e:
            print(f"Error verifying decrypted database: {str(e)}")
            return False
    
    except Exception as e:
        print(f"Error decrypting database: {str(e)}")
        return False

def initialize_database_protection():
    """
    Initialize database protection by decrypting the database if it's encrypted.
    This should be called at application startup.
    """
    # Check if encrypted database exists
    encrypted_filename = f"{DB_FILENAME}{ENCRYPTED_EXTENSION}"
    if os.path.exists(encrypted_filename):
        # If both encrypted and decrypted exist, use the encrypted one
        if os.path.exists(DB_FILENAME):
            # Backup the current decrypted file just in case
            backup_filename = f"{DB_FILENAME}.bak"
            try:
                import shutil
                shutil.copy2(DB_FILENAME, backup_filename)
                print(f"Created backup of existing database as {backup_filename}")
            except Exception as e:
                print(f"Warning: Failed to create backup: {str(e)}")
        
        # Decrypt the database
        return decrypt_database()
    
    # If only the decrypted database exists, encrypt it for protection
    elif os.path.exists(DB_FILENAME):
        return encrypt_database()
    
    # Neither exists, which is a problem
    else:
        print(f"Error: Neither {DB_FILENAME} nor {encrypted_filename} found.")
        return False

def cleanup_database_protection():
    """
    Clean up database protection by encrypting the database if it's decrypted.
    This should be called at application shutdown.
    """
    # If the decrypted database exists, encrypt it
    if os.path.exists(DB_FILENAME):
        result = encrypt_database()
        
        # If encryption was successful, remove the decrypted file
        if result:
            try:
                os.remove(DB_FILENAME)
                print(f"Removed decrypted database {DB_FILENAME}")
            except Exception as e:
                print(f"Warning: Failed to remove decrypted database: {str(e)}")
        
        return result
    
    return True

if __name__ == "__main__":
    # Simple command-line interface for testing
    if len(sys.argv) < 2:
        print("Usage: python db_protection.py [encrypt|decrypt|init|cleanup]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "encrypt":
        encrypt_database()
    elif command == "decrypt":
        decrypt_database()
    elif command == "init":
        initialize_database_protection()
    elif command == "cleanup":
        cleanup_database_protection()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: encrypt, decrypt, init, cleanup")
        sys.exit(1)
