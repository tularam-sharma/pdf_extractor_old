from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QScrollArea, QFrame, QStackedWidget, QMessageBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
                             QComboBox, QLineEdit, QCheckBox, QDialog, QFormLayout,
                             QSpinBox, QDoubleSpinBox, QTextEdit, QGroupBox, QFileDialog,
                             QDialogButtonBox, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QSize
from PySide6.QtGui import (QFont, QImage, QPixmap, QCursor, QPainter, 
                          QPen, QColor)
import pandas as pd
import fitz
import pypdf_table_extraction
import json
import os
import re
import sqlite3
from database import InvoiceDatabase  # Import the InvoiceDatabase class

# Create a global database instance with the correct database path
db = InvoiceDatabase("invoice_templates.db")  # Initialize with the correct database path

class PDFLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent  # Store parent widget reference
        self.setMouseTracking(True)
        self.scaled_pixmap = None
        self.scale_factor = 1.0
        self.offset = QPoint(0, 0)
        self._pixmap = None  # Store the original pixmap

    def setPixmap(self, pixmap):
        if not self.isValid():  # Check if widget is still valid
            return
        self._pixmap = pixmap
        super().setPixmap(pixmap)
        self.adjustPixmap()

    def isValid(self):
        """Check if the widget is still valid and not deleted"""
        try:
            return not self.isHidden()
        except RuntimeError:
            return False

    def resizeEvent(self, event):
        if not self.isValid():
            return
        super().resizeEvent(event)
        self.adjustPixmap()

    def adjustPixmap(self):
        if not self.isValid() or not self._pixmap:
            return
            
        # Calculate scaling to fit the label while maintaining aspect ratio
        label_size = self.size()
        pixmap_size = self._pixmap.size()
        
        width_ratio = label_size.width() / pixmap_size.width()
        height_ratio = label_size.height() / pixmap_size.height()
        self.scale_factor = min(width_ratio, height_ratio)
        
        # Calculate the scaled size
        scaled_width = int(pixmap_size.width() * self.scale_factor)
        scaled_height = int(pixmap_size.height() * self.scale_factor)
        
        # Calculate offset to center the image
        self.offset = QPoint(
            (label_size.width() - scaled_width) // 2,
            (label_size.height() - scaled_height) // 2
        )
        
        # Store the scaled pixmap
        self.scaled_pixmap = self._pixmap.scaled(
            scaled_width,
            scaled_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.update()

    def mapToPixmap(self, pos):
        if not self.scaled_pixmap:
            return pos
            
        # Remove the offset to get coordinates relative to the scaled image
        pos = pos - self.offset
        
        # Convert the coordinates back to original pixmap space
        if self.scale_factor != 0:
            x = pos.x() / self.scale_factor
            y = pos.y() / self.scale_factor
            return QPoint(int(x), int(y))
        return pos

    def mapFromPixmap(self, pos):
        if not self.scaled_pixmap:
            return pos
            
        # Scale the coordinates
        x = pos.x() * self.scale_factor
        y = pos.y() * self.scale_factor
        
        # Add the offset
        return QPoint(int(x), int(y)) + self.offset

    def paintEvent(self, event):
        if not self.isValid() or not self.scaled_pixmap:
            super().paintEvent(event)
            return
            
        painter = QPainter(self)
        painter.drawPixmap(self.offset, self.scaled_pixmap)
        
        # Draw regions and column lines
        if self.parent_widget and hasattr(self.parent_widget, 'isValid') and self.parent_widget.isValid():
            # Get current page index (0-based)
            current_page_index = self.parent_widget.current_page - 1
            
            # Handle both single-page and multi-page formats
            regions = self.parent_widget.regions
            column_lines = self.parent_widget.column_lines
            
            # If regions is a dict with page indices, get current page's regions
            if isinstance(regions, dict) and current_page_index in regions:
                regions = regions[current_page_index]
            
            # If column_lines is a dict with page indices, get current page's column lines
            if isinstance(column_lines, dict) and current_page_index in column_lines:
                column_lines = column_lines[current_page_index]
            
            # Draw regions
            for region_type, rects in regions.items():
                if rects is None:  # Skip if region type is not applicable
                    continue
                    
                color = self.parent_widget.get_region_color(region_type)
                pen = QPen(color, 2, Qt.SolidLine)
                painter.setPen(pen)
                
                for i, rect in enumerate(rects):
                    scaled_rect = QRect(
                        self.mapFromPixmap(rect.topLeft()),
                        self.mapFromPixmap(rect.bottomRight())
                    )
                    painter.drawRect(scaled_rect)
                    
                    # Draw column lines for this region
                    if region_type in column_lines:
                        for line in column_lines[region_type]:
                            if len(line) == 3 and line[2] == i:  # Check if line belongs to this region
                                start = self.mapFromPixmap(line[0])
                                end = self.mapFromPixmap(line[1])
                                painter.drawLine(start, end)
        
        painter.end()  # Properly end the painter

class MultiPageSectionViewer(QWidget):
    # Add a new signal to notify when save template button is clicked
    save_template_signal = Signal()  # Signal to trigger template saving

    def __init__(self, pdf_path, all_pages_data, regions, column_lines):
        super().__init__()
        print("\nInitializing MultiPageSectionViewer...")
        print(f"PDF Path: {pdf_path}")
        print(f"Number of pages: {len(all_pages_data)}")
        
        self.pdf_path = pdf_path
        self.all_pages_data = all_pages_data  # List of dictionaries containing data for each page
        self.regions = regions
        self.column_lines = column_lines
        
        # Initialize PDF document first
        self.pdf_document = fitz.open(pdf_path)
        print(f"PDF document opened successfully with {len(self.pdf_document)} pages")
        
        # Initialize page numbers after PDF document is loaded
        self.total_pages = len(self.pdf_document)  # Use actual PDF document length
        self.current_page = 1
        self.current_section = 'header'  # Initialize current section to header
        
        # Initialize extraction parameters
        self.extraction_params = {
            'header': {'row_tol': 5},    # Default for header
            'items': {'row_tol': 15},    # Default for items
            'summary': {'row_tol': 10},  # Default for summary
            'split_text': True,
            'strip_text': '\n',
            'flavor': 'stream'
            
        }
        
        print("\nExtraction parameters initialized:")
        print(json.dumps(self.extraction_params, indent=2))
        
        self.initUI()
        self.load_pdf()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Title
        title = QLabel("Multi-Page Invoice Section Analysis")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #333333; margin: 20px 0;")
        layout.addWidget(title)
        
        # Create main content area
        content = QWidget()
        content_layout = QHBoxLayout(content)  # Changed to horizontal layout
        
        # Left side - PDF display
        pdf_container = QWidget()
        pdf_layout = QVBoxLayout(pdf_container)
        
        # Add page navigation
        page_nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("← Previous Page")
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn = QPushButton("Next Page →")
        self.next_btn.clicked.connect(self.next_page)
        self.page_label = QLabel(f"Page {self.current_page} of {self.total_pages}")
        
        page_nav_layout.addWidget(self.prev_btn)
        page_nav_layout.addWidget(self.page_label)
        page_nav_layout.addWidget(self.next_btn)
        pdf_layout.addLayout(page_nav_layout)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        self.pdf_label = PDFLabel(self)
        self.pdf_label.setAlignment(Qt.AlignCenter)
        self.pdf_label.setStyleSheet("QLabel { background-color: #f0f0f0; }")
        
        self.scroll_area.setWidget(self.pdf_label)
        pdf_layout.addWidget(self.scroll_area)
        
        # Right side - Data tables
        data_container = QWidget()
        data_layout = QVBoxLayout(data_container)
        
        # Add section navigation
        section_nav_layout = QHBoxLayout()
        self.section_label = QLabel(f"Section: {self.current_section.title()}")
        section_nav_layout.addWidget(self.section_label)
        data_layout.addLayout(section_nav_layout)
        
        section_title_container = QWidget()
        section_title_layout = QHBoxLayout(section_title_container)
        section_title_layout.setContentsMargins(0, 0, 0, 0)
        
        # Section title
        self.section_title = QLabel("Extracted Data")
        self.section_title.setFont(QFont("Arial", 16, QFont.Bold))
        self.section_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.section_title.setStyleSheet("color: white;")
        section_title_layout.addWidget(self.section_title)
        
        # Add stretch to push the download button to the far right
        section_title_layout.addStretch()
        
        # Download JSON button
        self.download_json_btn = QPushButton("Download JSON")
        self.download_json_btn.clicked.connect(self.download_json)
        self.download_json_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        section_title_layout.addWidget(self.download_json_btn)
        
        # Add section title container to data layout
        data_layout.addWidget(section_title_container)
        
        # Create and initialize the data table
        self.data_table = QTableWidget()
        self.data_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                color: black;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #ddd;
                font-weight: bold;
                color: black;
            }
            QTableWidget::item {
                color: black;
            }
        """)
        
        # Add the data table to the layout
        data_layout.addWidget(self.data_table)
        
        # Add both containers to the main layout
        content_layout.addWidget(pdf_container)
        content_layout.addWidget(data_container)
        
        layout.addWidget(content)

        # Navigation buttons at the bottom
        nav_layout = QHBoxLayout()
        
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

        # Create navigation buttons
        prev_section_btn = QPushButton("Previous Section")
        prev_section_btn.clicked.connect(self.prev_section)
        prev_section_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3159C1;
            }
        """)

        next_section_btn = QPushButton("Next Section")
        next_section_btn.clicked.connect(self.next_section)
        next_section_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3159C1;
            }
        """)
        
        # Create a "Retry with Custom Settings" button
        self.retry_btn = QPushButton("Retry With Custom Settings")
        self.retry_btn.clicked.connect(self.show_custom_settings)
        self.retry_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        self.retry_btn.setToolTip("Adjust extraction parameters for table content")
        
        # Create a new "Save Template" button
        save_template_btn = QPushButton("Save Template")
        save_template_btn.clicked.connect(self.save_template)
        save_template_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        
        # Add back button to the left
        nav_layout.addWidget(back_btn)
        
        # Add a stretch to push everything to the center
        nav_layout.addStretch()
        
        # Create a center container for section navigation
        center_nav = QHBoxLayout()
        center_nav.addWidget(prev_section_btn)
        center_nav.addWidget(next_section_btn)
        
        # Add the retry button
        center_nav.addWidget(self.retry_btn)
        
        # Add the center navigation to the main nav layout
        nav_layout.addLayout(center_nav)
        
        # Add another stretch
        nav_layout.addStretch()
        
        # Add the save template button to the right
        nav_layout.addWidget(save_template_btn)
        
        layout.addLayout(nav_layout)
        
        self.setLayout(layout)

    def load_pdf(self):
        print(f"\nLoading PDF for page {self.current_page}")
        try:
            # Basic validation checks
            if not hasattr(self, 'pdf_document') or self.pdf_document is None:
                print("PDF document not initialized")
                return
                
            if not hasattr(self, 'current_page') or self.current_page < 1 or self.current_page > self.total_pages:
                print(f"Invalid page number: {self.current_page} (valid range: 1-{self.total_pages})")
                return
                
            if not hasattr(self, 'pdf_path') or not self.pdf_path:
                print("PDF path not set")
                return
            
            # Get the page
            page = self.pdf_document[self.current_page - 1]
            print(f"Successfully loaded page {self.current_page}")
            
            # Create a new pixmap for the page
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            print(f"Page rendered with dimensions: {pix.width}x{pix.height}")
            
            # Convert PyMuPDF pixmap to QPixmap
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
            
            if hasattr(self, 'pdf_label') and self.pdf_label.isValid():
                # Create a new pixmap for drawing
                drawing_pixmap = QPixmap(pixmap.size())
                drawing_pixmap.fill(Qt.transparent)
                
                # Create a painter for the drawing pixmap
                painter = QPainter()
                painter.begin(drawing_pixmap)
                
                try:
                    # Draw the original PDF pixmap first
                    painter.drawPixmap(0, 0, pixmap)
                    
                    # Get current page's regions and column lines
                    current_regions = self.regions
                    current_column_lines = self.column_lines
                    
                    if isinstance(self.regions, dict) and (self.current_page - 1) in self.regions:
                        current_regions = self.regions[self.current_page - 1]
                    if isinstance(self.column_lines, dict) and (self.current_page - 1) in self.column_lines:
                        current_column_lines = self.column_lines[self.current_page - 1]
                    
                    # Draw regions
                    for region_type, rects in current_regions.items():
                        if rects is None:  # Skip if region type is not applicable
                            continue
                            
                        color = self.get_region_color(region_type)
                        pen = QPen(color, 2, Qt.SolidLine)
                        painter.setPen(pen)
                        
                        for i, rect in enumerate(rects):
                            # Ensure rect is a QRect object
                            if isinstance(rect, str):
                                # Parse string coordinates into QRect
                                coords = [float(x) for x in rect.split(',')]
                                rect = QRect(int(coords[0]), int(coords[1]), 
                                           int(coords[2] - coords[0]), int(coords[3] - coords[1]))
                            
                            # Draw the region rectangle
                            painter.drawRect(rect)
                            
                            # Draw column lines for this region
                            if region_type in current_column_lines:
                                for line in current_column_lines[region_type]:
                                    if len(line) == 3 and line[2] == i:  # Check if line belongs to this region
                                        start = line[0]
                                        end = line[1]
                                        painter.drawLine(start, end)
                finally:
                    # Ensure painter is properly ended
                    painter.end()
                
                # Set the combined pixmap to the label
                self.pdf_label.setPixmap(drawing_pixmap)
                self.pdf_label.adjustPixmap()
                print("PDF label updated with new pixmap and drawings")
            
            # Update page label
            if hasattr(self, 'page_label'):
                self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
            
            # Update navigation buttons
            if hasattr(self, 'prev_btn'):
                self.prev_btn.setEnabled(self.current_page > 1)
            if hasattr(self, 'next_btn'):
                self.next_btn.setEnabled(self.current_page < self.total_pages)
            
            # Extract and update data for the current page
            print("\nExtracting data for current page...")
            self.extract_and_update_section_data()
            
            # Update tables with extracted data
            self.update_tables()
            print("Tables updated with extracted data")
            
        except Exception as e:
            print(f"Error loading PDF: {str(e)}")
            import traceback
            traceback.print_exc()

    def extract_and_update_section_data(self):
        """Extract and update data for all sections of the current page"""
        print("\n=== Starting Section Data Extraction ===")
        print(f"Current page: {self.current_page}")
        
        try:
            # Get current page
            page = self.pdf_document[self.current_page - 1]
            print(f"\nProcessing page {self.current_page}")
            
            # Get actual page dimensions in points (1/72 inch)
            page_width = page.mediabox.width
            page_height = page.mediabox.height
            
            # Get the rendered dimensions
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            rendered_width = pix.width
            rendered_height = pix.height
            
            # Calculate scaling factors
            scale_x = page_width / rendered_width
            scale_y = page_height / rendered_height
            
            # Get current page's regions and column lines
            current_regions = self.regions
            current_column_lines = self.column_lines
            
            if isinstance(self.regions, dict) and (self.current_page - 1) in self.regions:
                current_regions = self.regions[self.current_page - 1]
            if isinstance(self.column_lines, dict) and (self.current_page - 1) in self.column_lines:
                current_column_lines = self.column_lines[self.current_page - 1]
            
            # Process each section
            for section in ['header', 'items', 'summary']:
                print(f"\n=== Processing {section.upper()} Section ===")
                if section in current_regions and current_regions[section]:
                    section_regions = current_regions[section]
                    section_column_lines = current_column_lines.get(section, [])
                    
                    processed_tables = []
                    for i, region in enumerate(section_regions):
                        # Convert region coordinates
                        x1 = region.x() * scale_x
                        y1 = page_height - (region.y() * scale_y)  # Flip Y coordinate
                        x2 = (region.x() + region.width()) * scale_x
                        y2 = page_height - ((region.y() + region.height()) * scale_y)  # Flip Y coordinate
                        table_area = f"{x1},{y1},{x2},{y2}"
                        
                        # Get column lines for this region
                        region_columns = []
                        if section_column_lines:
                            for line in section_column_lines:
                                if len(line) == 3 and line[2] == i:
                                    region_columns.append(line[0].x() * scale_x)
                                elif len(line) == 2 and i == 0:
                                    region_columns.append(line[0].x() * scale_x)
                        
                        # Sort and format column lines
                        col_str = ','.join([str(x) for x in sorted(region_columns)]) if region_columns else ''
                        
                        # Set extraction parameters
                        params = {
                            'pages': str(self.current_page),
                            'table_areas': [table_area],
                            'columns': [col_str] if col_str else None,
                            'split_text': self.extraction_params['split_text'],
                            'strip_text': self.extraction_params['strip_text'],
                            'flavor': 'stream',
                            'row_tol': self.extraction_params[section]['row_tol']
                        }
                        
                        try:
                            # Extract table
                            table_result = pypdf_table_extraction.read_pdf(self.pdf_path, **params)
                            
                            if table_result and len(table_result) > 0 and table_result[0].df is not None:
                                table_df = table_result[0].df
                                
                                # Clean up the DataFrame
                                table_df = table_df.replace(r'^\s*$', pd.NA, regex=True)
                                table_df = table_df.dropna(how='all')
                                table_df = table_df.dropna(axis=1, how='all')
                                
                                if not table_df.empty:
                                    # Process based on section type
                                    if section == 'header':
                                        # Convert to key-value format
                                        if len(table_df.columns) >= 2:
                                            # Use first column as key, second as value
                                            processed_df = pd.DataFrame({
                                                'Field': table_df.iloc[:, 0],
                                                'Value': table_df.iloc[:, 1]
                                            })
                                        else:
                                            # If only one column, use index as key
                                            processed_df = pd.DataFrame({
                                                'Field': table_df.index,
                                                'Value': table_df.iloc[:, 0]
                                            })
                                        processed_tables.append(processed_df)
                                    elif section == 'summary':
                                        # For summary, keep all columns to support multi-column data
                                        processed_tables.append(table_df)
                                    else:  # items section
                                        # Keep original structure for items
                                        processed_tables.append(table_df)
                                
                        except Exception as e:
                            print(f"Error extracting table: {str(e)}")
                    
                    # Update the data for the current page
                    current_page_data = self.all_pages_data[self.current_page - 1]
                    if processed_tables:
                        if len(processed_tables) == 1:
                            current_page_data[section] = processed_tables[0]
                        else:
                            current_page_data[section] = processed_tables
                    else:
                        current_page_data[section] = None
                else:
                    print(f"No regions defined for {section} section")
            
            # Update the display
            self.update_tables()
            
        except Exception as e:
            print(f"Error in extract_and_update_section_data: {str(e)}")
            import traceback
            traceback.print_exc()

    def update_tables(self):
        print(f"\nUpdating tables for page {self.current_page}")
        try:
            # Get data for current page (0-based index)
            current_page_data = self.all_pages_data[self.current_page - 1]
            print(f"Current page data structure: {list(current_page_data.keys())}")
            
            # Update the data table based on current section
            if self.current_section in current_page_data:
                section_data = current_page_data[self.current_section]
                if section_data is not None:
                    if isinstance(section_data, list):
                        # Handle multiple tables
                        self.update_data_table_for_header(section_data, self.current_section)
                    else:
                        # Handle single table
                        self.update_data_table(section_data, self.current_section)
                else:
                    # Clear table and show no data message
                    self.data_table.setRowCount(0)
                    self.data_table.setColumnCount(2)
                    self.data_table.setHorizontalHeaderLabels(["Key", "Value"])
                    self.data_table.insertRow(0)
                    message_item = QTableWidgetItem(f"No data available for the {self.current_section} section")
                    self.data_table.setItem(0, 0, message_item)
                    self.data_table.setSpan(0, 0, 1, 2)
            else:
                # Clear table and show no data message
                self.data_table.setRowCount(0)
                self.data_table.setColumnCount(2)
                self.data_table.setHorizontalHeaderLabels(["Key", "Value"])
                self.data_table.insertRow(0)
                message_item = QTableWidgetItem(f"No data available for the {self.current_section} section")
                self.data_table.setItem(0, 0, message_item)
                self.data_table.setSpan(0, 0, 1, 2)
            
            # Update section title
            self.section_title.setText(f"{self.current_section.title()} Section")
            
            # Update section label
            if hasattr(self, 'section_label'):
                self.section_label.setText(f"Section: {self.current_section.title()}")
            
        except Exception as e:
            print(f"Error updating tables: {str(e)}")
            import traceback
            traceback.print_exc()

    def next_page(self):
        print(f"\nMoving to next page from {self.current_page}")
        if self.current_page < self.total_pages:
            self.current_page += 1
            print(f"New page number: {self.current_page}")
            self.load_pdf()

    def prev_page(self):
        print(f"\nMoving to previous page from {self.current_page}")
        if self.current_page > 1:
            self.current_page -= 1
            print(f"New page number: {self.current_page}")
            self.load_pdf()

    def go_back(self):
        # Get the main window and go back one screen
        main_window = self.window()
        if hasattr(main_window, 'stacked_widget'):
            main_window.stacked_widget.setCurrentWidget(main_window.pdf_processor)

    def save_template(self):
        """Save the current multi-page template to the database"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QTextEdit, QDialogButtonBox, QMessageBox, QCheckBox, QGroupBox, QHBoxLayout
        
        # Create a dialog for entering template name and description
        dialog = QDialog(self)
        dialog.setWindowTitle("Save Multi-page Template")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        
        # Create form layout for inputs
        form_layout = QFormLayout()
        
        # Name input
        name_label = QLabel("Template Name:")
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter a descriptive name for your template")
        form_layout.addRow(name_label, name_input)
        
        # Description input
        desc_label = QLabel("Description (optional):")
        desc_input = QTextEdit()
        desc_input.setPlaceholderText("Describe the purpose or usage of this template")
        desc_input.setMaximumHeight(100)
        form_layout.addRow(desc_label, desc_input)
        
        layout.addLayout(form_layout)
        
        # Add template options group
        options_group = QGroupBox("Template Options")
        options_layout = QVBoxLayout(options_group)
        
        # Middle page checkbox
        middle_page_layout = QVBoxLayout()
        middle_page_checkbox = QCheckBox("Set Middle Page")
        middle_page_checkbox.setToolTip("Use this option for invoices with repetitive middle pages")
        middle_page_layout.addWidget(middle_page_checkbox)
        
        # Info message for middle page (initially hidden)
        middle_page_info = QLabel("Page range 2-2 is set as middle pages. Middle pages are repetitive and can exist in bulk extraction invoices.")
        middle_page_info.setStyleSheet("color: #666; font-style: italic;")
        middle_page_info.setWordWrap(True)
        middle_page_info.setVisible(False)
        middle_page_layout.addWidget(middle_page_info)
        
        # Connect checkbox to show/hide info
        middle_page_checkbox.toggled.connect(middle_page_info.setVisible)
        
        options_layout.addLayout(middle_page_layout)
        
        # Fixed number of pages checkbox
        fixed_pages_layout = QVBoxLayout()
        fixed_pages_checkbox = QCheckBox("Fixed Number of Pages")
        fixed_pages_checkbox.setToolTip("Use this option when all invoices have the same number of pages")
        fixed_pages_layout.addWidget(fixed_pages_checkbox)
        
        # Info message for fixed pages (initially hidden)
        fixed_pages_info = QLabel("Pages will be the same as sample while bulk extraction.")
        fixed_pages_info.setStyleSheet("color: #666; font-style: italic;")
        fixed_pages_info.setWordWrap(True)
        fixed_pages_info.setVisible(False)
        fixed_pages_layout.addWidget(fixed_pages_info)
        
        # Connect checkbox to show/hide info
        fixed_pages_checkbox.toggled.connect(fixed_pages_info.setVisible)
        
        options_layout.addLayout(fixed_pages_layout)
        
        layout.addWidget(options_group)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Show the dialog and get result
        if dialog.exec() == QDialog.Accepted:
            template_name = name_input.text().strip()
            template_description = desc_input.toPlainText().strip()
            
            if not template_name:
                QMessageBox.warning(
                    self,
                    "Template Name Required",
                    "Please provide a name for your template."
                )
                return
            
            # Get checkbox values
            use_middle_page = middle_page_checkbox.isChecked()
            fixed_page_count = fixed_pages_checkbox.isChecked()
            
            # Call the method to actually save the template with options
            self.save_template_directly(
                template_name, 
                template_description,
                use_middle_page=use_middle_page,
                fixed_page_count=fixed_page_count
            )
        else:
            # User canceled
            return
            
    def save_template_directly(self, name, description, use_middle_page=False, fixed_page_count=False):
        """Save the multi-page template directly to the database with actual parameters"""
        try:
            print("\nStarting template save process...")
            
            # Validate input parameters
            if not name or not isinstance(name, str):
                raise ValueError("Template name must be a non-empty string")
            if not isinstance(description, str):
                description = str(description)
            
            # Initialize config dictionary
            config = {
                'use_middle_page': use_middle_page,
                'fixed_page_count': fixed_page_count,
                'total_pages': len(self.pdf_document),
                'page_indices': list(range(len(self.pdf_document)))
            }
            
            # Validate regions and column lines data structures
            if not hasattr(self, 'regions') or not isinstance(self.regions, dict):
                print("Warning: No regions data found, initializing empty regions dictionary")
                self.regions = {}
            
            if not hasattr(self, 'column_lines') or not isinstance(self.column_lines, dict):
                print("Warning: No column lines data found, initializing empty column lines dictionary")
                self.column_lines = {}
            
            # Validate all_pages_data
            if not hasattr(self, 'all_pages_data') or not isinstance(self.all_pages_data, list):
                print("Warning: No page data found, initializing empty page data list")
                self.all_pages_data = []
            
            # Calculate total pages and page indices to save
            total_pages = len(self.pdf_document)
            if total_pages == 0:
                raise ValueError("No pages found in PDF document")
            
            page_indices_to_save = list(range(total_pages))
            if use_middle_page and total_pages > 2:
                # For middle page feature, only save first, last, and middle pages
                middle_idx = total_pages // 2
                page_indices_to_save = [0, middle_idx, total_pages - 1]
                config['page_indices'] = page_indices_to_save
            
            # Initialize lists to store page data
            page_regions = []
            page_column_lines = []
            
            print(f"\nProcessing {total_pages} pages for template saving...")
            
            # For each page, convert regions and column lines to serializable format
            for page_idx, page_num in enumerate(range(total_pages)):
                # Skip pages not in our save list if using middle page feature
                if use_middle_page and total_pages > 2 and page_num not in page_indices_to_save:
                    if page_idx < len(page_indices_to_save):
                        continue

                print(f"\nProcessing page {page_num + 1}/{total_pages}")

                # Get the regions and column lines for this page
                regions = self.regions.get(page_num, {})
                column_lines = self.column_lines.get(page_num, {})
                
                # Validate regions structure
                if not isinstance(regions, dict):
                    print(f"Warning: Invalid regions structure for page {page_num + 1}, initializing empty dict")
                    regions = {}
                    
                # Validate column lines structure
                if not isinstance(column_lines, dict):
                    print(f"Warning: Invalid column lines structure for page {page_num + 1}, initializing empty dict")
                    column_lines = {}
                
                # Get page dimensions for coordinate conversion
                page = self.pdf_document[page_num]
                page_width = page.mediabox.width
                page_height = page.mediabox.height
                
                # Get rendered dimensions
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                rendered_width = pix.width
                rendered_height = pix.height
                
                # Calculate scaling factors
                scale_x = page_width / rendered_width
                scale_y = page_height / rendered_height
                
                # Convert QRect objects to dictionaries for JSON serialization
                serializable_regions = {}
                for section, rects in regions.items():
                    serializable_regions[section] = []
                    for rect in rects:
                        # Convert QRect to bottom-left coordinate system
                        # In bottom-left system, y coordinates are measured from bottom up
                        # So we need to subtract y coordinates from page height
                        x1 = rect.x() * scale_x
                        y1 = page_height - (rect.y() * scale_y)  # Convert top y1 to bottom y1
                        x2 = (rect.x() + rect.width()) * scale_x
                        y2 = page_height - ((rect.y() + rect.height()) * scale_y)  # Convert bottom y2 to bottom y2
                        
                        serializable_regions[section].append({
                            'x1': x1,
                            'y1': y1,  # Store in bottom-left system
                            'x2': x2,
                            'y2': y2   # Store in bottom-left system
                        })
                
                # Convert column lines to serializable format
                serializable_column_lines = {}
                for section, lines in column_lines.items():
                    if not isinstance(lines, list):
                        print(f"Warning: Invalid column lines structure for section {section} on page {page_num + 1}, skipping")
                        continue
                    
                    serializable_column_lines[section] = []
                    for line in lines:
                        try:
                            if not isinstance(line, (list, tuple)) or len(line) < 2:
                                print(f"Warning: Invalid column line in section {section} on page {page_num + 1}, skipping")
                                continue
                            
                            # Convert line to serializable format with scaled coordinates
                            # Keep the QPoint format with x and y properties
                            line_data = [
                                {
                                    'x': line[0].x() * scale_x,
                                    'y': line[0].y() * scale_y
                                },
                                {
                                    'x': line[1].x() * scale_x,
                                    'y': line[1].y() * scale_y
                                }
                            ]
                            if len(line) > 2:
                                line_data.append(line[2])  # Add region index if present
                            serializable_column_lines[section].append(line_data)
                        except Exception as e:
                            print(f"Warning: Error converting column line in section {section} on page {page_num + 1}: {str(e)}")
                            continue
                
                # Add the serialized data for this page
                page_regions.append(serializable_regions)
                page_column_lines.append(serializable_column_lines)
            
                print(f"Successfully processed page {page_num + 1}")
            
            # Initialize page_column_lines if not already initialized
            if not page_column_lines:
                page_column_lines = []
                for page_data in page_regions:
                    page_column_lines.append({})  # Add empty dict for each page
            
            # Ensure we have extraction_params with proper default values if not set elsewhere
            if not hasattr(self, 'extraction_params'):
                print("\nInitializing default extraction parameters for template saving:")
                self.extraction_params = {
                    'header': {'row_tol': 5},    # Default for header
                    'items': {'row_tol': 15},    # Default for items
                    'summary': {'row_tol': 10},  # Default for summary
                    'split_text': True,
                    'strip_text': '\n',
                    'flavor': 'stream'
                }
                print(f"  Header row_tol: {self.extraction_params['header']['row_tol']}")
                print(f"  Items row_tol: {self.extraction_params['items']['row_tol']}")
                print(f"  Summary row_tol: {self.extraction_params['summary']['row_tol']}")
            
            # Try to get latest extraction parameters from main window
            try:
                from PySide6.QtWidgets import QApplication
                from main import PDFHarvest  # Import the main window class
                
                # Look specifically for the main application window
                for widget in QApplication.topLevelWidgets():
                    if isinstance(widget, PDFHarvest):
                        # Get the latest extraction parameters from main window
                        if hasattr(widget, 'latest_extraction_params'):
                            latest_params = widget.latest_extraction_params
                            print("\nFound latest extraction parameters in main window:")
                            
                            # Update section-specific parameters
                            for section in ['header', 'items', 'summary']:
                                if section in latest_params and 'row_tol' in latest_params[section]:
                                    self.extraction_params[section]['row_tol'] = latest_params[section]['row_tol']
                                    print(f"  Updated {section} row_tol: {latest_params[section]['row_tol']}")
                            
                            # Update global parameters
                            if 'split_text' in latest_params:
                                self.extraction_params['split_text'] = latest_params['split_text']
                                print(f"  Updated split_text: {latest_params['split_text']}")
                            if 'strip_text' in latest_params:
                                self.extraction_params['strip_text'] = latest_params['strip_text']
                                print(f"  Updated strip_text: {repr(latest_params['strip_text'])}")
                            if 'flavor' in latest_params:
                                self.extraction_params['flavor'] = latest_params['flavor']
                                print(f"  Updated flavor: {latest_params['flavor']}")
                            
                            # break
            except Exception as e:
                print(f"Could not get latest extraction params from main window: {str(e)}")
            
            # Add extraction parameters to config
            config['extraction_params'] = self.extraction_params
            
            print(f"\nFinal extraction parameters being saved to template:")
            for section in ['header', 'items', 'summary']:
                print(f"  {section.title()} row_tol: {self.extraction_params[section]['row_tol']}")
            
            print(f"  split_text: {self.extraction_params['split_text']}")
            print(f"  strip_text: {repr(self.extraction_params['strip_text'])}")
            print(f"  flavor: {self.extraction_params['flavor']}")
            
            
            print(f"\nSaving multi-page template '{name}' with {len(page_regions)} pages")
            print(f"Page regions count: {len(page_regions)}")
            print(f"Page column lines count: {len(page_column_lines)}")
            
            # Save template to the database
            template_id = db.save_template(
                    name=name,
                    description=description,
                    regions={},  # Empty for multi-page templates
                    column_lines={},  # Empty for multi-page templates
                    config=config,
                    template_type="multi",  # This is a multi-page template
            page_count=len(self.all_pages_data),  # Add the page count
                    page_regions=page_regions,
                    page_column_lines=page_column_lines,
                    page_configs=None  # Add page_configs parameter with default value
                )
            
            if template_id:
                QMessageBox.information(
                    self,
                    "Template Saved",
                    f"Multi-page template '{name}' has been saved successfully.Navigating to Template Manager...",
                    QMessageBox.Ok
                )
                print(f"Template saved successfully with ID: {template_id}")               
                # Navigate to template manager screen
                # self.navigate_to_template_manager()
            else:
                raise Exception("Failed to save template - no template ID returned")
            
            return template_id
                
        except Exception as e:
            print(f"\nError saving template: {str(e)}")
            import traceback
            traceback.print_exc()
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Error")
            msg.setText("Failed to save template")
            msg.setInformativeText(f"An error occurred: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            return None
        

    def get_region_color(self, region_type):
        colors = {
            'header': QColor(255, 0, 0, 127),  # Red
            'items': QColor(0, 255, 0, 127),   # Green
            'summary': QColor(0, 0, 255, 127)  # Blue
        }
        return colors.get(region_type, QColor(0, 0, 0, 127))

    def extract_with_new_params(self, section, table_areas, column_lines):
        """Show dialog to adjust extraction parameters and retry with new settings"""
        try:
            # Create dialog for parameter adjustment
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Adjust {section.title()} Extraction Parameters")
            dialog.setMinimumWidth(400)
            
            # Create form layout
            form_layout = QFormLayout()
            
            # Add row tolerance input
            row_tol_input = QSpinBox()
            row_tol_input.setRange(1, 50)
            row_tol_input.setValue(self.extraction_params[section]['row_tol'])
            form_layout.addRow("Row Tolerance:", row_tol_input)
            
            # Add split text checkbox
            split_text_check = QCheckBox()
            split_text_check.setChecked(self.extraction_params['split_text'])
            form_layout.addRow("Split Text:", split_text_check)
            
            # Add strip text input
            strip_text_input = QLineEdit()
            strip_text_input.setText(self.extraction_params['strip_text'])
            form_layout.addRow("Strip Text:", strip_text_input)
            
            # Add flavor selection
            flavor_combo = QComboBox()
            flavor_combo.addItems(['stream', 'lattice'])
            flavor_combo.setCurrentText(self.extraction_params['flavor'])
            form_layout.addRow("Flavor:", flavor_combo)
            
            # Add buttons
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            
            # Add everything to dialog layout
            layout = QVBoxLayout()
            layout.addLayout(form_layout)
            layout.addWidget(button_box)
            dialog.setLayout(layout)
            
            # Show dialog and get result
            if dialog.exec() == QDialog.Accepted:
                # Get new parameters
                new_params = {
                    'row_tol': row_tol_input.value(),
                    'split_text': split_text_check.isChecked(),
                    'strip_text': strip_text_input.text(),
                    'flavor': flavor_combo.currentText()
                }
                
                # Update extraction parameters
                self.extraction_params[section]['row_tol'] = new_params['row_tol']
                self.extraction_params['split_text'] = new_params['split_text']
                self.extraction_params['strip_text'] = new_params['strip_text']
                self.extraction_params['flavor'] = new_params['flavor']
                
                # Print current extraction parameters for debugging
                print(f"\nUpdated extraction parameters:")
                print(f"  {section.title()} row_tol: {self.extraction_params[section]['row_tol']}")
                print(f"  split_text: {self.extraction_params['split_text']}")
                print(f"  strip_text: {repr(self.extraction_params['strip_text'])}")
                
                # Single table extraction with new parameters
                single_table_params = {
                    'pages': '1',
                    'table_areas': table_areas,
                    'columns': column_lines if column_lines else None,
                    'split_text': new_params['split_text'],
                    'strip_text': new_params['strip_text'],
                    'flavor': new_params['flavor'],
                    'row_tol': new_params['row_tol']
                }
                
                print(f"\nRetrying single table extraction with new parameters: {single_table_params}")
                
                # Extract just this table
                table_result = pypdf_table_extraction.read_pdf(self.pdf_path, **single_table_params)
                
                if table_result and len(table_result) > 0 and table_result[0].df is not None:
                    table_df = table_result[0].df
                    
                    print(f"  Raw data extracted:")
                    print(table_df)
                    
                    if not table_df.empty:
                        print(f"  Successfully extracted table with {len(table_df)} rows and {len(table_df.columns)} columns")
                        
                        # Update the appropriate DataFrame based on section
                        if section == 'header':
                            self.header_df = table_df
                            self.update_data_table_for_header(table_df, 'header')
                        elif section == 'items':
                            self.item_details_df = table_df
                            self.update_data_table(table_df, 'items')
                        elif section == 'summary':
                            self.summary_df = table_df
                            self.update_data_table(table_df, 'summary')
                    else:
                        print(f"  No valid data found after cleaning")
                else:
                    print(f"  No data extracted from table area")
                
        except Exception as e:
            print(f"Error in extract_with_new_params: {str(e)}")
            import traceback
            traceback.print_exc()

    def update_data_table_for_header(self, table_list, section_type='header'):
        """Method to display multiple tables of a section type (header or summary)"""
        try:
            print(f"\n=== Updating data table for {section_type} ===")
            print(f"Input type: {type(table_list)}")
            
            # Clear existing table
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
            
            # Handle empty input
            if table_list is None:
                print("Table list is None")
                return
                
            if isinstance(table_list, pd.DataFrame):
                print("Single DataFrame provided")
                if table_list.empty:
                    print("DataFrame is empty")
                    return
                table_list = [table_list]
            elif not isinstance(table_list, list):
                print(f"Unexpected input type: {type(table_list)}")
                return
                
            if len(table_list) == 0:
                print("Table list is empty")
                return
            
            print(f"Processing {len(table_list)} tables")
            
            # Process each table
            for i, df in enumerate(table_list):
                if df is None or df.empty:
                    print(f"Table {i + 1} is None or empty, skipping")
                    continue
                    
                print(f"Processing table {i + 1} with shape {df.shape}")
                
                # Add table number as header if multiple tables
                if len(table_list) > 1:
                    header_item = QTableWidgetItem(f"Table {i + 1}")
                    header_item.setBackground(QColor("#2c3e50"))
                    header_item.setForeground(QColor("white"))
                    header_item.setFont(QFont("Arial", 10, QFont.Bold))
                    self.data_table.insertRow(self.data_table.rowCount())
                    self.data_table.setItem(self.data_table.rowCount() - 1, 0, header_item)
                    self.data_table.setSpan(self.data_table.rowCount() - 1, 0, 1, df.shape[1])
                
                # Add column headers
                if self.data_table.columnCount() < df.shape[1]:
                    self.data_table.setColumnCount(df.shape[1])
                    for col in range(df.shape[1]):
                        header_item = QTableWidgetItem(str(df.columns[col]))
                        header_item.setBackground(QColor("#34495e"))
                        header_item.setForeground(QColor("white"))
                        header_item.setFont(QFont("Arial", 10, QFont.Bold))
                        self.data_table.setHorizontalHeaderItem(col, header_item)
                
                # Add data rows
                for row in range(df.shape[0]):
                    self.data_table.insertRow(self.data_table.rowCount())
                    for col in range(df.shape[1]):
                        value = str(df.iloc[row, col])
                        item = QTableWidgetItem(value)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        self.data_table.setItem(self.data_table.rowCount() - 1, col, item)
                
                # Add spacing between tables
                if i < len(table_list) - 1:
                    spacer_row = self.data_table.rowCount()
                    self.data_table.insertRow(spacer_row)
                    spacer_item = QTableWidgetItem("")
                    spacer_item.setBackground(QColor("#2c3e50"))
                    self.data_table.setItem(spacer_row, 0, spacer_item)
                    self.data_table.setSpan(spacer_row, 0, 1, df.shape[1])
            
            print("Data table update completed successfully")
            
        except Exception as e:
            print(f"\nError in update_data_table_for_header: {str(e)}")
            import traceback
            traceback.print_exc()
            # Clear the table in case of error
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)

    def update_data_table(self, df, section):
        """Update the data table with the provided DataFrame and section type"""
        try:
            print(f"\n=== Updating data table for {section} ===")
            
            # Clear existing table
            self.data_table.clear()
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
            
            if df is not None and not df.empty:
                # Set up the table with two columns (Key and Value) for JSON-like display
                self.data_table.setColumnCount(2)
                self.data_table.setHorizontalHeaderLabels(["Key", "Value"])
                
                # Process differently based on section type
                if section == 'header':
                    # HEADER SECTION: First column as key, other columns as values
                    self.section_title.setText("Header Section - JSON Format")
                    
                    row_count = 0
                    for df_row_idx, row in df.iterrows():
                        # Skip processing if less than 2 columns
                        if len(row) < 2:
                            continue
                        
                        # Get the key from the first column
                        key = str(row.iloc[0]) if not pd.isna(row.iloc[0]) else "Unknown"
                        
                        # Create object for values from other columns
                        values = {}
                        for col_idx in range(1, len(row)):
                            col_name = f"C{col_idx}" if isinstance(df.columns[col_idx], int) else str(df.columns[col_idx])
                            value = str(row.iloc[col_idx]) if not pd.isna(row.iloc[col_idx]) else ""
                            if value:  # Only add non-empty values
                                values[col_name] = value
                        
                        # Add row for the key-value pair
                        self.data_table.insertRow(row_count)
                        key_item = QTableWidgetItem(key)
                        value_item = QTableWidgetItem(str(values))
                        self.data_table.setItem(row_count, 0, key_item)
                        self.data_table.setItem(row_count, 1, value_item)
                        row_count += 1
                    
                elif section == 'items':
                    # ITEMS SECTION: Show all rows directly without grouping
                    self.section_title.setText("Items Section")
                    
                    row_count = 0
                    
                    for df_row_idx, row in df.iterrows():
                        # Create a dictionary of column values for this row
                        item_data = {}
                        for col_idx, value in enumerate(row):
                            col_name = f"C{col_idx+1}" if isinstance(df.columns[col_idx], int) else str(df.columns[col_idx])
                            if not pd.isna(value) and str(value).strip():
                                item_data[col_name] = str(value)
                        
                        # Only add rows that have at least some data
                        if item_data:
                            self.data_table.insertRow(row_count)
                            item_key = QTableWidgetItem(f"Row {df_row_idx+1}")
                            item_value = QTableWidgetItem(str(item_data))
                            self.data_table.setItem(row_count, 0, item_key)
                            self.data_table.setItem(row_count, 1, item_value)
                            row_count += 1
                
                elif section == 'summary':
                    # SUMMARY SECTION: Process with multiple columns support
                    self.section_title.setText("Summary Section")
                    
                    row_count = 0
                    # Process all rows regardless of column count
                    for df_row_idx, row in df.iterrows():
                        # Skip empty rows
                        if row.isna().all():
                            continue
                            
                        # Get the key from the first column
                        key = str(row.iloc[0]) if not pd.isna(row.iloc[0]) else "Unknown"
                        
                        if key.strip():  # Only add if the key is not empty
                            if len(df.columns) == 1:
                                # Single column - just show the key
                                self.data_table.insertRow(row_count)
                                key_item = QTableWidgetItem(key)
                                value_item = QTableWidgetItem("")
                                self.data_table.setItem(row_count, 0, key_item)
                                self.data_table.setItem(row_count, 1, value_item)
                                row_count += 1
                            elif len(df.columns) == 2:
                                # Two columns - simple key-value
                                value = str(row.iloc[1]) if not pd.isna(row.iloc[1]) else ""
                                
                                self.data_table.insertRow(row_count)
                                key_item = QTableWidgetItem(key)
                                value_item = QTableWidgetItem(value)
                                self.data_table.setItem(row_count, 0, key_item)
                                self.data_table.setItem(row_count, 1, value_item)
                                row_count += 1
                            else:
                                # Multiple columns - create a dictionary for columns beyond the first
                                values = {}
                                for col_idx in range(1, len(row)):
                                    col_name = f"C{col_idx}" if isinstance(df.columns[col_idx], int) else str(df.columns[col_idx])
                                    value = str(row.iloc[col_idx]) if not pd.isna(row.iloc[col_idx]) else ""
                                    if value:  # Only add non-empty values
                                        values[col_name] = value
                                
                                self.data_table.insertRow(row_count)
                                key_item = QTableWidgetItem(key)
                                value_item = QTableWidgetItem(str(values))
                                self.data_table.setItem(row_count, 0, key_item)
                                self.data_table.setItem(row_count, 1, value_item)
                                row_count += 1
                
                
                # Adjust column widths for better readability
                header = self.data_table.horizontalHeader()
                header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
                header.setSectionResizeMode(1, QHeaderView.Stretch)
                
                # Set background colors to distinguish sections
                self.data_table.setStyleSheet("""
                    QTableWidget {
                        background-color: white;
                        color: black;
                    }
                    QTableWidget::item:selected {
                        background-color: #E6F2FF;
                        color: black;
                    }
                    QHeaderView::section {
                        background-color: #f0f0f0;
                        padding: 5px;
                        border: 1px solid #ddd;
                        font-weight: bold;
                        color: black;
                    }
                """)
            else:
                self.section_title.setText(f"No {section.title()} Data Available")
                
                # Add a message row
                self.data_table.setColumnCount(2)
                self.data_table.setHorizontalHeaderLabels(["Key", "Value"])
                self.data_table.insertRow(0)
                message_item = QTableWidgetItem(f"No data available for the {section} section")
                self.data_table.setItem(0, 0, message_item)
                self.data_table.setSpan(0, 0, 1, 2)  # Span across both columns
                
        except Exception as e:
            print(f"\nError in update_data_table: {str(e)}")
            import traceback
            traceback.print_exc()
            # Clear the table in case of error
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)

    def next_section(self):
        """Move to the next section"""
        sections = ['header', 'items', 'summary']
        current_index = sections.index(self.current_section)
        if current_index < len(sections) - 1:
            self.current_section = sections[current_index + 1]
            self.section_label.setText(f"Section: {self.current_section.title()}")
            self.update_tables()

    def prev_section(self):
        """Move to the previous section"""
        sections = ['header', 'items', 'summary']
        current_index = sections.index(self.current_section)
        if current_index > 0:
            self.current_section = sections[current_index - 1]
            self.section_label.setText(f"Section: {self.current_section.title()}")
            self.update_tables()

    def show_custom_settings(self):
        """Show dialog to adjust extraction parameters"""
        # Get current page's regions
        current_regions = self.regions
        if isinstance(self.regions, dict) and (self.current_page - 1) in self.regions:
            current_regions = self.regions[self.current_page - 1]
        
        # Get current page's column lines
        current_column_lines = self.column_lines
        if isinstance(self.column_lines, dict) and (self.current_page - 1) in self.column_lines:
            current_column_lines = self.column_lines[self.current_page - 1]
        
        # Get regions and column lines for current section
        if self.current_section in current_regions and current_regions[self.current_section]:
            section_regions = current_regions[self.current_section]
            section_column_lines = current_column_lines.get(self.current_section, [])
            
            # Get current page
            page = self.pdf_document[self.current_page - 1]
            
            # Get actual page dimensions in points (1/72 inch)
            page_width = page.mediabox.width
            page_height = page.mediabox.height
            
            # Get the rendered dimensions
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            rendered_width = pix.width
            rendered_height = pix.height
            
            # Calculate scaling factors
            scale_x = page_width / rendered_width
            scale_y = page_height / rendered_height
            
            # Convert regions to table areas
            table_areas = []
            column_lines = []
            
            for i, region in enumerate(section_regions):
                # Convert region coordinates to table area format
                x1 = region.x() * scale_x
                y1 = page_height - (region.y() * scale_y)
                x2 = (region.x() + region.width()) * scale_x
                y2 = page_height - ((region.y() + region.height()) * scale_y)
                table_area = f"{x1},{y1},{x2},{y2}"
                table_areas.append(table_area)
                
                # Get column lines for this region
                region_columns = []
                if section_column_lines:
                    for line in section_column_lines:
                        # Check if the line has a region index and matches current region
                        if len(line) == 3 and line[2] == i:
                            region_columns.append(line[0].x() * scale_x)
                        # Handle old format without region index - associate with first region
                        elif len(line) == 2 and i == 0:
                            region_columns.append(line[0].x() * scale_x)
                
                if region_columns:
                    # Sort column lines by x-coordinate and join as comma-separated string
                    col_str = ','.join([str(x) for x in sorted(region_columns)])
                    column_lines.append(col_str)
                else:
                    # Empty string for regions with no column lines
                    column_lines.append('')
            
            # Extract with new parameters
            self.extract_with_new_params(self.current_section, table_areas, column_lines)
            return True
        else:
            QMessageBox.warning(self, "Warning", f"No regions defined for {self.current_section} section")
            return False

    def show_json_view(self):
        """Show the extracted data in JSON format"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("JSON View")
            dialog.setMinimumSize(800, 600)
            
            layout = QVBoxLayout(dialog)
            
            # Add header
            header = QLabel("Extracted Data (JSON Format)")
            header.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
            layout.addWidget(header)
            
            # Add text area for JSON
            json_text = QTextEdit()
            json_text.setReadOnly(True)
            json_text.setFont(QFont("Courier New", 10))
            layout.addWidget(json_text)
            
            # Format and display the data
            if hasattr(self, 'all_pages_data') and self.all_pages_data:
                formatted_json = json.dumps(self.all_pages_data, indent=2)
                json_text.setText(formatted_json)
            else:
                json_text.setText("No data extracted yet")
            
            # Add close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.close)
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            layout.addWidget(close_btn)
            
            dialog.exec()
            
        except Exception as e:
            print(f"Error showing JSON view: {str(e)}")
            import traceback
            traceback.print_exc()

    def download_json(self):
        """Download the extracted data as JSON file"""
        try:
            # Get suggested filename from PDF path
            base_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
            suggested_name = f"{base_name}_extracted.json"
            
            # Open file dialog to select save location
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save JSON Data",
                suggested_name,
                "JSON Files (*.json);;All Files (*)"
            )
            
            if file_path:
                # Ensure the file has .json extension
                if not file_path.lower().endswith('.json'):
                    file_path += '.json'
                
                # Write the data to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.all_pages_data, f, indent=2, ensure_ascii=False)
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Download Complete",
                    f"Data successfully saved to:\n{file_path}"
                )
                
        except Exception as e:
            # Show error message
            QMessageBox.critical(
                self,
                "Download Error",
                f"Error saving data: {str(e)}"
            )
            print(f"Error downloading JSON: {str(e)}")
            import traceback
            traceback.print_exc()
