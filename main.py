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
    QGroupBox, QMenu, QMenuBar
)
from PySide6.QtCore import Qt, Signal, QObject, QRect
from PySide6.QtGui import QFont, QIcon, QAction
from pdf_processor import PDFProcessor
from template_manager import TemplateManager
from invoice_section_viewer import InvoiceSectionViewer
from bulk_processor import BulkProcessor
from user_management import UserManagement
from role_based_ui import (
    MainDashboard, TemplateManagementCard, 
    BulkExtractionCard, UploadProcessCard, RoleBasedWidget,
    RoleBasedPDFProcessor
)
from user_management_ui import UserManagementDialog, RoleManagementDialog
import pandas as pd
import fitz
import pypdf_table_extraction

class PDFHarvest(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Harvest")
        self.setMinimumSize(1200, 800)
        
        # Initialize user management
        self.user_management = UserManagement()
        
        # Create menu bar
        self.create_menus()
        
        # Create stacked widget for multiple screens
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Create and add login screen
        self.show_login_on_start = False  # Set to False to bypass login at startup
        
        # Create and add main dashboard with role-based components
        self.main_dashboard = MainDashboard(self.user_management)
        self.main_dashboard.show_pdf_processor.connect(self.show_pdf_processor)
        self.main_dashboard.show_template_manager.connect(self.show_template_manager)
        self.main_dashboard.show_bulk_processor.connect(self.show_bulk_processor)
        self.main_dashboard.show_user_management.connect(self.show_user_management)
        # Connect login signals - use dashboard's integrated login panel
        self.main_dashboard.user_profile.login_requested.connect(self.handle_login_request)
        # Connect logout signal to update menus
        self.main_dashboard.user_profile.logout_requested.connect(self.update_menus)
        # Connect integrated login success signal
        self.main_dashboard.login_successful.connect(self.handle_login_success)
        self.stacked_widget.addWidget(self.main_dashboard)
        
        # Initialize other objects as None first, then create them
        self.pdf_processor = None
        self.template_manager = None
        self.multi_page_processor = None
        self.invoice_viewer = None
        
        # Create and add PDF processor screen (now using role-based version)
        self.pdf_processor = RoleBasedPDFProcessor()
        self.pdf_processor.set_user_management(self.user_management)
        self.stacked_widget.addWidget(self.pdf_processor)
        
        # Create and add template manager screen
        self.template_manager = TemplateManager(self.pdf_processor)
        self.stacked_widget.addWidget(self.template_manager)
        
        # Template manager signals
        self.template_manager.go_back.connect(lambda: self.stacked_widget.setCurrentWidget(self.main_dashboard))
        self.template_manager.template_selected.connect(self.apply_template)

        # Check if we should show login on start
        if self.show_login_on_start:
            self.handle_login_request()
        else:
            self.stacked_widget.setCurrentWidget(self.main_dashboard)

    def create_menus(self):
        """Create application menu bar with various options."""
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)
        
        # File menu
        file_menu = menubar.addMenu('&File')
        
        # Exit action
        exit_action = QAction('E&xit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Admin menu (only for developers with user_management permission)
        self.admin_menu = menubar.addMenu('&Admin')
        
        # User management action
        self.user_management_action = QAction('&User Management', self)
        self.user_management_action.setStatusTip('Manage users and permissions')
        self.user_management_action.triggered.connect(self.show_user_management)
        self.admin_menu.addAction(self.user_management_action)
        
        # Role management action
        self.role_management_action = QAction('&Role Management', self)
        self.role_management_action.setStatusTip('Manage roles and their permissions')
        self.role_management_action.triggered.connect(self.show_role_management)
        self.admin_menu.addAction(self.role_management_action)
        
        # Initially disable admin menu
        self.admin_menu.setEnabled(False)
        
        # Help menu
        help_menu = menubar.addMenu('&Help')
        
        # About action
        about_action = QAction('&About', self)
        about_action.setStatusTip('About this application')
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def update_menus(self):
        """Update menu availability based on user permissions."""
        if self.user_management.get_current_user() and self.user_management.has_permission('user_management'):
            self.admin_menu.setEnabled(True)
        else:
            self.admin_menu.setEnabled(False)

    def handle_login_request(self):
        """Show the login panel in the dashboard."""
        # Switch to main dashboard if not already there
        self.stacked_widget.setCurrentWidget(self.main_dashboard)
        # Update dashboard to show login panel
        self.main_dashboard.update_dashboard()
        # Focus on username field
        if hasattr(self.main_dashboard, 'username_edit'):
            self.main_dashboard.username_edit.setFocus()

    def handle_login_success(self, user):
        """Handle successful login."""
        # Reset the state of all screens first
        for i in range(self.stacked_widget.count()):
            widget = self.stacked_widget.widget(i)
            if widget != self.main_dashboard:
                widget.setVisible(False)
        
        # Make sure the main dashboard is visible and in front
        self.main_dashboard.setVisible(True)
        self.stacked_widget.setCurrentWidget(self.main_dashboard)
        
        # Update the main dashboard to reflect the user's permissions
        self.main_dashboard.update_dashboard()
        
        # Update menus based on user permissions
        self.update_menus()
        
        # Show welcome message
        QMessageBox.information(
            self, 
            "Login Successful", 
            f"Welcome, {user['full_name']}!\n\nYou are logged in as: {user['role_name']}"
        )

    def show_pdf_processor(self):
        """Show the PDF processor screen with proper transition."""
        # Check if user has permission
        if (not self.user_management.get_current_user() or 
            not self.user_management.has_permission("draw_pdf_rules")):
            result = QMessageBox.question(
                self,
                "Permission Required",
                "You need to log in with appropriate permissions to access this feature.\n\nWould you like to log in now?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.Yes:
                # Show login panel in dashboard
                self.handle_login_request()
            return
        
        # Hide all widgets in the stacked widget to prevent overlapping
        for i in range(self.stacked_widget.count()):
            widget = self.stacked_widget.widget(i)
            if widget:
                widget.setVisible(False)
        
        # Make sure the PDF processor is updated for permissions
        if hasattr(self, 'pdf_processor') and self.pdf_processor:
            self.pdf_processor.update_visibility()
            self.pdf_processor.setVisible(True)
            
            # Now set it as the current widget
        self.stacked_widget.setCurrentWidget(self.pdf_processor)

    def show_invoice_config(self):
        self.stacked_widget.setCurrentWidget(self.invoice_config)

    def handle_config_completed(self, config):
        if config['has_multiple_pages']:
            # Create multi-page processor
            self.multi_page_processor = MultiPageProcessor(
                config['sample_multi_page_invoice'],
                has_header_repeat=config['has_header_repeat']
            )
            self.stacked_widget.addWidget(self.multi_page_processor)
            
            # Connect signals
            self.multi_page_processor.go_back.connect(
                lambda: self.stacked_widget.setCurrentWidget(self.invoice_config)
            )
            self.multi_page_processor.config_completed.connect(self.process_multi_page_invoice)
            
            # Show multi-page processor
            self.stacked_widget.setCurrentWidget(self.multi_page_processor)
        else:
            # Handle single page invoice as before
            self.process_invoice(self.pdf_processor.pdf_path)

    def process_multi_page_invoice(self, regions):
        """Process multi-page invoice with configured regions"""
        # Extract data from all pages
        all_data = self.pdf_processor.extract_multi_page_invoice()
        
        # Create and show the section viewer with multi-page support
        self.invoice_viewer = InvoiceSectionViewer(
            self.pdf_processor.pdf_path,
            all_data['header'],
            all_data['items'],
            all_data['summary'],
            regions,
            self.pdf_processor.column_lines,
            is_multi_page=True
        )
        
        self.stacked_widget.addWidget(self.invoice_viewer)
        self.stacked_widget.setCurrentWidget(self.invoice_viewer)

    def process_invoice(self, pdf_path):
        # Extract tables using the provided code
        header_df, item_details_df, summary_df = self.extract_invoice_tables(self.pdf_processor.pdf_path)
        
        # Check if we already have an invoice viewer and reuse it if possible
        if self.invoice_viewer:
            # Remove existing viewer from stacked widget to avoid potential duplicates
            old_index = self.stacked_widget.indexOf(self.invoice_viewer)
            if old_index != -1:
                self.stacked_widget.removeWidget(self.invoice_viewer)
            # Clean up the old viewer
            self.invoice_viewer.deleteLater()
        
        # Create and show the section viewer with regions from PDF processor
        self.invoice_viewer = InvoiceSectionViewer(
            pdf_path, 
            header_df, 
            item_details_df, 
            summary_df,
            self.pdf_processor.regions,  # Pass the regions directly
            self.pdf_processor.column_lines  # Pass the column lines
        )
        
        # Connect the save_template_signal to show the template manager
        print("\n[DEBUG] Connecting save_template_signal in process_invoice")
        # Disconnect any previous connections to avoid duplicate signals
        try:
            self.invoice_viewer.save_template_signal.disconnect()
        except:
            # No existing connection to disconnect
            pass
        # Connect the signal to our handler
        self.invoice_viewer.save_template_signal.connect(self.show_template_manager_from_viewer)
        
        # Add to the stacked widget
        self.stacked_widget.addWidget(self.invoice_viewer)
        self.stacked_widget.setCurrentWidget(self.invoice_viewer)

    def extract_invoice_tables(self, pdf_path):
        """Extract tables from the PDF file using the defined regions"""
        header_df = None
        item_details_df = None
        summary_df = None
        
        try:
            if not os.path.exists(pdf_path):
                print(f"PDF file not found: {pdf_path}")
                return header_df, item_details_df, summary_df
            
            print(f"\n{'='*80}")
            print(f"STARTING TABLE EXTRACTION FROM: {pdf_path}")
            print(f"{'='*80}")
            
            # Print regions information at the start
            if hasattr(self.pdf_processor, 'regions'):
                print("\nRegions in original drawing order:")
                for region_type, rects in self.pdf_processor.regions.items():
                    print(f"\n{region_type.upper()} REGIONS ({len(rects)}):")
                    for i, rect in enumerate(rects):
                        print(f"  {region_type} {i}: top={rect.top()}, left={rect.left()}, width={rect.width()}, height={rect.height()}")
            
            # Print column lines information at the start
            if hasattr(self.pdf_processor, 'column_lines'):
                print("\nColumn lines by region:")
                for region_type, lines in self.pdf_processor.column_lines.items():
                    print(f"\n{region_type.upper()} COLUMN LINES ({len(lines)}):")
                    # Group by rect_index
                    lines_by_rect = {}
                    for line in lines:
                        if len(line) == 3:  # New format with rect_index
                            rect_idx = line[2]
                            if rect_idx not in lines_by_rect:
                                lines_by_rect[rect_idx] = []
                            lines_by_rect[rect_idx].append(line[0].x())
                    
                    # Print organized by rect_index
                    for rect_idx, x_positions in sorted(lines_by_rect.items()):
                        print(f"  Table {rect_idx} column x positions: {sorted(x_positions)}")
            
            # Print table_areas information at the start
            if hasattr(self.pdf_processor, 'table_areas'):
                print("\ntable_areas details:")
                for label, info in self.pdf_processor.table_areas.items():
                    rect = info['rect']
                    print(f"  {label}: type={info['type']}, index={info['index']}, " +
                          f"position=[{rect.top()},{rect.left()},{rect.width()},{rect.height()}], " +
                          f"columns={info.get('columns', [])}")
            
            # Get PDF dimensions for scaling
            import fitz
            pdf_document = fitz.open(pdf_path)
            page = pdf_document[0]
            page_width = page.rect.width
            page_height = page.rect.height
            pdf_document.close()
            
            # Calculate scale factors (pdf_processor uses a scaled pixmap)
            pix_scale = 2  # The pixmap scaling used in display_current_page
            print(f"\nScaling Information:")
            print(f"  PDF Size: {page_width} x {page_height}")
            print(f"  Pixmap Scale Factor: {pix_scale}")
            scale_x = page_width / (self.pdf_processor.pdf_label.pixmap().width() / pix_scale)
            scale_y = page_height / (self.pdf_processor.pdf_label.pixmap().height() / pix_scale)
            print(f"  Scale X: {scale_x:.4f}, Scale Y: {scale_y:.4f}")
            
            import pypdf_table_extraction
            header_dfs = []
            
            # Check if we have table_areas for more structured processing
            if hasattr(self.pdf_processor, 'table_areas') and self.pdf_processor.table_areas:
                print("\nUsing structured table_areas for extraction")
                
                # Debug output of all table_areas for reference
                print("\nAll table_areas entries:")
                for label, info in self.pdf_processor.table_areas.items():
                    print(f"  {label}: type={info['type']}, index={info['index']}, columns={len(info.get('columns', []))} columns")
                
                # Extract header tables using table_areas
                # Instead of sorting by index, maintain the original order they were drawn
                header_tables = []
                # First create list of all header tables
                all_header_tables = [(label, info) for label, info in self.pdf_processor.table_areas.items() 
                                    if info['type'] == 'header']
                
                # Now organize them by index to preserve drawing order
                max_index = max([info['index'] for _, info in all_header_tables]) if all_header_tables else -1
                for i in range(max_index + 1):
                    for label, info in all_header_tables:
                        if info['index'] == i:
                            header_tables.append((label, info))
                            break
                
                print(f"\nProcessing {len(header_tables)} header tables in original drawing order:")
                for table_index, (label, table_info) in enumerate(header_tables):
                    print(f"\nProcessing header table {table_index} ({label}) with index {table_info['index']}:")
                    rect = table_info['rect']
                    
                    # Raw rectangle coordinates
                    print(f"  Raw rectangle: x={rect.x()}, y={rect.y()}, width={rect.width()}, height={rect.height()}")
                    
                    # Convert rectangle to table area format
                    x1 = rect.x() * scale_x
                    y1 = page_height - (rect.y() * scale_y)
                    x2 = (rect.x() + rect.width()) * scale_x
                    y2 = page_height - ((rect.y() + rect.height()) * scale_y)
                    table_area = f"{x1},{y1},{x2},{y2}"
                    print(f"  Scaled table area: {table_area}")
                    
                    # Get column lines for this table
                    columns = table_info.get('columns', [])
                    region_columns = None
                    
                    if columns:
                        print(f"  Raw column x-coordinates: {columns}")
                        # Scale column lines by scale_x (they are raw coordinates)
                        scaled_columns = [x * scale_x for x in columns]
                        print(f"  Scaled column x-coordinates: {scaled_columns}")
                        region_columns = ','.join([str(x) for x in sorted(scaled_columns)])
                        print(f"  Formatted column coordinates: {region_columns}")
                    else:
                        print("  No column lines defined for this table")
                    
                    # Extract this header table
                    try:
                        print(f"  Extracting table with area {table_area} and columns: {region_columns}")
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
                            print(f"  Successfully extracted table data with {len(tables[0].df)} rows and {len(tables[0].df.columns)} columns")
                            header_dfs.append(tables[0].df)
                        else:
                            print(f"  No data found in table")
                    except Exception as e:
                        print(f"  Error extracting table: {str(e)}")
                
                # Keep header_df as a list of DataFrames to preserve the order
                if header_dfs:
                    header_df = header_dfs[0] if len(header_dfs) == 1 else header_dfs
                    print(f"\nSuccessfully processed {len(header_dfs)} header tables in original drawing order")
                else:
                    print("\nNo valid header tables found")
                
                # Process items table
                # Preserve original drawing order for items tables too
                items_tables = []
                all_items_tables = [(label, info) for label, info in self.pdf_processor.table_areas.items() 
                                  if info['type'] == 'items']
                
                # Organize by index to preserve original order
                if all_items_tables:
                    max_index = max([info['index'] for _, info in all_items_tables])
                    for i in range(max_index + 1):
                        for label, info in all_items_tables:
                            if info['index'] == i:
                                items_tables.append((label, info))
                                break
                
                if items_tables:
                    print("\nProcessing items table:")
                    label, table_info = items_tables[0]  # Usually just one items table
                    rect = table_info['rect']
                    
                    # Raw rectangle coordinates
                    print(f"  Raw rectangle: x={rect.x()}, y={rect.y()}, width={rect.width()}, height={rect.height()}")
                    
                    # Convert rectangle to table area format
                    x1 = rect.x() * scale_x
                    y1 = page_height - (rect.y() * scale_y)
                    x2 = (rect.x() + rect.width()) * scale_x
                    y2 = page_height - ((rect.y() + rect.height()) * scale_y)
                    table_area = f"{x1},{y1},{x2},{y2}"
                    print(f"  Scaled table area: {table_area}")
                    
                    # Get column lines for this table
                    columns = table_info.get('columns', [])
                    region_columns = None
                    
                    if columns:
                        print(f"  Raw column x-coordinates: {columns}")
                        # Scale column lines by scale_x (they are raw coordinates)
                        scaled_columns = [x * scale_x for x in columns]
                        print(f"  Scaled column x-coordinates: {scaled_columns}")
                        region_columns = ','.join([str(x) for x in sorted(scaled_columns)])
                        print(f"  Formatted column coordinates: {region_columns}")
                    else:
                        print("  No column lines defined for this table")
                    
                    # Extract this items table
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
                    except Exception as e:
                        print(f"  Error extracting items table: {str(e)}")
                
                # Process summary table
                # Preserve original drawing order for summary tables too
                summary_tables = []
                all_summary_tables = [(label, info) for label, info in self.pdf_processor.table_areas.items() 
                                    if info['type'] == 'summary']
                
                # Organize by index to preserve original order
                if all_summary_tables:
                    max_index = max([info['index'] for _, info in all_summary_tables])
                    for i in range(max_index + 1):
                        for label, info in all_summary_tables:
                            if info['index'] == i:
                                summary_tables.append((label, info))
                                break
                
                if summary_tables:
                    print("\nProcessing summary table:")
                    label, table_info = summary_tables[0]  # Usually just one summary table
                    rect = table_info['rect']
                    
                    # Raw rectangle coordinates
                    print(f"  Raw rectangle: x={rect.x()}, y={rect.y()}, width={rect.width()}, height={rect.height()}")
                    
                    # Convert rectangle to table area format
                    x1 = rect.x() * scale_x
                    y1 = page_height - (rect.y() * scale_y)
                    x2 = (rect.x() + rect.width()) * scale_x
                    y2 = page_height - ((rect.y() + rect.height()) * scale_y)
                    table_area = f"{x1},{y1},{x2},{y2}"
                    print(f"  Scaled table area: {table_area}")
                    
                    # Get column lines for this table
                    columns = table_info.get('columns', [])
                    region_columns = None
                    
                    if columns:
                        print(f"  Raw column x-coordinates: {columns}")
                        # Scale column lines by scale_x (they are raw coordinates)
                        scaled_columns = [x * scale_x for x in columns]
                        print(f"  Scaled column x-coordinates: {scaled_columns}")
                        region_columns = ','.join([str(x) for x in sorted(scaled_columns)])
                        print(f"  Formatted column coordinates: {region_columns}")
                    else:
                        print("  No column lines defined for this table")
                    
                    # Extract this summary table
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
                    except Exception as e:
                        print(f"  Error extracting summary table: {str(e)}")
            
            # Handle traditional regions format
            else:
                # Extract headers
                header_dfs = []
                if 'header' in regions:
                    header_regions = regions['header']
                    for i, rect_data in enumerate(header_regions):
                        # Convert region to table area format
                        rect = QRect(rect_data['x'], rect_data['y'], rect_data['width'], rect_data['height'])
                        x1 = rect.x() * scale_x
                        y1 = page_height - (rect.y() * scale_y)
                        x2 = (rect.x() + rect.width()) * scale_x
                        y2 = page_height - ((rect.y() + rect.height()) * scale_y)
                        table_area = f"{x1},{y1},{x2},{y2}"
                        
                        # Find column lines for this region
                        region_columns = None
                        if 'header' in column_lines:
                            column_x_coords = []
                            for line in column_lines['header']:
                                if len(line) == 3 and line[2] == i:
                                    # Extract the x-coordinate and scale it
                                    column_x_coords.append(line[0]['x'] * scale_x)
                            
                            if column_x_coords:
                                region_columns = ','.join([str(x) for x in sorted(column_x_coords)])
                        
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
                        except Exception as e:
                            print(f"  Error extracting header table: {str(e)}")
                
                # Keep header_df as a list of DataFrames to preserve the order
                if header_dfs:
                    header_df = header_dfs[0] if len(header_dfs) == 1 else header_dfs
                    print(f"Successfully processed {len(header_dfs)} header tables")

                # Extract items
                items_region = regions.get('items', [])
                if items_region and len(items_region) > 0:
                    # Process each items region (typically just one)
                    for idx, region in enumerate(items_region):
                        print(f"\nProcessing Items Table {idx}:")
                        
                        # Raw rectangle coordinates
                        print(f"  Raw rectangle: x={region.x()}, y={region.y()}, width={region.width()}, height={region.height()}")
                        
                        # Convert region to table area format
                        x1 = region.x() * scale_x
                        y1 = page_height - (region.y() * scale_y)
                        x2 = (region.x() + region.width()) * scale_x
                        y2 = page_height - ((region.y() + region.height()) * scale_y)
                        table_area = f"{x1},{y1},{x2},{y2}"
                        print(f"  Scaled table area: {table_area}")
                        
                        # Find column lines specifically for this region
                        region_columns = None
                        if 'items' in column_lines:
                            # Get column lines for this specific region index only
                            column_x_coords = []
                            for line in column_lines['items']:
                                # Only include lines explicitly associated with this table (rect_index)
                                if len(line) == 3 and line[2] == idx:
                                    # Store the x-coordinate, scaling appropriately
                                    raw_x = line[0].x()
                                    scaled_x = raw_x * scale_x
                                    column_x_coords.append(scaled_x)
                                    print(f"    Found column line at x={raw_x} (scaled to {scaled_x}) with rect_index={line[2]}")
                                # Handle old format lines without rect_index (for backward compatibility)
                                elif len(line) == 2 and idx == 0:
                                    # Store the x-coordinate, scaling appropriately
                                    raw_x = line[0].x()
                                    scaled_x = raw_x * scale_x
                                    column_x_coords.append(scaled_x)
                                    print(f"    Found column line at x={raw_x} (scaled to {scaled_x}) (legacy format)")
                            
                            if column_x_coords:
                                # Sort column lines by x-coordinate and format as a comma-separated string
                                print(f"    Raw scaled column x-coordinates: {column_x_coords}")
                                region_columns = ','.join([str(x) for x in sorted(column_x_coords)])
                                print(f"    Formatted column coordinates: {region_columns}")
                            else:
                                print("    No column lines found for this table")
                        
                        # Extract this items table
                        try:
                            print(f"  Extracting items table at area {table_area} with columns: {region_columns}")
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
                                print(f"  Successfully extracted items table with {len(item_details_df)} rows and {len(item_details_df.columns)} columns")
                            else:
                                print(f"  No data found in items table")
                        except Exception as e:
                            print(f"  Error extracting items table: {str(e)}")

                # Extract summary
                summary_region = regions.get('summary', [])
                if summary_region and len(summary_region) > 0:
                    # Process each summary region (typically just one)
                    for idx, region in enumerate(summary_region):
                        print(f"\nProcessing Summary Table {idx}:")
                        
                        # Raw rectangle coordinates
                        print(f"  Raw rectangle: x={region.x()}, y={region.y()}, width={region.width()}, height={region.height()}")
                        
                        # Convert region to table area format
                        x1 = region.x() * scale_x
                        y1 = page_height - (region.y() * scale_y)
                        x2 = (region.x() + region.width()) * scale_x
                        y2 = page_height - ((region.y() + region.height()) * scale_y)
                        table_area = f"{x1},{y1},{x2},{y2}"
                        print(f"  Scaled table area: {table_area}")
                        
                        # Find column lines specifically for this region
                        region_columns = None
                        if 'summary' in column_lines:
                            # Get column lines for this specific region index only
                            column_x_coords = []
                            for line in column_lines['summary']:
                                # Only include lines explicitly associated with this table (rect_index)
                                if len(line) == 3 and line[2] == idx:
                                    # Store the x-coordinate, scaling appropriately
                                    raw_x = line[0].x()
                                    scaled_x = raw_x * scale_x
                                    column_x_coords.append(scaled_x)
                                    print(f"    Found column line at x={raw_x} (scaled to {scaled_x}) with rect_index={line[2]}")
                                # Handle old format lines without rect_index (for backward compatibility)
                                elif len(line) == 2 and idx == 0:
                                    # Store the x-coordinate, scaling appropriately
                                    raw_x = line[0].x()
                                    scaled_x = raw_x * scale_x
                                    column_x_coords.append(scaled_x)
                                    print(f"    Found column line at x={raw_x} (scaled to {scaled_x}) (legacy format)")
                            
                            if column_x_coords:
                                # Sort column lines by x-coordinate and format as a comma-separated string
                                print(f"    Raw scaled column x-coordinates: {column_x_coords}")
                                region_columns = ','.join([str(x) for x in sorted(column_x_coords)])
                                print(f"    Formatted column coordinates: {region_columns}")
                            else:
                                print("    No column lines found for this table")
                        
                        # Extract this summary table
                        try:
                            print(f"  Extracting summary table at area {table_area} with columns: {region_columns}")
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
                                print(f"  Successfully extracted summary table with {len(summary_df)} rows and {len(summary_df.columns)} columns")
                            else:
                                print(f"  No data found in summary table")
                        except Exception as e:
                            print(f"  Error extracting summary table: {str(e)}")
            
            return header_df, item_details_df, summary_df
            
        except Exception as e:
            print(f"Error extracting tables: {str(e)}")
            import traceback
            traceback.print_exc()
            return header_df, item_details_df, summary_df

    def upload_invoice(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Invoice PDF",
            "",
            "PDF Files (*.pdf)"
        )
        
        if file_path:
            # Create PDF processor screen if it doesn't exist
            if not self.pdf_processor:
                self.pdf_processor = PDFProcessor()
                self.stacked_widget.addWidget(self.pdf_processor)
            
            # Load the PDF
            self.pdf_processor.load_pdf(file_path)
            
            # Show the PDF processor screen
            self.stacked_widget.setCurrentWidget(self.pdf_processor)

    def show_template_manager(self):
        # Only allow if user has permission
        if (not self.user_management.get_current_user() or 
            not self.user_management.has_permission("template_management")):
            QMessageBox.warning(
                self,
                "Permission Denied",
                "You do not have permission to access template management.\n\n"
                "Please log in with a developer account to access this feature."
            )
            return
            
        self.stacked_widget.setCurrentWidget(self.template_manager)

    def show_bulk_processor(self):
        """Show the bulk processor screen."""
        # Check if user has permission
        if (not self.user_management.get_current_user() or 
            not self.user_management.has_permission("bulk_extraction")):
            QMessageBox.warning(
                self,
                "Permission Denied",
                "You do not have permission to access bulk extraction.\n\n"
                "Please log in with an appropriate account to access this feature."
            )
            return
        
        # Hide all widgets in the stacked widget to prevent overlapping
        for i in range(self.stacked_widget.count()):
            widget = self.stacked_widget.widget(i)
            if widget:
                widget.setVisible(False)
            
        # Initialize bulk processor if it doesn't exist
        if not hasattr(self, 'bulk_processor'):
            self.bulk_processor = BulkProcessor()
            # Connect the go_back signal (not directly to a method)
            self.bulk_processor.go_back.connect(self.handle_bulk_processor_go_back)
            self.stacked_widget.addWidget(self.bulk_processor)
        
        # Show the bulk processor
        self.bulk_processor.setVisible(True)
        self.stacked_widget.setCurrentWidget(self.bulk_processor)
    
    def handle_bulk_processor_go_back(self):
        """Handle the go_back signal from the bulk processor."""
        # Hide all widgets first
        for i in range(self.stacked_widget.count()):
            widget = self.stacked_widget.widget(i)
            if widget:
                widget.setVisible(False)
                
        # Show dashboard and make it current
        self.main_dashboard.setVisible(True)
        self.stacked_widget.setCurrentWidget(self.main_dashboard)

    def apply_template(self, template):
        """Apply the selected template to the current PDF processor"""
        try:
            # Apply the template settings to the PDF processor
            if hasattr(self.pdf_processor, 'regions'):
                self.pdf_processor.regions = template['regions']
            if hasattr(self.pdf_processor, 'column_lines'):
                self.pdf_processor.column_lines = template['column_lines']
            if hasattr(self.pdf_processor, 'multi_table_mode'):
                self.pdf_processor.multi_table_mode = template.get('config', {}).get('multi_table_mode', False)
            
            # Show success message
            success_msg = QMessageBox(self)
            success_msg.setWindowTitle("Template Applied")
            success_msg.setText("Template Applied Successfully")
            success_msg.setInformativeText(f"The template '{template['name']}' has been applied to the PDF processor.")
            success_msg.setIcon(QMessageBox.Information)
            success_msg.setStyleSheet("QLabel { color: black; }")
            success_msg.exec()
            
            # Switch back to the PDF processor screen
            self.stacked_widget.setCurrentWidget(self.pdf_processor)
            
        except Exception as e:
            error_dialog = QMessageBox(self)
            error_dialog.setWindowTitle("Error")
            error_dialog.setText("Error Applying Template")
            error_dialog.setInformativeText(f"An error occurred: {str(e)}")
            error_dialog.setIcon(QMessageBox.Critical)
            error_dialog.setStyleSheet("QLabel { color: black; }")
            error_dialog.exec()

    def next_step(self):
        """Process to the next step based on the current widget"""
        current_widget = self.stacked_widget.currentWidget()
        
        if current_widget == self.pdf_processor:
            # Process from PDF processor to invoice config
            self.show_invoice_config()
        elif current_widget == self.invoice_config:
            # Process from invoice config to results
            config = self.invoice_config.get_config()
            self.handle_config_completed(config)
        
        # Use the existing process_invoice method to handle invoice viewing
        # This ensures we don't have duplicate code for creating the viewer
        self.process_invoice(self.pdf_processor.pdf_path)

    def show_template_manager_from_viewer(self):
        """Show the template manager from the invoice viewer, preserving all data for template creation"""
        print("\n[DEBUG] show_template_manager_from_viewer called")
        
        # Check if we have a valid template manager
        if not hasattr(self, 'template_manager') or self.template_manager is None:
            print("[ERROR] Template manager is not available")
            QMessageBox.critical(
                self,
                "Error",
                "Template manager is not available. Please try again."
            )
            return
        
        # Make sure the current invoice configuration is retained
        # This ensures that when we save a template, we're saving the current state
        try:
            self.template_manager.refresh()
            
            # Switch to the template manager
            self.stacked_widget.setCurrentWidget(self.template_manager)
            
            # Show a hint to the user about template saving
            QMessageBox.information(
                self,
                "Save Template",
                "You can now save the current invoice configuration as a template.\n\n"
                "Templates save all table regions, column lines, and extraction settings "
                "for reuse with similar invoices."
            )
        except Exception as e:
            print(f"[ERROR] Failed to switch to template manager: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to switch to template manager: {str(e)}"
            )

    def show_user_management(self):
        """Show the user management dialog."""
        # Check if user has permission
        if (not self.user_management.get_current_user() or 
            not self.user_management.has_permission("user_management")):
            QMessageBox.warning(
                self,
                "Permission Denied",
                "You do not have permission to access user management.\n\n"
                "Please log in with an administrator account to access this feature."
            )
            return
            
        dialog = UserManagementDialog(self.user_management, self)
        dialog.exec()
    
    def show_role_management(self):
        """Show the role management dialog."""
        # Check if user has permission
        if (not self.user_management.get_current_user() or 
            not self.user_management.has_permission("user_management")):
            QMessageBox.warning(
                self,
                "Permission Denied",
                "You do not have permission to access role management.\n\n"
                "Please log in with an administrator account to access this feature."
            )
            return
            
        dialog = RoleManagementDialog(self.user_management, self)
        dialog.exec()
    
    def show_about_dialog(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About PDF Harvest",
            "PDF Harvest\n\n"
            "Version 1.0.0\n\n"
            "A PDF invoice data extraction tool with visual selection and mapping capabilities.\n\n"
            "© 2023 PDF Harvest Team"
            )

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = PDFHarvest()
    window.show()
    sys.exit(app.exec()) 
    