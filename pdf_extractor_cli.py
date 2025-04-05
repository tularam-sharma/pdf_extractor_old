#!/usr/bin/env python3
"""
Command-line interface for PDF Extractor

This script provides a command-line interface to extract data from PDF files
using templates defined in the PDF Extractor application.

Usage:
    python pdf_extractor_cli.py --folder <pdf_folder> --template <template_name> --username <username> --password <password> [--output <output_dir>] [--threads 4 <num_threads>] [--chunk 50 <chunk_size>]
"""

import os
import sys
import json
import sqlite3
import argparse
import multiprocessing
from pathlib import Path
from datetime import datetime
import concurrent.futures
import pandas as pd
import fitz  # PyMuPDF

# Import necessary functions from bulk_processor
from bulk_processor import load_template_from_database, extract_invoice_tables, process_pages_chunk, optimized_apply_regex

# Import user management for authentication
try:
    from user_management import UserManagement
except ImportError:
    print("Warning: Could not import UserManagement. Authentication might not work correctly.")
    
    # Simple fallback implementation
    class UserManagement:
        def __init__(self, db_path="user_management.db"):
            self.db_path = db_path
            
        def authenticate_user(self, username, password):
            # Simple authentication fallback
            print(f"Authenticating user: {username}...")
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, role_id FROM users WHERE username=?", (username,))
                user = cursor.fetchone()
                conn.close()
                if user:
                    print(f"Authentication successful for user: {username}")
                    return {"id": user[0], "username": user[1], "role_id": user[2]}
                print(f"Authentication failed: User {username} not found")
                return None
            except Exception as e:
                print(f"Authentication error: {str(e)}")
                return None

def get_template_id_by_name(template_name):
    """Get template ID by name"""
    try:
        conn = sqlite3.connect("invoice_templates.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM templates WHERE name = ?", (template_name,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        else:
            return None
    except Exception as e:
        print(f"Database error: {str(e)}")
        return None

def authenticate_user(username, password):
    """Authenticate user credentials"""
    try:
        user_mgmt = UserManagement()
        user = user_mgmt.authenticate_user(username, password)
        return user is not None
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        return False

def process_pdf_file(args):
    """Process a single PDF file"""
    pdf_path, template_data, output_dir, chunk_size = args
    
    try:
        print(f"Processing: {os.path.basename(pdf_path)}")
        results = extract_invoice_tables(pdf_path, template_data["id"], template_data, chunk_size)
        
        if results:
            # Check if there are no_tables_found warnings
            no_tables_warnings = results.get("no_tables_found", [])
            
            # Export data if output directory specified
            if output_dir:
                export_results(pdf_path, results, output_dir)
            
            # Determine extraction status
            extraction_status = results.get("extraction_status", {})
            overall_status = extraction_status.get("overall", "failed")
            
            if overall_status == "success":
                status = "success"
            elif overall_status == "partial":
                status = "partial"
            else:
                status = "failed"
            
            # Include information about no_tables_found
            result = {
                "path": pdf_path,
                "filename": os.path.basename(pdf_path),
                "status": status,
                "tables": {
                    "header": len(results.get("header_tables", [])),
                    "items": len(results.get("items_tables", [])),
                    "summary": len(results.get("summary_tables", [])),
                }
            }
            
            # Add warnings if any were found
            if no_tables_warnings:
                print(f"⚠️ Warning: {len(no_tables_warnings)} table areas had no tables detected in {os.path.basename(pdf_path)}")
                result["warnings"] = {
                    "no_tables_found": no_tables_warnings
                }
            
            return result
        else:
            return {
                "path": pdf_path,
                "filename": os.path.basename(pdf_path),
                "status": "failed",
                "error": "No results returned"
            }
    except Exception as e:
        print(f"Error processing {os.path.basename(pdf_path)}: {str(e)}")
        return {
            "path": pdf_path,
            "filename": os.path.basename(pdf_path),
            "status": "failed",
            "error": str(e)
        }

def export_results(pdf_path, results, output_dir):
    """Export extraction results to files"""
    try:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # Save to Excel
        excel_path = os.path.join(output_dir, f"{base_name}_extracted.xlsx")
        with pd.ExcelWriter(excel_path) as writer:
            # Write header tables
            for i, df in enumerate(results.get("header_tables", [])):
                if df is not None and not df.empty:
                    df.to_excel(writer, sheet_name=f"Header_{i+1}", index=False)
            
            # Write items tables
            for i, df in enumerate(results.get("items_tables", [])):
                if df is not None and not df.empty:
                    df.to_excel(writer, sheet_name=f"Items_{i+1}", index=False)
            
            # Write summary tables
            for i, df in enumerate(results.get("summary_tables", [])):
                if df is not None and not df.empty:
                    df.to_excel(writer, sheet_name=f"Summary_{i+1}", index=False)
        
        # Save to JSON for completeness
        json_path = os.path.join(output_dir, f"{base_name}_data.json")
        json_data = {
            "metadata": {
                "filename": os.path.basename(pdf_path),
                "export_date": datetime.now().isoformat(),
            },
            "data": {}
        }
        
        # Convert DataFrames to JSON-serializable format
        for section in ["header_tables", "items_tables", "summary_tables"]:
            json_data["data"][section] = []
            for i, df in enumerate(results.get(section, [])):
                if df is not None and not df.empty:
                    json_data["data"][section].append(df.to_dict(orient="records"))
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
            
        print(f"  Exported to {excel_path} and {json_path}")
        return True
    except Exception as e:
        print(f"  Error exporting results: {str(e)}")
        return False

def process_pdf_folder(folder_path, template_name, username, password, output_dir=None, 
                      num_threads=None, chunk_size=None):
    """Process all PDFs in a folder using the specified template
    
    Args:
        folder_path: Path to folder containing PDF files
        template_name: Name of the template to use
        username: Username for authentication
        password: Password for authentication
        output_dir: Optional output directory for extracted data
        num_threads: Number of parallel threads to use (default: CPU count)
        chunk_size: Chunk size for large documents (default: 50)
    """
    start_time = datetime.now()
    
    # Authenticate user
    if not authenticate_user(username, password):
        print("Authentication failed: Invalid username or password")
        return False

    # Get template ID from name
    template_id = get_template_id_by_name(template_name)
    if not template_id:
        print(f"Template not found: '{template_name}'")
        return False

    # Load template data
    template_data = load_template_from_database(template_id)
    if not template_data:
        print(f"Failed to load template data for template: {template_name}")
        return False
    
    # Print template info
    print(f"Using template: {template_name} (ID: {template_id})")
    print(f"Template type: {template_data.get('template_type', 'single')}")
    
    # Verify folder exists
    if not os.path.isdir(folder_path):
        print(f"Folder not found: '{folder_path}'")
        return False

    # Create output directory if specified
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    # Get all PDF files in the folder
    pdf_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in {folder_path}")
        return False

    print(f"Found {len(pdf_files)} PDF files in {folder_path}")
    
    # Determine number of threads to use
    if not num_threads:
        num_threads = min(len(pdf_files), multiprocessing.cpu_count())
    else:
        num_threads = min(num_threads, len(pdf_files), multiprocessing.cpu_count())
    
    print(f"Using {num_threads} threads for processing")
    
    # Default chunk size for large documents
    if not chunk_size:
        chunk_size = 50
    
    # Process files in parallel
    args_list = [(pdf_path, template_data, output_dir, chunk_size) for pdf_path in pdf_files]
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_pdf = {executor.submit(process_pdf_file, args): args[0] for args in args_list}
        
        # Process results as they complete
        completed = 0
        for future in concurrent.futures.as_completed(future_to_pdf):
            pdf_path = future_to_pdf[future]
            try:
                result = future.result()
                results.append(result)
                
                # Update progress
                completed += 1
                print(f"Completed {completed}/{len(pdf_files)}: {os.path.basename(pdf_path)} - {result['status']}")
            except Exception as e:
                print(f"Error processing {os.path.basename(pdf_path)}: {str(e)}")
                results.append({
                    "path": pdf_path,
                    "filename": os.path.basename(pdf_path),
                    "status": "failed",
                    "error": str(e)
                })
                completed += 1
    
    # Generate summary
    successful = [r for r in results if r["status"] == "success"]
    partial = [r for r in results if r["status"] == "partial"]
    failed = [r for r in results if r["status"] == "failed"]
    
    # Count files with warnings
    files_with_warnings = [r for r in results if "warnings" in r and "no_tables_found" in r["warnings"]]
    
    # Save summary report
    if output_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_path = os.path.join(output_dir, f"extraction_summary_{timestamp}.json")
        
        summary_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "template": template_name,
                "template_id": template_id,
                "folder": folder_path,
                "files_processed": len(pdf_files),
                "successful": len(successful),
                "partial": len(partial),
                "failed": len(failed),
                "with_warnings": len(files_with_warnings),
                "duration_seconds": (datetime.now() - start_time).total_seconds()
            },
            "results": results
        }
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2)
        
        print(f"Summary report saved to: {summary_path}")
    
    # Print final summary
    print("\n" + "="*50)
    print("EXTRACTION SUMMARY")
    print("="*50)
    print(f"Total files processed: {len(pdf_files)}")
    print(f"Successful extractions: {len(successful)}")
    if partial:
        print(f"Partial extractions: {len(partial)}")
    print(f"Failed extractions: {len(failed)}")
    if files_with_warnings:
        print(f"Files with 'No tables found' warnings: {len(files_with_warnings)}")
        for file_with_warning in files_with_warnings:
            print(f"  - {file_with_warning['filename']}: {len(file_with_warning['warnings']['no_tables_found'])} warnings")
    print(f"Duration: {datetime.now() - start_time}")
    print("="*50)
    
    return len(successful) > 0

def main():
    parser = argparse.ArgumentParser(description='Bulk PDF data extraction using templates')
    parser.add_argument('--folder', required=True, help='Folder containing PDF files to process')
    parser.add_argument('--template', required=True, help='Template name to use for extraction')
    parser.add_argument('--username', required=True, help='Username for authentication')
    parser.add_argument('--password', required=True, help='Password for authentication')
    parser.add_argument('--output', help='Output directory for extracted data (optional)')
    parser.add_argument('--threads', type=int, help='Number of threads to use for parallel processing (default: CPU count)')
    parser.add_argument('--chunk', type=int, help='Chunk size for large documents (default: 50)')
    
    args = parser.parse_args()
    
    result = process_pdf_folder(
        args.folder, 
        args.template, 
        args.username, 
        args.password, 
        args.output,
        args.threads,
        args.chunk
    )
    
    # Return success/failure code
    sys.exit(0 if result else 1)

if __name__ == '__main__':
    main() 