import sys
import os
import re
import json
import sqlite3
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QStackedWidget, QFileDialog, QMessageBox,
    QScrollArea, QFrame, QSplitter, QGridLayout, QLineEdit, QComboBox,
    QListWidget, QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox
)
from PySide6.QtCore import Qt, Signal, QObject, QRect
from PySide6.QtGui import QFont, QIcon
import pandas as pd

class BulkProcessor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.pdf_files = []
        self.processed_data = {}
        
        self.init_ui()
        self.load_templates()  # Load templates when initializing
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Template selection
        template_layout = QHBoxLayout()
        template_label = QLabel("Select Template:", self)
        self.template_combo = QComboBox(self)
        template_layout.addWidget(template_label)
        template_layout.addWidget(self.template_combo)
        template_layout.addStretch()
        layout.addLayout(template_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready", self)
        layout.addWidget(self.status_label)
        
        # File list
        self.file_list = QListWidget(self)
        layout.addWidget(self.file_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_files_btn = QPushButton("Add Files", self)
        add_files_btn.clicked.connect(self.add_files)
        button_layout.addWidget(add_files_btn)
        
        clear_files_btn = QPushButton("Clear Files", self)
        clear_files_btn.clicked.connect(self.clear_files)
        button_layout.addWidget(clear_files_btn)
        
        process_btn = QPushButton("Process Files", self)
        process_btn.clicked.connect(self.process_files)
        button_layout.addWidget(process_btn)
        
        layout.addLayout(button_layout)
        
        # Results table
        self.results_table = QTableWidget(self)
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["File Name", "Status", "Header Rows", "Item Rows"])
        layout.addWidget(self.results_table)
        
        # Export buttons
        export_layout = QHBoxLayout()
        
        export_header_btn = QPushButton("Export Header Data", self)
        export_header_btn.clicked.connect(lambda: self.export_data('header'))
        export_layout.addWidget(export_header_btn)
        
        export_items_btn = QPushButton("Export Item Data", self)
        export_items_btn.clicked.connect(lambda: self.export_data('items'))
        export_layout.addWidget(export_items_btn)
        
        export_summary_btn = QPushButton("Export Summary Data", self)
        export_summary_btn.clicked.connect(lambda: self.export_data('summary'))
        export_layout.addWidget(export_summary_btn)
        
        layout.addLayout(export_layout)
        
        # Navigation
        nav_layout = QHBoxLayout()
        
        # Back button on the left
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.go_back)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #666666;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        
        # Reset screen button on the right
        reset_btn = QPushButton("Reset Screen")
        reset_btn.clicked.connect(self.reset_screen)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffaaaa;
                color: #aa0000;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff8888;
            }
        """)
        
        nav_layout.addWidget(back_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(reset_btn)
        
        layout.addLayout(nav_layout)
        
        self.setLayout(layout)
    
    def load_templates(self):
        """Load templates from the database"""
        try:
            conn = sqlite3.connect('invoice_templates.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, template_type FROM templates")
            templates = cursor.fetchall()
            
            self.template_combo.clear()
            for template in templates:
                self.template_combo.addItem(f"{template[1]} ({template[2]})", template[0])
            
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load templates: {str(e)}")
    
    def process_files(self):
        """Process all selected PDF files using the database template"""
        if not self.pdf_files:
            QMessageBox.warning(self, "Warning", "Please select PDF files to process")
            return
            
        if self.template_combo.count() == 0:
            QMessageBox.warning(self, "Warning", "No templates available. Please create a template first.")
            return
            
        # Get selected template ID
        template_id = self.template_combo.currentData()
        template_name = self.template_combo.currentText()
        print(f"\n{'*'*100}")
        print(f"STARTING BULK PROCESSING")
        print(f"Selected template ID: {template_id}, Name: {template_name}")
        print(f"{'*'*100}")
        
        # Reset results before processing
        self.results_table.setRowCount(0)
        self.processed_data = {}
        
        try:
            print("\n" + "="*80)
            print(f"STEP 1: DATABASE CONNECTION AND TEMPLATE RETRIEVAL")
            print("="*80)
            
            # Connect to database
            print("Connecting to database: 'invoice_templates.db'")
            conn = sqlite3.connect('invoice_templates.db')
            cursor = conn.cursor()
            
            # Display database structure for debugging
            print("\nEXAMINING DATABASE STRUCTURE:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"Database tables: {[table[0] for table in tables]}")
            
            # Following the structure in database.py, fetch all template data directly
            try:
                print(f"\nATTEMPTING TO FETCH TEMPLATE WITH ID {template_id}")
                print("Using primary query based on InvoiceDatabase.save_template structure")
                query = """
                    SELECT id, name, description, template_type, regions, column_lines, config, creation_date 
                    FROM templates WHERE id = ?
                """
                print(f"Query: {query}")
                
                cursor.execute(query, (template_id,))
                template = cursor.fetchone()
                
                if template:
                    print("✓ Template found successfully!")
                    # Print column indices for reference
                    print("Column indices in result:")
                    print("  0: id")
                    print("  1: name")
                    print("  2: description")
                    print("  3: template_type")
                    print("  4: regions")
                    print("  5: column_lines")
                    print("  6: config")
                    print("  7: creation_date")
                else:
                    print("✗ Template not found with primary query")
                
            except sqlite3.OperationalError as e:
                # If the query fails, try with just the essential columns
                print(f"✗ Primary query failed with error: {str(e)}")
                
                if "no such column" in str(e):
                    print("\nDATABASE SCHEMA DIFFERS FROM EXPECTED STRUCTURE")
                    print("Trying alternative query approach...")
                    
                    cursor.execute("SELECT id, name, template_type FROM templates WHERE id = ?", (template_id,))
                    basic_template = cursor.fetchone()
                    
                    if basic_template:
                        print("✓ Basic template info found")
                        print(f"  ID: {basic_template[0]}")
                        print(f"  Name: {basic_template[1]}")
                        print(f"  Type: {basic_template[2]}")
                    else:
                        print("✗ Template not found even with basic query")
                        raise Exception(f"Template with ID {template_id} not found")
                    
                    # Get detailed column information
                    print("\nEXAMINING ACTUAL DATABASE COLUMNS:")
                    cursor.execute("PRAGMA table_info(templates)")
                    columns = cursor.fetchall()
                    print("Column structure from PRAGMA:")
                    for col in columns:
                        print(f"  {col[0]}: {col[1]} ({col[2]}), notnull={col[3]}, dflt_value={col[4]}, pk={col[5]}")
                    
                    column_names = [col[1] for col in columns]
                    print(f"Available column names: {column_names}")
                    
                    # Try to get all columns
                    print("\nFetching all columns from templates table:")
                    cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
                    template = cursor.fetchone()
                    
                    if template:
                        print(f"✓ Template data fetched with {len(template)} columns")
                    else:
                        print("✗ Failed to fetch template data")
                else:
                    raise
            
            if not template:
                raise Exception(f"Template with ID {template_id} not found")
            
            # Verify database column structure
            print("\nMAPPING DATABASE COLUMNS TO EXPECTED FIELDS:")
            cursor.execute("PRAGMA table_info(templates)")
            cols = cursor.fetchall()
            col_names = [col[1] for col in cols]
            print(f"Database columns: {', '.join(col_names)}")
            
            # Extract template data based on the expected column structure
            # Use data from column positions based on column names if possible
            print("\nFINDING JSON DATA COLUMNS:")
            regions_col = next((i for i, name in enumerate(col_names) if name == 'regions'), -1)
            column_lines_col = next((i for i, name in enumerate(col_names) if name == 'column_lines'), -1)
            config_col = next((i for i, name in enumerate(col_names) if name == 'config'), -1)
            
            if regions_col >= 0:
                print(f"✓ Found 'regions' data in column {regions_col} ('{col_names[regions_col]}')")
            else:
                print("✗ No column named 'regions' found")
                
            if column_lines_col >= 0:
                print(f"✓ Found 'column_lines' data in column {column_lines_col} ('{col_names[column_lines_col]}')")
            else:
                print("✗ No column named 'column_lines' found")
                
            if config_col >= 0:
                print(f"✓ Found 'config' data in column {config_col} ('{col_names[config_col]}')")
            else:
                print("✗ No column named 'config' found")
            
            # Print template basic info
            print("\nTEMPLATE METADATA:")
            name_col = col_names.index('name') if 'name' in col_names else 1
            type_col = col_names.index('template_type') if 'template_type' in col_names else -1
            desc_col = col_names.index('description') if 'description' in col_names else -1
            
            template_name = template[name_col] if name_col >= 0 and name_col < len(template) else "Unknown"
            template_type = template[type_col] if type_col >= 0 and type_col < len(template) else "unknown"
            description = template[desc_col] if desc_col >= 0 and desc_col < len(template) else ""
            
            print(f"  Name: {template_name}")
            print(f"  Type: {template_type}")
            if description:
                print(f"  Description: {description}")
            
            # Extract JSON data from the template row
            print("\nEXTRACTING JSON DATA FROM DATABASE ROW:")
            regions_json = template[regions_col] if regions_col >= 0 and regions_col < len(template) else None
            column_lines_json = template[column_lines_col] if column_lines_col >= 0 and column_lines_col < len(template) else None
            config_json = template[config_col] if config_col >= 0 and config_col < len(template) else None
            
            if regions_json:
                print(f"✓ Regions JSON data found ({len(regions_json)} characters)")
                print(f"  Preview: {regions_json[:100]}..." if len(regions_json) > 100 else f"  Full data: {regions_json}")
            else:
                print("✗ No regions JSON data found in the specified column")
            
            if column_lines_json:
                print(f"✓ Column lines JSON data found ({len(column_lines_json)} characters)")
                print(f"  Preview: {column_lines_json[:100]}..." if len(column_lines_json) > 100 else f"  Full data: {column_lines_json}")
            else:
                print("✗ No column_lines JSON data found in the specified column")
                
            if config_json:
                print(f"✓ Config JSON data found ({len(config_json)} characters)")
                print(f"  Preview: {config_json[:100]}..." if len(config_json) > 100 else f"  Full data: {config_json}")
            else:
                print("✗ No config JSON data found in the specified column")
            
            # If columns were not found directly, search by content
            if regions_json is None or column_lines_json is None or config_json is None:
                print("\nATTEMPTING TO IDENTIFY JSON DATA BY CONTENT ANALYSIS:")
                # Find JSON columns by content
                for i, val in enumerate(template):
                    if isinstance(val, str) and val.strip().startswith('{') and val.strip().endswith('}'):
                        try:
                            data = json.loads(val)
                            print(f"Column {i} contains valid JSON with keys: {list(data.keys())}")
                            
                            if regions_json is None and ('header' in data or 'items' in data or 'table_areas' in data):
                                regions_json = val
                                print(f"✓ Identified column {i} as regions data (contains header/items/table_areas keys)")
                            elif column_lines_json is None and any(key in data for key in ['header', 'items', 'summary']):
                                column_lines_json = val
                                print(f"✓ Identified column {i} as column_lines data (contains header/items/summary keys)")
                            elif config_json is None:
                                config_json = val
                                print(f"✓ Identified column {i} as config data (other JSON data)")
                        except json.JSONDecodeError:
                            print(f"Column {i} contains invalid JSON: {val[:30]}...")
            
            # Close database connection
            conn.close()
            print("\nDatabase connection closed")
            
            # Parse the template data
            print("\n" + "="*80)
            print(f"STEP 2: PARSING TEMPLATE JSON DATA")
            print("="*80)
            
            # Parse regions data
            print("\nPARSING REGIONS JSON:")
            try:
                if regions_json:
                    regions = json.loads(regions_json)
                    print(f"✓ Successfully parsed regions JSON with {len(regions)} keys: {list(regions.keys())}")
                    
                    # More detailed inspection of regions data
                    if 'table_areas' in regions:
                        print(f"  Using structured table_areas format with {len(regions['table_areas'])} tables:")
                        for label, info in regions['table_areas'].items():
                            rect = info.get('rect', {})
                            if isinstance(rect, dict):
                                print(f"    - {label}: type={info.get('type', 'unknown')}, "
                                     f"position=({rect.get('x', '?')},{rect.get('y', '?')}), "
                                     f"size=({rect.get('width', '?')}x{rect.get('height', '?')})")
                            else:
                                print(f"    - {label}: type={info.get('type', 'unknown')}, rect={type(rect)}")
                    else:
                        for key in regions:
                            if isinstance(regions[key], list):
                                print(f"  {key}: {len(regions[key])} rectangles")
                                if regions[key] and isinstance(regions[key][0], dict):
                                    sample = regions[key][0]
                                    print(f"    Sample: {sample}")
                else:
                    regions = {}
                    print("✗ No regions data found - tables cannot be extracted")
            except json.JSONDecodeError as e:
                print(f"✗ Error parsing regions JSON: {str(e)}")
                raise Exception(f"Invalid regions data in template: {str(e)}")
            
            # Parse column lines data
            print("\nPARSING COLUMN LINES JSON:")
            try:
                if column_lines_json:
                    column_lines = json.loads(column_lines_json)
                    print(f"✓ Successfully parsed column_lines JSON with keys: {list(column_lines.keys())}")
                    
                    # Inspect column lines data
                    for section, lines in column_lines.items():
                        print(f"  {section}: {len(lines)} column lines")
                        if lines and isinstance(lines[0], list):
                            if len(lines[0]) >= 3:
                                print(f"    Format: [point, point, rect_index]")
                            elif len(lines[0]) == 2:
                                print(f"    Format: [start_point, end_point]")
                else:
                    column_lines = {}
                    print("ℹ No column lines data found - extraction will proceed without column separators")
            except json.JSONDecodeError as e:
                print(f"✗ Error parsing column lines JSON: {str(e)}")
                column_lines = {}  # Use empty dict if parsing fails
            
            # Parse config data
            print("\nPARSING CONFIG JSON:")
            try:
                if config_json:
                    config = json.loads(config_json)
                    print(f"✓ Successfully parsed config JSON with {len(config)} settings:")
                    for key, value in config.items():
                        print(f"  {key}: {value}")
                else:
                    config = {}
                    print("ℹ No config data found - using default extraction settings")
            except json.JSONDecodeError as e:
                print(f"✗ Error parsing config JSON: {str(e)}")
                config = {}  # Use empty dict if parsing fails
            
            # Final verification of template data
            if not regions:
                print("\n✗ CRITICAL ERROR: No valid region data found")
                raise Exception("Template contains no valid region data. Please configure the template regions first.")
            
            # Process each PDF file
            self.progress_bar.setMaximum(len(self.pdf_files))
            self.progress_bar.setValue(0)
            self.results_table.setRowCount(len(self.pdf_files))
            
            print("\n" + "="*80)
            print(f"STEP 3: PROCESSING {len(self.pdf_files)} PDF FILES")
            print("="*80)
            
            # Track success and failure counts
            success_count = 0
            error_count = 0
            
            for i, pdf_path in enumerate(self.pdf_files):
                try:
                    # Update progress
                    self.progress_bar.setValue(i + 1)
                    self.status_label.setText(f"Processing {i+1}/{len(self.pdf_files)}: {os.path.basename(pdf_path)}")
                    QApplication.processEvents()
                    
                    # Log the current file being processed
                    print(f"\nPROCESSING FILE {i+1}/{len(self.pdf_files)}: {os.path.basename(pdf_path)}")
                    
                    # Check if the PDF file exists
                    if not os.path.exists(pdf_path):
                        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
                    
                    # Extract tables using the template
                    print(f"Calling extract_invoice_tables with template data...")
                    header_df, item_details_df, summary_df = self.extract_invoice_tables(pdf_path, regions, column_lines, config)
                    
                    # Verify results - make sure we got at least something
                    print("\nEXTRACTION RESULTS SUMMARY:")
                    
                    # Check header data
                    if header_df is None:
                        print("  - Header: None (no data extracted)")
                    elif isinstance(header_df, list):
                        print(f"  - Header: {len(header_df)} tables")
                        for j, df in enumerate(header_df):
                            if df is None or df.empty:
                                print(f"    Table {j+1}: Empty")
                            else:
                                print(f"    Table {j+1}: {len(df)} rows, {len(df.columns)} columns")
                                print(f"    Columns: {list(df.columns)}")
                                print(f"    First row: {df.iloc[0].to_dict() if len(df) > 0 else 'N/A'}")
                    elif header_df.empty:
                        print("  - Header: Empty DataFrame (0 rows)")
                    else:
                        print(f"  - Header: {len(header_df)} rows, {len(header_df.columns)} columns")
                        print(f"    Columns: {list(header_df.columns)}")
                        print(f"    First row: {header_df.iloc[0].to_dict() if len(header_df) > 0 else 'N/A'}")
                    
                    # Check item data
                    if item_details_df is None:
                        print("  - Items: None (no data extracted)")
                    elif item_details_df.empty:
                        print("  - Items: Empty DataFrame (0 rows)")
                    else:
                        print(f"  - Items: {len(item_details_df)} rows, {len(item_details_df.columns)} columns")
                        print(f"    Columns: {list(item_details_df.columns)}")
                        print(f"    First row: {item_details_df.iloc[0].to_dict() if len(item_details_df) > 0 else 'N/A'}")
                    
                    # Check summary data
                    if summary_df is None:
                        print("  - Summary: None (no data extracted)")
                    elif summary_df.empty:
                        print("  - Summary: Empty DataFrame (0 rows)")
                    else:
                        print(f"  - Summary: {len(summary_df)} rows, {len(summary_df.columns)} columns")
                        print(f"    Columns: {list(summary_df.columns)}")
                        print(f"    First row: {summary_df.iloc[0].to_dict() if len(summary_df) > 0 else 'N/A'}")
                        
                    if (header_df is None or (isinstance(header_df, pd.DataFrame) and header_df.empty) or 
                        (isinstance(header_df, list) and all(df is None or df.empty for df in header_df))) and \
                       (item_details_df is None or item_details_df.empty) and \
                       (summary_df is None or summary_df.empty):
                        # No data extracted from any section
                        print("⚠ WARNING: No data was extracted from the PDF")
                    else:
                        print("✓ Successfully extracted data from PDF")
                        
                    # Store results anyway
                    self.processed_data[pdf_path] = {
                        'header': header_df,
                        'items': item_details_df,
                        'summary': summary_df
                    }
                    
                    # Format row counts for display
                    header_rows = "0 rows"
                    if header_df is not None:
                        if isinstance(header_df, list):
                            total_rows = sum(len(df) if df is not None and not df.empty else 0 for df in header_df)
                            header_rows = f"{total_rows} rows ({len(header_df)} tables)"
                        else:
                            header_rows = f"{len(header_df) if not header_df.empty else 0} rows"
                    
                    item_rows = "0 rows"
                    if item_details_df is not None and not item_details_df.empty:
                        item_rows = f"{len(item_details_df)} rows"
                    
                    summary_rows = "0 rows"
                    if summary_df is not None and not summary_df.empty:
                        summary_rows = f"{len(summary_df)} rows"
                    
                    # Update results table with detailed information
                    self.results_table.setItem(i, 0, QTableWidgetItem(os.path.basename(pdf_path)))
                    self.results_table.setItem(i, 1, QTableWidgetItem("Success"))
                    self.results_table.setItem(i, 2, QTableWidgetItem(header_rows))
                    self.results_table.setItem(i, 3, QTableWidgetItem(item_rows))
                    
                    # Log success
                    print(f"  Results added to table:")
                    print(f"  - Header: {header_rows}")
                    print(f"  - Items: {item_rows}")
                    print(f"  - Summary: {summary_rows}")
                    
                    success_count += 1
                    
                except Exception as e:
                    # Update results table with error information
                    self.results_table.setItem(i, 0, QTableWidgetItem(os.path.basename(pdf_path)))
                    self.results_table.setItem(i, 1, QTableWidgetItem(f"Error: {str(e)}"))
                    self.results_table.setItem(i, 2, QTableWidgetItem(""))
                    self.results_table.setItem(i, 3, QTableWidgetItem(""))
                    
                    # Log detailed error message
                    print(f"✗ Error processing file {pdf_path}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    
                    error_count += 1
            
            # Resize table columns to fit content
            self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            
            # Update status and show completion message
            total_str = f"{success_count} succeeded, {error_count} failed"
            self.status_label.setText(f"Processing completed: {total_str}")
            
            print("\n" + "="*80)
            print(f"PROCESSING COMPLETED: {success_count} succeeded, {error_count} failed")
            print("="*80)
            
            QMessageBox.information(self, "Processing Complete", 
                                   f"Processing complete:\n\n"
                                   f"- Files processed: {len(self.pdf_files)}\n"
                                   f"- Successful: {success_count}\n"
                                   f"- Failed: {error_count}\n\n"
                                   f"You can now export the extracted data using the export buttons below.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to process files: {str(e)}")
            self.status_label.setText("Processing failed")
            print("\n✗ CRITICAL ERROR:")
            import traceback
            traceback.print_exc()
    
    def add_files(self):
        """Add PDF files to the list"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select PDF Files",
            "",
            "PDF Files (*.pdf)"
        )
        
        for file in files:
            if file not in self.pdf_files:
                self.pdf_files.append(file)
                self.file_list.addItem(os.path.basename(file))
    
    def clear_files(self):
        """Clear the file list"""
        self.pdf_files.clear()
        self.file_list.clear()
        self.results_table.setRowCount(0)
        self.processed_data.clear()
    
    def export_data(self, section):
        """Export processed data in JSON format"""
        if not self.processed_data:
            QMessageBox.warning(self, "Warning", "No processed data available to export")
            return
            
        try:
            # Create export directory if it doesn't exist
            export_dir = "exported_data"
            os.makedirs(export_dir, exist_ok=True)
            
            # Prepare data for export
            export_data = {}
            for pdf_path, data in self.processed_data.items():
                if data[section] is not None:
                    # Handle case where data is a list of dataframes (multiple header tables)
                    if isinstance(data[section], list):
                        # Create a combined dictionary with table indexes
                        tables_dict = {}
                        for i, df in enumerate(data[section]):
                            if df is not None and not df.empty:
                                tables_dict[f'table_{i}'] = df.to_dict(orient='records')
                        export_data[os.path.basename(pdf_path)] = tables_dict
                    else:
                        # Regular case - single dataframe
                        export_data[os.path.basename(pdf_path)] = data[section].to_dict(orient='records')
            
            # Save to JSON file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{export_dir}/{section}_data_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "Success", f"Data exported successfully to {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def go_back(self):
        """Return to the main screen"""
        if self.parent:  # Check if parent is not None
            self.parent.stacked_widget.setCurrentWidget(self.parent.main_screen)
        else:
            print("Parent is not set correctly.")
    
    def reset_screen(self):
        """Reset the screen to its initial state"""
        # Clear all data
        self.pdf_files.clear()
        self.file_list.clear()
        self.results_table.setRowCount(0)
        self.processed_data.clear()
        
        # Reset progress bar
        self.progress_bar.setValue(0)
        
        # Reset status label
        self.status_label.setText("Ready")
        
        # Reset template selection if needed
        if self.template_combo.count() > 0:
            self.template_combo.setCurrentIndex(0)
        
        # Show confirmation message
        QMessageBox.information(
            self,
            "Screen Reset",
            "The screen has been reset to its initial state."
        )
    
    def extract_invoice_tables(self, pdf_path, regions, column_lines, config):
        """Extract tables from the PDF file using the template data"""
        header_df = None
        item_details_df = None
        summary_df = None
        
        try:
            if not os.path.exists(pdf_path):
                print(f"PDF file not found: {pdf_path}")
                return header_df, item_details_df, summary_df
            
            # Import required modules 
            try:
                import fitz
                import pypdf_table_extraction
            except ImportError as e:
                print(f"Error importing required modules: {str(e)}")
                print("Make sure 'PyMuPDF' and 'pypdf-table-extraction' are installed.")
                return header_df, item_details_df, summary_df
                
            print(f"\n{'='*80}")
            print(f"STARTING TABLE EXTRACTION FROM: {pdf_path}")
            print(f"{'='*80}")
            
            print("Template Data:")
            print(f"  Regions: {type(regions)}, {len(regions) if isinstance(regions, dict) else 'Not a dict'}")
            print(f"  Column Lines: {type(column_lines)}, {len(column_lines) if isinstance(column_lines, dict) else 'Not a dict'}")
            print(f"  Config: {type(config)}, {len(config) if isinstance(config, dict) else 'Not a dict'}")
            
            # Get PDF dimensions for scaling
            pdf_document = fitz.open(pdf_path)
            page = pdf_document[0]
            page_width = page.rect.width
            page_height = page.rect.height
            
            # Get the rendered dimensions - using Matrix(2, 2) for consistency with invoice_section_viewer.py
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            rendered_width = pix.width
            rendered_height = pix.height
            
            # Calculate scaling factors properly - same method as invoice_section_viewer.py
            scale_x = page_width / rendered_width
            scale_y = page_height / rendered_height
            
            print(f"Actual PDF dimensions: width={page_width} points, height={page_height} points")
            print(f"Rendered dimensions: width={rendered_width}, height={rendered_height}")
            print(f"Calculated scaling factors: x={scale_x}, y={scale_y}")
            
            pdf_document.close()
            
            # Check if we have table_areas in the template
            if 'table_areas' in regions:
                print("\nUsing structured table_areas for extraction")
                table_areas = regions['table_areas']
                
                # Process header tables
                header_dfs = []
                header_tables = [(label, info) for label, info in table_areas.items() 
                                if info['type'] == 'header']
                
                # Sort by index to preserve original order
                header_tables.sort(key=lambda x: x[1]['index'])
                
                for label, table_info in header_tables:
                    rect = table_info['rect']
                    
                    # Handle both QRect objects and dictionary rect representations
                    if isinstance(rect, dict):
                        x1 = rect['x'] * scale_x
                        y1 = page_height - (rect['y'] * scale_y)
                        x2 = (rect['x'] + rect['width']) * scale_x
                        y2 = page_height - ((rect['y'] + rect['height']) * scale_y)
                    else:
                        x1 = rect.x() * scale_x
                        y1 = page_height - (rect.y() * scale_y)
                        x2 = (rect.x() + rect.width()) * scale_x
                        y2 = page_height - ((rect.y() + rect.height()) * scale_y)
                    
                    table_area = f"{x1},{y1},{x2},{y2}"
                    
                    # Get column lines
                    region_columns = None
                    if 'columns' in table_info and table_info['columns']:
                        columns = table_info['columns']
                        scaled_columns = [x * scale_x for x in columns]
                        region_columns = ','.join([str(x) for x in sorted(scaled_columns)])
                    
                    # Extract table
                    try:
                        tables = pypdf_table_extraction.read_pdf(
                            pdf_path,
                            flavor='stream',
                            pages='1',
                            table_areas=[table_area],
                            columns=[region_columns] if region_columns else None,
                            split_text=True,
                            strip_text='\n',
                            row_tol=10
                        )
                        
                        if tables and tables[0].df is not None and not tables[0].df.empty:
                            header_dfs.append(tables[0].df)
                            print(f"Extracted header table {label} with {len(tables[0].df)} rows")
                    except Exception as e:
                        print(f"Error extracting header table: {str(e)}")
                
                # Keep header_df as a list of DataFrames
                if header_dfs:
                    header_df = header_dfs[0] if len(header_dfs) == 1 else header_dfs
                    print(f"Successfully processed {len(header_dfs)} header tables")
                
                # Process items table
                items_tables = [(label, info) for label, info in table_areas.items() 
                              if info['type'] == 'items']
                
                if items_tables:
                    items_tables.sort(key=lambda x: x[1]['index'])
                    label, table_info = items_tables[0]  # Usually just one items table
                    rect = table_info['rect']
                    
                    # Handle both QRect objects and dictionary rect representations
                    if isinstance(rect, dict):
                        x1 = rect['x'] * scale_x
                        y1 = page_height - (rect['y'] * scale_y)
                        x2 = (rect['x'] + rect['width']) * scale_x
                        y2 = page_height - ((rect['y'] + rect['height']) * scale_y)
                    else:
                        x1 = rect.x() * scale_x
                        y1 = page_height - (rect.y() * scale_y)
                        x2 = (rect.x() + rect.width()) * scale_x
                        y2 = page_height - ((rect.y() + rect.height()) * scale_y)
                    
                    table_area = f"{x1},{y1},{x2},{y2}"
                    
                    # Get column lines
                    region_columns = None
                    if 'columns' in table_info and table_info['columns']:
                        columns = table_info['columns']
                        scaled_columns = [x * scale_x for x in columns]
                        region_columns = ','.join([str(x) for x in sorted(scaled_columns)])
                    
                    # Extract table
                    try:
                        tables = pypdf_table_extraction.read_pdf(
                            pdf_path,
                            flavor='stream',
                            pages='1',
                            table_areas=[table_area],
                            columns=[region_columns] if region_columns else None,
                            split_text=True,
                            strip_text='\n',
                            row_tol=25
                        )
                        
                        if tables and tables[0].df is not None:
                            item_details_df = tables[0].df
                            print(f"Extracted items table with {len(item_details_df)} rows")
                    except Exception as e:
                        print(f"Error extracting items table: {str(e)}")
                
                # Process summary table
                summary_tables = [(label, info) for label, info in table_areas.items() 
                                if info['type'] == 'summary']
                
                if summary_tables:
                    summary_tables.sort(key=lambda x: x[1]['index'])
                    label, table_info = summary_tables[0]  # Usually just one summary table
                    rect = table_info['rect']
                    
                    # Handle both QRect objects and dictionary rect representations
                    if isinstance(rect, dict):
                        x1 = rect['x'] * scale_x
                        y1 = page_height - (rect['y'] * scale_y)
                        x2 = (rect['x'] + rect['width']) * scale_x
                        y2 = page_height - ((rect['y'] + rect['height']) * scale_y)
                    else:
                        x1 = rect.x() * scale_x
                        y1 = page_height - (rect.y() * scale_y)
                        x2 = (rect.x() + rect.width()) * scale_x
                        y2 = page_height - ((rect.y() + rect.height()) * scale_y)
                    
                    table_area = f"{x1},{y1},{x2},{y2}"
                    
                    # Get column lines
                    region_columns = None
                    if 'columns' in table_info and table_info['columns']:
                        columns = table_info['columns']
                        scaled_columns = [x * scale_x for x in columns]
                        region_columns = ','.join([str(x) for x in sorted(scaled_columns)])
                    
                    # Extract table
                    try:
                        tables = pypdf_table_extraction.read_pdf(
                            pdf_path,
                            flavor='stream',
                            pages='1',
                            table_areas=[table_area],
                            columns=[region_columns] if region_columns else None,
                            split_text=True,
                            strip_text='\n',
                            row_tol=10
                        )
                        
                        if tables and tables[0].df is not None:
                            summary_df = tables[0].df
                            print(f"Extracted summary table with {len(summary_df)} rows")
                    except Exception as e:
                        print(f"Error extracting summary table: {str(e)}")
            # Handle traditional regions format
            else:
                print("\nFalling back to traditional regions format")
                
                # Process header regions
                header_dfs = []
                if 'header' in regions and regions['header']:
                    header_regions = regions['header']
                    print(f"Found {len(header_regions)} header regions")
                    
                    for i, rect_data in enumerate(header_regions):
                        # Create QRect from dictionary or use provided QRect
                        if isinstance(rect_data, dict):
                            if all(k in rect_data for k in ['x', 'y', 'width', 'height']):
                                # Create QRect from dictionary format
                                rect = QRect(rect_data['x'], rect_data['y'], rect_data['width'], rect_data['height'])
                                print(f"  Using dictionary format for header region {i}: x={rect_data['x']}, y={rect_data['y']}, w={rect_data['width']}, h={rect_data['height']}")
                            else:
                                print(f"  Invalid rectangle format for header {i}")
                                continue
                        else:
                            # Use provided QRect object
                            rect = rect_data
                            print(f"  Using QRect object for header region {i}: x={rect.x()}, y={rect.y()}, w={rect.width()}, h={rect.height()}")
                        
                        # Convert to table area format - same coordinate conversion as invoice_section_viewer.py
                        # This conversion does TWO things:
                        # 1. Scales coordinates according to the calculated scale factors
                        # 2. Converts from top-left (UI) to bottom-left (PDF) coordinate system
                        x1 = rect.x() * scale_x
                        y1 = page_height - (rect.y() * scale_y)  # Flip Y-axis for PDF coordinates
                        x2 = (rect.x() + rect.width()) * scale_x
                        y2 = page_height - ((rect.y() + rect.height()) * scale_y)  # Flip Y-axis
                        table_area = f"{x1},{y1},{x2},{y2}"
                        print(f"  Converted coordinates to PDF space (bottom-left origin): ({x1},{y1})-({x2},{y2})")
                        
                        # Process column lines
                        region_columns = None
                        column_x_coords = []
                        if 'header' in column_lines and column_lines['header']:
                            print(f"  Looking for column lines for region {i}:")
                            for line in column_lines['header']:
                                # Two cases: line with region index or line without region index
                                if isinstance(line, list) and len(line) >= 2:
                                    # Check if line belongs to this region
                                    if (len(line) == 3 and line[2] == i) or (len(line) == 2 and i == 0):
                                        # Get the x-coordinate from either QPoint or dictionary
                                        if hasattr(line[0], 'x'):  # QPoint
                                            x_coord = line[0].x() * scale_x
                                            print(f"    Found line at x={line[0].x()} (QPoint) -> scaled to {x_coord}")
                                        elif isinstance(line[0], dict) and 'x' in line[0]:  # Dict
                                            x_coord = line[0]['x'] * scale_x
                                            print(f"    Found line at x={line[0]['x']} (dict) -> scaled to {x_coord}")
                                        else:
                                            print(f"    Skipping line with invalid format: {line}")
                                            continue
                                            
                                        column_x_coords.append(x_coord)
                            
                            if column_x_coords:
                                # Sort column lines by x-coordinate and join as comma-separated string
                                region_columns = ','.join([str(x) for x in sorted(column_x_coords)])
                                print(f"  Final column lines for header region {i}: {region_columns}")
                        
                        # Extract table
                        try:
                            extract_params = {
                                'flavor': 'stream',
                                'pages': '1',
                                'table_areas': [table_area],
                                'columns': [region_columns] if region_columns else None,
                                'split_text': True,
                                'strip_text': '\n',
                                'row_tol': 10
                            }
                            
                            print(f"  Extraction parameters for header {i}:")
                            print(f"    - table_areas: {extract_params['table_areas']}")
                            print(f"    - columns: {extract_params['columns']}")
                            
                            tables = pypdf_table_extraction.read_pdf(pdf_path, **extract_params)
                            
                            if tables and tables[0].df is not None and not tables[0].df.empty:
                                table_df = tables[0].df
                                # Clean the DataFrame
                                table_df = table_df.replace(r'^\s*$', pd.NA, regex=True)
                                table_df = table_df.dropna(how='all')
                                table_df = table_df.dropna(axis=1, how='all')
                                
                                if not table_df.empty:
                                    header_dfs.append(table_df)
                                    print(f"  Successfully extracted header {i} with {len(table_df)} rows and {len(table_df.columns)} columns")
                                else:
                                    print(f"  No valid data found in header {i} after cleaning")
                            else:
                                print(f"  No data extracted from header {i}")
                        except Exception as e:
                            print(f"  Error extracting header {i}: {str(e)}")
                
                # Set header_df based on number of tables found
                if header_dfs:
                    header_df = header_dfs[0] if len(header_dfs) == 1 else header_dfs
                    print(f"Successfully processed {len(header_dfs)} header tables")
                
                # Process items table
                if 'items' in regions and regions['items']:
                    items_regions = regions['items']
                    print(f"Found {len(items_regions)} items regions")
                    
                    if items_regions:
                        rect_data = items_regions[0]
                        # Create QRect from dictionary or use provided QRect
                        if isinstance(rect_data, dict):
                            if all(k in rect_data for k in ['x', 'y', 'width', 'height']):
                                # Create QRect from dictionary format
                                rect = QRect(rect_data['x'], rect_data['y'], rect_data['width'], rect_data['height'])
                                print(f"Using dictionary format for items: x={rect_data['x']}, y={rect_data['y']}, w={rect_data['width']}, h={rect_data['height']}")
                            else:
                                print(f"Invalid rectangle format for items")
                                return header_df, item_details_df, summary_df
                        else:
                            # Use provided QRect object
                            rect = rect_data
                            print(f"Using QRect object for items: x={rect.x()}, y={rect.y()}, w={rect.width()}, h={rect.height()}")
                        
                        # Convert to table area format with proper coordinate system conversion
                        x1 = rect.x() * scale_x
                        y1 = page_height - (rect.y() * scale_y)  # Flip Y-axis for PDF coordinates
                        x2 = (rect.x() + rect.width()) * scale_x
                        y2 = page_height - ((rect.y() + rect.height()) * scale_y)  # Flip Y-axis
                        table_area = f"{x1},{y1},{x2},{y2}"
                        print(f"Converted items coordinates to PDF space (bottom-left origin): ({x1},{y1})-({x2},{y2})")
                        
                        # Process column lines
                        region_columns = None
                        column_x_coords = []
                        if 'items' in column_lines and column_lines['items']:
                            print(f"Looking for column lines for items:")
                            for line in column_lines['items']:
                                if isinstance(line, list) and len(line) >= 2:
                                    # Get the x-coordinate from either QPoint or dictionary
                                    if hasattr(line[0], 'x'):  # QPoint
                                        x_coord = line[0].x() * scale_x
                                        print(f"  Found line at x={line[0].x()} (QPoint) -> scaled to {x_coord}")
                                    elif isinstance(line[0], dict) and 'x' in line[0]:  # Dict
                                        x_coord = line[0]['x'] * scale_x
                                        print(f"  Found line at x={line[0]['x']} (dict) -> scaled to {x_coord}")
                                    else:
                                        print(f"  Skipping line with invalid format: {line}")
                                        continue
                                        
                                    column_x_coords.append(x_coord)
                            
                            if column_x_coords:
                                # Sort column lines by x-coordinate and join as comma-separated string
                                region_columns = ','.join([str(x) for x in sorted(column_x_coords)])
                                print(f"Final column lines for items: {region_columns}")
                        
                        # Extract table
                        try:
                            extract_params = {
                                'flavor': 'stream',
                                'pages': '1',
                                'table_areas': [table_area],
                                'columns': [region_columns] if region_columns else None,
                                'split_text': True,
                                'strip_text': '\n',
                                'row_tol': 25
                            }
                            
                            print(f"Extraction parameters for items:")
                            print(f"  - table_areas: {extract_params['table_areas']}")
                            print(f"  - columns: {extract_params['columns']}")
                            
                            tables = pypdf_table_extraction.read_pdf(pdf_path, **extract_params)
                            
                            if tables and tables[0].df is not None:
                                item_details_df = tables[0].df
                                # Clean the DataFrame
                                item_details_df = item_details_df.replace(r'^\s*$', pd.NA, regex=True)
                                item_details_df = item_details_df.dropna(how='all')
                                item_details_df = item_details_df.dropna(axis=1, how='all')
                                
                                if not item_details_df.empty:
                                    print(f"Successfully extracted items table with {len(item_details_df)} rows and {len(item_details_df.columns)} columns")
                                else:
                                    print(f"No valid data found in items table after cleaning")
                            else:
                                print(f"No data extracted from items table")
                        except Exception as e:
                            print(f"Error extracting items table: {str(e)}")
                
                # Process summary table
                if 'summary' in regions and regions['summary']:
                    summary_regions = regions['summary']
                    print(f"Found {len(summary_regions)} summary regions")
                    
                    if summary_regions:
                        rect_data = summary_regions[0]
                        # Create QRect from dictionary or use provided QRect
                        if isinstance(rect_data, dict):
                            if all(k in rect_data for k in ['x', 'y', 'width', 'height']):
                                # Create QRect from dictionary format
                                rect = QRect(rect_data['x'], rect_data['y'], rect_data['width'], rect_data['height'])
                                print(f"Using dictionary format for summary: x={rect_data['x']}, y={rect_data['y']}, w={rect_data['width']}, h={rect_data['height']}")
                            else:
                                print(f"Invalid rectangle format for summary")
                                return header_df, item_details_df, summary_df
                        else:
                            # Use provided QRect object
                            rect = rect_data
                            print(f"Using QRect object for summary: x={rect.x()}, y={rect.y()}, w={rect.width()}, h={rect.height()}")
                        
                        # Convert to table area format with proper coordinate system conversion
                        x1 = rect.x() * scale_x
                        y1 = page_height - (rect.y() * scale_y)  # Flip Y-axis for PDF coordinates
                        x2 = (rect.x() + rect.width()) * scale_x
                        y2 = page_height - ((rect.y() + rect.height()) * scale_y)  # Flip Y-axis
                        table_area = f"{x1},{y1},{x2},{y2}"
                        print(f"Converted summary coordinates to PDF space (bottom-left origin): ({x1},{y1})-({x2},{y2})")
                        
                        # Process column lines
                        region_columns = None
                        column_x_coords = []
                        if 'summary' in column_lines and column_lines['summary']:
                            print(f"Looking for column lines for summary:")
                            for line in column_lines['summary']:
                                if isinstance(line, list) and len(line) >= 2:
                                    # Get the x-coordinate from either QPoint or dictionary
                                    if hasattr(line[0], 'x'):  # QPoint
                                        x_coord = line[0].x() * scale_x
                                        print(f"  Found line at x={line[0].x()} (QPoint) -> scaled to {x_coord}")
                                    elif isinstance(line[0], dict) and 'x' in line[0]:  # Dict
                                        x_coord = line[0]['x'] * scale_x
                                        print(f"  Found line at x={line[0]['x']} (dict) -> scaled to {x_coord}")
                                    else:
                                        print(f"  Skipping line with invalid format: {line}")
                                        continue
                                        
                                    column_x_coords.append(x_coord)
                            
                            if column_x_coords:
                                # Sort column lines by x-coordinate and join as comma-separated string
                                region_columns = ','.join([str(x) for x in sorted(column_x_coords)])
                                print(f"Final column lines for summary: {region_columns}")
                        
                        # Extract table
                        try:
                            extract_params = {
                                'flavor': 'stream',
                                'pages': '1',
                                'table_areas': [table_area],
                                'columns': [region_columns] if region_columns else None,
                                'split_text': True,
                                'strip_text': '\n',
                                'row_tol': 10
                            }
                            
                            print(f"Extraction parameters for summary:")
                            print(f"  - table_areas: {extract_params['table_areas']}")
                            print(f"  - columns: {extract_params['columns']}")
                            
                            tables = pypdf_table_extraction.read_pdf(pdf_path, **extract_params)
                            
                            if tables and tables[0].df is not None:
                                summary_df = tables[0].df
                                # Clean the DataFrame
                                summary_df = summary_df.replace(r'^\s*$', pd.NA, regex=True)
                                summary_df = summary_df.dropna(how='all')
                                summary_df = summary_df.dropna(axis=1, how='all')
                                
                                if not summary_df.empty:
                                    print(f"Successfully extracted summary table with {len(summary_df)} rows and {len(summary_df.columns)} columns")
                                else:
                                    print(f"No valid data found in summary table after cleaning")
                            else:
                                print(f"No data extracted from summary table")
                        except Exception as e:
                            print(f"Error extracting summary table: {str(e)}")
            
            return header_df, item_details_df, summary_df
        
        except Exception as e:
            print(f"Error extracting tables: {str(e)}")
            import traceback
            traceback.print_exc()
            return header_df, item_details_df, summary_df 