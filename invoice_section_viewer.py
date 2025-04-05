from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QScrollArea, QFrame, QStackedWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QDialog, QFormLayout, 
                             QSpinBox, QCheckBox, QLineEdit, QMessageBox, QDialogButtonBox, QSpacerItem,
                             QComboBox, QGroupBox, QFileDialog)
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import (QFont, QImage, QPixmap, QCursor, QPainter, 
                          QPen, QColor)
import fitz
from PIL import Image
import io
import pandas as pd
import re
import pypdf_table_extraction
import json
import os

class PDFLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setMouseTracking(True)
        self.scaled_pixmap = None
        self.scale_factor = 1.0
        self.offset = QPoint(0, 0)

    def setPixmap(self, pixmap):
        super().setPixmap(pixmap)
        self.adjustPixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjustPixmap()

    def adjustPixmap(self):
        if not self.pixmap():
            return
            
        # Calculate scaling to fit the label while maintaining aspect ratio
        label_size = self.size()
        pixmap_size = self.pixmap().size()
        
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
        self.scaled_pixmap = self.pixmap().scaled(
            scaled_width,
            scaled_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

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
        if not self.scaled_pixmap:
            super().paintEvent(event)
            return
            
        painter = QPainter(self)
        painter.drawPixmap(self.offset, self.scaled_pixmap)

class InvoiceSectionViewer(QWidget):
    # Add a new signal to notify when save template button is clicked
    save_template_signal = Signal()  # Signal to trigger template saving
    
    def __init__(self, pdf_path, header_df, item_details_df, summary_df, regions, column_lines, is_multi_page=False):
        super().__init__()
        self.pdf_path = pdf_path
        self.header_df = header_df
        self.item_details_df = item_details_df
        self.summary_df = summary_df
        self.regions = regions
        self.column_lines = column_lines
        self.is_multi_page = is_multi_page
        
        # Initialize section areas
        self.header_areas = []
        self.item_areas = []
        self.summary_areas = []
        
        # Initialize current page for section navigation
        self.current_page = 0
        
        # Initialize extraction parameters
        self.extraction_params = {
            'header': {'row_tol': 5},
            'items': {'row_tol': 5},
            'summary': {'row_tol': 5},
            'split_text': True,
            'strip_text': '\n',
            'flavor': 'stream'
        }
        
        # Initialize UI
        self.initUI()
        
        # Load PDF and draw sections
        self.load_pdf()
        self.draw_sections()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Title
        title = QLabel("Invoice Section Analysis")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #333333; margin: 20px 0;")
        layout.addWidget(title)

        # Create main content area with split view
        content = QWidget()
        content_layout = QHBoxLayout(content)  # Changed to horizontal layout
        
        # Left side - PDF display
        pdf_container = QWidget()
        pdf_layout = QVBoxLayout(pdf_container)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(600)
        
        self.pdf_label = PDFLabel(self)
        self.pdf_label.setAlignment(Qt.AlignCenter)
        self.pdf_label.setStyleSheet("QLabel { background-color: #f0f0f0; }")
        
        self.scroll_area.setWidget(self.pdf_label)
        pdf_layout.addWidget(self.scroll_area)
        
        # Right side - Extracted data
        data_container = QWidget()
        data_layout = QVBoxLayout(data_container)
        
        # Section title container with horizontal layout for title and download button
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
        
        data_layout.addWidget(section_title_container)
        
        # Table for extracted data
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
        data_layout.addWidget(self.data_table)
        
        # Add both containers to the main layout
        content_layout.addWidget(pdf_container)
        content_layout.addWidget(data_container)
        
        layout.addWidget(content)

        # Navigation
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
        prev_btn = QPushButton("Previous Section")
        prev_btn.clicked.connect(self.prev_section)
        prev_btn.setStyleSheet("""
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

        next_btn = QPushButton("Next Section")
        next_btn.clicked.connect(self.next_section)
        next_btn.setStyleSheet("""
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
        self.retry_btn.setToolTip("Adjust extraction parameters or test regex patterns for table content filtering")
        
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
        center_nav.addWidget(prev_btn)
        center_nav.addWidget(next_btn)
        
        # Add the retry button
        center_nav.addWidget(self.retry_btn)
        
        # Add the center navigation to the main nav layout
        nav_layout.addLayout(center_nav)
        
        # Add another stretch
        nav_layout.addStretch()
        
        # Add the save template button to the right
        nav_layout.addWidget(save_template_btn)
        
        layout.addLayout(nav_layout)

        if self.is_multi_page:
            # Add page navigation
            nav_layout = QHBoxLayout()
            self.prev_page_btn = QPushButton("← Previous Page")
            self.next_page_btn = QPushButton("Next Page →")
            self.page_label = QLabel("Page 1")
            
            self.prev_page_btn.clicked.connect(self.prev_page)
            self.next_page_btn.clicked.connect(self.next_page)
            
            nav_layout.addWidget(self.prev_page_btn)
            nav_layout.addWidget(self.page_label)
            nav_layout.addWidget(self.next_page_btn)
            layout.addLayout(nav_layout)
        
        self.setLayout(layout)

    def load_pdf(self):
        if not self.pdf_path:
            return
            
        # Open the PDF
        self.pdf_document = fitz.open(self.pdf_path)
        
        # Get the first page
        page = self.pdf_document[0]
            
        # Render the page
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        
        # Convert PyMuPDF pixmap to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Convert PIL Image to QPixmap
        bytes_io = io.BytesIO()
        img.save(bytes_io, format='PNG')
        qimg = QImage.fromData(bytes_io.getvalue())
        self.original_pixmap = QPixmap.fromImage(qimg)
        
        # Create a copy for drawing
        self.drawing_pixmap = self.original_pixmap.copy()
        
        # Draw sections
        self.draw_sections()
        
        # Display the result
        self.pdf_label.setPixmap(self.drawing_pixmap)
        
        # Extract and update data for current section
        self.extract_and_update_section_data()

    def draw_sections(self):
        """Draw the sections on the PDF view"""
        try:
            print("\n=== Drawing sections ===")
            if not hasattr(self, 'drawing_pixmap') or self.drawing_pixmap is None:
                print("No drawing pixmap available")
                return
                
            # Create a copy of the original pixmap for drawing
            self.drawing_pixmap = self.original_pixmap.copy()
            painter = QPainter(self.drawing_pixmap)
            
            # Define section names and colors
            sections = ['header', 'items', 'summary']
            colors = {
                'header': QColor(52, 152, 219),  # Blue
                'items': QColor(46, 204, 113),   # Green
                'summary': QColor(155, 89, 182)  # Purple
            }
            
            # Draw each section
            for section in sections:
                if section in self.regions and self.regions[section]:
                    print(f"Drawing {section} section")
                    color = colors[section]
                    pen = QPen(color, 2, Qt.SolidLine)
                    painter.setPen(pen)
                    
                    # Draw each region for this section
                    for i, rect in enumerate(self.regions[section]):
                        # Draw the rectangle
                        painter.drawRect(rect)
                        
                        # Add section label
                        painter.setPen(Qt.black)
                        font = QFont("Arial", 10, QFont.Bold)
                        painter.setFont(font)
                        label = f"{section[0].upper()}{i+1}"  # H1, I1, S1, etc.
                        painter.drawText(rect.topLeft() + QPoint(5, 20), label)
            
            # End painting and update the PDF label
            painter.end()
            self.pdf_label.setPixmap(self.drawing_pixmap)
            print("Sections drawn successfully")
            
        except Exception as e:
            print(f"\nError in draw_sections: {str(e)}")
            import traceback
            traceback.print_exc()

    def extract_and_update_section_data(self):
        sections = ['header', 'items', 'summary']
        if 0 <= self.current_page < len(sections):
            section = sections[self.current_page]
            if section in self.regions and self.regions[section]:
                try:
                    # Get page height to convert coordinates
                    page = self.pdf_document[0]
                    # Get actual page dimensions in points (1/72 inch)
                    page_width = page.mediabox.width
                    page_height = page.mediabox.height
                    print(f"Actual PDF dimensions: width={page_width} points, height={page_height} points")
                    
                    # Get the rendered dimensions
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    rendered_width = pix.width
                    rendered_height = pix.height
                    print(f"Rendered dimensions: width={rendered_width}, height={rendered_height}")
                    
                    # Calculate scaling factors
                    scale_x = page_width / rendered_width
                    scale_y = page_height / rendered_height
                    print(f"Scaling factors: x={scale_x}, y={scale_y}")
                    
                    # Prepare table areas and column lines based on section
                    table_areas = []
                    column_lines = []
                    
                    # Handle multiple tables for header section
                    if section == 'header':
                        # Print a separator for clarity
                        print("\n" + "="*50)
                        print("EXTRACTING HEADER TABLES")
                        print("="*50)
                        
                        # Process all header regions in their original order
                        print(f"\nHeader regions in original drawing order:")
                        for idx, rect in enumerate(self.regions[section]):
                            print(f"  Header {idx}: top={rect.top()}, left={rect.left()}, width={rect.width()}, height={rect.height()}")
                        
                        # Process each header region in the original order it was drawn
                        for idx, rect in enumerate(self.regions[section]):
                            print(f"\nProcessing header region {idx}:")
                            print(f"  Position: top={rect.top()}, left={rect.left()}, width={rect.width()}, height={rect.height()}")
                            
                            # Convert rectangle coordinates to PDF space with proper scaling
                            x1 = rect.x() * scale_x
                            y1 = page_height - (rect.y() * scale_y)
                            x2 = (rect.x() + rect.width()) * scale_x
                            y2 = page_height - ((rect.y() + rect.height()) * scale_y)
                            
                            table_area = f"{x1},{y1},{x2},{y2}"
                            table_areas.append(table_area)
                            print(f"  Table area: {table_area}")
                            
                            # Find column lines specific to this region
                            region_columns = []
                            if section in self.column_lines and self.column_lines[section]:
                                print(f"  Looking for column lines for region {idx}:")
                                for line in self.column_lines[section]:
                                    # Check if the line has a region index and matches current region
                                    if len(line) == 3 and line[2] == idx:
                                        region_columns.append(line[0].x() * scale_x)
                                        print(f"    Found line at x={line[0].x()} with rect_index={line[2]}")
                                    # Handle old format without region index - associate with first region
                                    elif len(line) == 2 and idx == 0:
                                        region_columns.append(line[0].x() * scale_x)
                                        print(f"    Found line at x={line[0].x()} (old format, associated with first table)")
                            
                            if region_columns:
                                # Sort column lines by x-coordinate and join as comma-separated string
                                col_str = ','.join([str(x) for x in sorted(region_columns)])
                                column_lines.append(col_str)
                                print(f"  Final column lines: {col_str}")
                            else:
                                # Empty string for regions with no column lines
                                column_lines.append('')
                        
                        print(f"\nHeader table areas: {table_areas}")
                        print(f"Header column lines: {column_lines}")
                        print("="*50)
                        
                        # Define extraction parameters - set header row_tol to 5
                        extraction_params = {
                            'row_tol': 5,  # Set header row_tol to 5
                            'split_text': True,
                            'strip_text': '\n',
                            'flavor': 'stream'
                        }
                        
                        # Store the extraction parameters for potential template saving
                        if not hasattr(self, 'extraction_params'):
                            self.extraction_params = {'header': {}, 'items': {}, 'summary': {}}
                        
                        self.extraction_params['header']['row_tol'] = extraction_params['row_tol']
                        self.extraction_params['split_text'] = extraction_params['split_text']
                        self.extraction_params['strip_text'] = extraction_params['strip_text']
                        self.extraction_params['flavor'] = extraction_params['flavor']
                        
                        # For header tables, extract each table separately to preserve order
                        processed_tables = []
                        
                        for idx, (table_area, col_line) in enumerate(zip(table_areas, column_lines)):
                            print(f"\nExtracting Header Table {idx + 1} individually:")
                            try:
                                # Parameters for this single table
                                single_table_params = {
                                    'pages': '1',
                                    'table_areas': [table_area],
                                    'columns': [col_line] if col_line else None,
                                    'split_text': extraction_params['split_text'],
                                    'strip_text': extraction_params['strip_text'],
                                    'flavor': extraction_params['flavor'],
                                    'row_tol': extraction_params['row_tol']
                                }
                                
                                # Extract just this table
                                table_result = pypdf_table_extraction.read_pdf(self.pdf_path, **single_table_params)
                                
                                if table_result and len(table_result) > 0 and table_result[0].df is not None:
                                    table_df = table_result[0].df
                                    
                                    # Clean up the DataFrame
                                    table_df = table_df.replace(r'^\s*$', pd.NA, regex=True)
                                    table_df = table_df.dropna(how='all')
                                    table_df = table_df.dropna(axis=1, how='all')
                                    
                                    if not table_df.empty:
                                        print(f"  Successfully extracted table with {len(table_df)} rows and {len(table_df.columns)} columns")
                                        processed_tables.append(table_df)
                                    else:
                                        print(f"  No valid data found after cleaning")
                                else:
                                    print(f"  No data extracted from table area")
                            except Exception as e:
                                print(f"  Error extracting table: {str(e)}")
                        
                        # Update the display with tables in the correct order
                        if processed_tables:
                            print(f"\nSuccessfully processed {len(processed_tables)} header tables in original drawing order")
                            self.header_df = processed_tables
                            self.update_data_table_for_header(processed_tables, section_type=section)
                        else:
                            print("No valid header tables found")
                            self.update_data_table(None, section)
                    else:
                        # For items and summary sections
                        # Print a separator for clarity
                        print(f"\n{'='*50}")
                        print(f"EXTRACTING {section.upper()} TABLES")
                        print(f"{'='*50}")
                        
                        # Process all regions in their original order
                        print(f"\n{section.title()} regions in original drawing order:")
                        for idx, rect in enumerate(self.regions[section]):
                            print(f"  {section.title()} {idx}: top={rect.top()}, left={rect.left()}, width={rect.width()}, height={rect.height()}")
                        
                        # Process each region in the original order
                        table_areas = []
                        column_lines = []
                        
                        for idx, rect in enumerate(self.regions[section]):
                            print(f"\nProcessing {section} region {idx}:")
                            print(f"  Position: top={rect.top()}, left={rect.left()}, width={rect.width()}, height={rect.height()}")
                            
                            # Convert rectangle coordinates to PDF space with proper scaling
                            x1 = rect.x() * scale_x
                            y1 = page_height - (rect.y() * scale_y)
                            x2 = (rect.x() + rect.width()) * scale_x
                            y2 = page_height - ((rect.y() + rect.height()) * scale_y)
                            
                            table_area = f"{x1},{y1},{x2},{y2}"
                            table_areas.append(table_area)
                            print(f"  Table area: {table_area}")
                            
                            # Find column lines specific to this region
                            region_columns = []
                            if section in self.column_lines and self.column_lines[section]:
                                print(f"  Looking for column lines for region {idx}:")
                                for line in self.column_lines[section]:
                                    # Check if the line has a region index and matches current region
                                    if len(line) == 3 and line[2] == idx:
                                        region_columns.append(line[0].x() * scale_x)
                                        print(f"    Found line at x={line[0].x()} with rect_index={line[2]}")
                                    # Handle old format without region index - associate with first region
                                    elif len(line) == 2 and idx == 0:
                                        region_columns.append(line[0].x() * scale_x)
                                        print(f"    Found line at x={line[0].x()} (old format, associated with first table)")
                            
                            if region_columns:
                                # Sort column lines by x-coordinate and join as comma-separated string
                                col_str = ','.join([str(x) for x in sorted(region_columns)])
                                column_lines.append(col_str)
                                print(f"  Final column lines: {col_str}")
                            else:
                                # Empty string for regions with no column lines
                                column_lines.append('')
                        
                        print(f"\n{section.title()} table areas: {table_areas}")
                        print(f"{section.title()} column lines: {column_lines}")
                        print("="*50)
                        
                        # Set specific extraction parameters based on section
                        extraction_params = {
                            'row_tol': 15 if section == 'items' else 10,  # 15 for items, 10 for summary
                            'split_text': True,
                            'strip_text': '\n',
                            'flavor': 'stream'
                        }
                        
                        # Store the extraction parameters for potential template saving
                        if not hasattr(self, 'extraction_params'):
                            self.extraction_params = {'header': {}, 'items': {}, 'summary': {}}
                            
                        # Initialize all section parameters if not already done
                        if 'header' not in self.extraction_params:
                            self.extraction_params['header'] = {'row_tol': 5}  # Default for header
                        if 'items' not in self.extraction_params:
                            self.extraction_params['items'] = {'row_tol': 15}  # Default for items
                        if 'summary' not in self.extraction_params:
                            self.extraction_params['summary'] = {'row_tol': 10}  # Default for summary
                            
                        # Update the current section's parameters
                        self.extraction_params[section]['row_tol'] = extraction_params['row_tol']
                        self.extraction_params['split_text'] = extraction_params['split_text']
                        self.extraction_params['strip_text'] = extraction_params['strip_text']
                        self.extraction_params['flavor'] = extraction_params['flavor']
                        
                        # Check if we have multiple tables for this section
                        if len(table_areas) > 1:
                            # Extract each table separately to preserve order (similar to header approach)
                            processed_tables = []
                            
                            for idx, (table_area, col_line) in enumerate(zip(table_areas, column_lines)):
                                print(f"\nExtracting {section.title()} Table {idx + 1} individually:")
                                try:
                                    # Parameters for this single table
                                    single_table_params = {
                                        'pages': '1',
                                        'table_areas': [table_area],
                                        'columns': [col_line] if col_line else None,
                                        'split_text': extraction_params['split_text'],
                                        'strip_text': extraction_params['strip_text'],
                                        'flavor': extraction_params['flavor'],
                                        'row_tol': extraction_params['row_tol']
                                    }
                                    
                                    # Extract just this table
                                    table_result = pypdf_table_extraction.read_pdf(self.pdf_path, **single_table_params)
                                    
                                    if table_result and len(table_result) > 0 and table_result[0].df is not None:
                                        table_df = table_result[0].df
                                        
                                        print(f"  Raw data extracted for {section.title()} Table {idx + 1}:")
                                        print(table_df)
                                        
                                        # Clean up the DataFrame
                                        table_df = table_df.replace(r'^\s*$', pd.NA, regex=True)
                                        table_df = table_df.dropna(how='all')
                                        table_df = table_df.dropna(axis=1, how='all')
                                        
                                        # Format columns if needed (especially for summary)
                                        if all(isinstance(col, int) for col in table_df.columns):
                                            if len(table_df.columns) == 2:  # If it has 2 columns (label and value)
                                                # Convert to a proper key-value format
                                                new_df = pd.DataFrame({
                                                    'Item': table_df[0].values,
                                                    'Value': table_df[1].values
                                                })
                                                table_df = new_df
                                                print(f"  Reformatted table with named columns")
                                        
                                        if not table_df.empty:
                                            print(f"  Successfully extracted table with {len(table_df)} rows and {len(table_df.columns)} columns")
                                            processed_tables.append(table_df)
                                        else:
                                            print(f"  No valid data found after cleaning")
                                    else:
                                        print(f"  No data extracted from table area")
                                except Exception as e:
                                    print(f"  Error extracting table: {str(e)}")
                            
                            # Update the display with tables in the correct order
                            if processed_tables:
                                print(f"\nSuccessfully processed {len(processed_tables)} {section} tables in original drawing order")
                                
                                # Update the appropriate dataframe attribute and display
                                if section == 'items':
                                    self.item_details_df = processed_tables
                                    self.update_data_table_for_header(processed_tables, section_type=section)
                                elif section == 'summary':
                                    self.summary_df = processed_tables
                                    self.update_data_table_for_header(processed_tables, section_type=section)
                            else:
                                print(f"No valid {section} tables found")
                                # Update the display with empty data
                                self.update_data_table(None, section)
                        else:
                            # For single table
                            single_table_params = {
                                'pages': '1',
                                'table_areas': table_areas,
                                'columns': column_lines if column_lines else None,
                                'split_text': extraction_params['split_text'],
                                'strip_text': extraction_params['strip_text'],
                                'flavor': extraction_params['flavor'],
                                'row_tol': extraction_params['row_tol']
                            }
                            
                            print(f"\nExtracting single {section} table:")
                            print(f"  Parameters: {single_table_params}")
                            
                            # Extract data
                            tables = pypdf_table_extraction.read_pdf(self.pdf_path, **single_table_params)
                            
                            if tables and len(tables) > 0 and tables[0].df is not None:
                                df = tables[0].df
                                
                                # Special logging for summary section
                                if section == 'summary':
                                    print("\n=== SUMMARY SECTION SPECIAL DEBUG ===")
                                    print(f"Summary table column names: {df.columns.tolist()}")
                                    print(f"Summary table shape: {df.shape}")
                                
                                print(f"\nRaw extracted data for {section}:")
                                print(df)
                                
                                # Format columns if needed
                                if all(isinstance(col, int) for col in df.columns):
                                    if len(df.columns) == 2:  # If it has 2 columns (label and value)
                                        # Convert to a proper key-value format
                                        new_df = pd.DataFrame({
                                            'Item': df[0].values,
                                            'Value': df[1].values
                                        })
                                        df = new_df
                                        print("\nDataFrame reformatted with named columns:")
                                        print(df)
                                
                                # Clean up the DataFrame
                                df = df.replace(r'^\s*$', pd.NA, regex=True)  # Replace empty strings with NA
                                df = df.dropna(how='all')  # Drop rows that are all NA
                                df = df.dropna(axis=1, how='all')  # Drop columns that are all NA
                                
                                if not df.empty:
                                    print(f"\nSuccessfully extracted {section} data")
                                    print(f"Final DataFrame shape: {df.shape}")
                                    
                                    # Update the appropriate dataframe attribute and display
                                    if section == 'items':
                                        self.item_details_df = df
                                    elif section == 'summary':
                                        self.summary_df = df
                                    
                                    # Update display
                                    self.update_data_table(df, section)
                                else:
                                    print(f"\nNo valid data found in {section} section after cleaning")
                                    self.update_data_table(None, section)
                            else:
                                print(f"\nNo data found in {section} section")
                                self.update_data_table(None, section)
                except Exception as e:
                    print(f"\nError extracting {section} data: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    self.update_data_table(None, section)
            else:
                # If we're on the header section and we have a pre-loaded header_df (passed from main),
                # use that instead of extracting it
                if section == 'header' and self.header_df is not None:
                    # Check if header_df is a list of DataFrames (new format) or a single DataFrame (old format)
                    if isinstance(self.header_df, list):
                        print("Using pre-loaded header tables (list format)")
                        self.update_data_table_for_header(self.header_df, section_type=section)
                    else:
                        print("Using pre-loaded header table (single DataFrame format)")
                        self.update_data_table(self.header_df, section)
                elif section == 'items' and self.item_details_df is not None:
                    # Check if item_details_df is a list of DataFrames (new format) or a single DataFrame (old format)
                    if isinstance(self.item_details_df, list):
                        print("Using pre-loaded items tables (list format)")
                        self.update_data_table_for_header(self.item_details_df, section_type=section)
                    else:
                        print("Using pre-loaded items table (single DataFrame format)")
                        self.update_data_table(self.item_details_df, section)
                elif section == 'summary' and self.summary_df is not None:
                    # Check if summary_df is a list of DataFrames (new format) or a single DataFrame (old format)
                    if isinstance(self.summary_df, list):
                        print("Using pre-loaded summary tables (list format)")
                        self.update_data_table_for_header(self.summary_df, section_type=section)
                    else:
                        print("Using pre-loaded summary table (single DataFrame format)")
                        self.update_data_table(self.summary_df, section)
                else:
                    self.update_data_table(None, section)
                    
        # Initialize extraction_params if this is our first time
        if not hasattr(self, 'extraction_params'):
            self.extraction_params = {
                'header': {'row_tol': 5},    # Default for header
                'items': {'row_tol': 15},    # Default for items
                'summary': {'row_tol': 10},  # Default for summary
                'split_text': True,
                'strip_text': '\n',
                'flavor': 'stream',
                'regex_patterns': {          # Initialize empty regex patterns structure
                    'header': {},
                    'items': {},
                    'summary': {}
                }
            }
            print("\nInitialized default extraction parameters:")
            print(f"  Header row_tol: {self.extraction_params['header']['row_tol']}")
            print(f"  Items row_tol: {self.extraction_params['items']['row_tol']}")
            print(f"  Summary row_tol: {self.extraction_params['summary']['row_tol']}")
        else:
            # Make sure all section parameters exist with proper defaults
            if 'header' not in self.extraction_params:
                self.extraction_params['header'] = {}
            if 'items' not in self.extraction_params:
                self.extraction_params['items'] = {}
            if 'summary' not in self.extraction_params:
                self.extraction_params['summary'] = {}
            
            # Set default row_tol values if not already set
            if 'row_tol' not in self.extraction_params['header']:
                self.extraction_params['header']['row_tol'] = 5
            if 'row_tol' not in self.extraction_params['items']:
                self.extraction_params['items']['row_tol'] = 15
            if 'row_tol' not in self.extraction_params['summary']:
                self.extraction_params['summary']['row_tol'] = 10
            
            # Make sure global parameters exist
            if 'split_text' not in self.extraction_params:
                self.extraction_params['split_text'] = True
            if 'strip_text' not in self.extraction_params:
                self.extraction_params['strip_text'] = '\n'
            if 'flavor' not in self.extraction_params:
                self.extraction_params['flavor'] = 'stream'
            
            # Make sure regex_patterns structure exists
            if 'regex_patterns' not in self.extraction_params:
                self.extraction_params['regex_patterns'] = {
                    'header': {},
                    'items': {},
                    'summary': {}
                }
            else:
                # Ensure all section keys exist in regex_patterns
                for section in ['header', 'items', 'summary']:
                    if section not in self.extraction_params['regex_patterns']:
                        self.extraction_params['regex_patterns'][section] = {}

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
                self.section_title.setText("Header Section")
                
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

    def next_section(self):
        self.current_page = (self.current_page + 1) % 3
        self.load_pdf()

    def prev_section(self):
        self.current_page = (self.current_page - 1) % 3
        self.load_pdf()

    def go_back(self):
        """Return to the main screen instead of the previous screen to maintain proper navigation flow"""
        print("[DEBUG] go_back method called in InvoiceSectionViewer")
        
        # Get the main window
        main_window = self.window()
        if main_window:
            print("[DEBUG] Found main window")
            stacked_widget = main_window.findChild(QStackedWidget)
            if stacked_widget:
                print("[DEBUG] Found stacked widget")
                # Instead of returning to the previous screen, always return to the main screen
                # This avoids issues with destroyed screens and maintains signal connections
                try:
                    # Try to access the main screen (should be at index 0)
                    main_screen = stacked_widget.widget(0)
                    if main_screen:
                        print("[DEBUG] Setting current widget to main screen")
                        stacked_widget.setCurrentWidget(main_screen)
                    else:
                        # If we can't access the main screen directly, go to the first available screen
                        print("[DEBUG] Main screen not found, going to first screen")
                        stacked_widget.setCurrentIndex(0)
                except Exception as e:
                    print(f"[ERROR] Error navigating back: {str(e)}")
                    # Fall back to previous behavior if the above fails
                    current_index = stacked_widget.currentIndex()
                    if current_index > 0:  # Make sure we're not at the first screen
                        stacked_widget.setCurrentIndex(current_index - 1)
            else:
                print("[ERROR] Could not find stacked widget")
        else:
            print("[ERROR] Could not find main window")

    def save_template(self):
        """Signal to the main application to show the template saving screen"""
        print("\n[DEBUG] save_template method called in InvoiceSectionViewer")
        
        try:
            # Import necessary modules
            from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QTextEdit, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox
            from PySide6.QtCore import Qt
            from PySide6.QtGui import QFont
            from database import InvoiceDatabase
            
            # Create dialog for template info
            dialog = QDialog(self)
            dialog.setWindowTitle("Save Invoice Template")
            dialog.setMinimumWidth(450)
            
            # Set global style for this dialog
            dialog.setStyleSheet("""
                QDialog {
                    background-color: white;
                }
                QLabel {
                    color: black;
                }
                QLineEdit, QTextEdit {
                    color: black;
                    background-color: white;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    padding: 5px;
                }
                QFormLayout QLabel {
                    color: black;
                    font-weight: bold;
                }
            """)
            
            layout = QVBoxLayout()
            layout.setSpacing(16)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # Add header/title
            header_label = QLabel("Template Information")
            header_label.setFont(QFont("Arial", 14, QFont.Bold))
            header_label.setStyleSheet("color: #333;")
            layout.addWidget(header_label)
            
            # Add description
            description_label = QLabel("Fill in the details to save your invoice template for future use.")
            description_label.setWordWrap(True)
            description_label.setStyleSheet("color: #666; margin-bottom: 10px;")
            layout.addWidget(description_label)
            
            form_layout = QFormLayout()
            form_layout.setSpacing(12)
            
            # Explicitly set label styling for form fields
            name_label = QLabel("Template Name:")
            name_label.setStyleSheet("color: black; font-weight: bold;")
            
            desc_label = QLabel("Description:")
            desc_label.setStyleSheet("color: black; font-weight: bold;")
            
            name_input = QLineEdit()
            name_input.setPlaceholderText("Enter a descriptive name for your template")
            name_input.setStyleSheet("color: black; background-color: white;")
            
            description_input = QTextEdit()
            description_input.setPlaceholderText("Describe the purpose or usage of this template (optional)")
            description_input.setMinimumHeight(100)
            description_input.setStyleSheet("color: black; background-color: white;")
            
            form_layout.addRow(name_label, name_input)
            form_layout.addRow(desc_label, description_input)
            
            layout.addLayout(form_layout)
            
            # Buttons
            buttons_layout = QHBoxLayout()
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.reject)
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f8f9fa;
                    color: #212529;
                    padding: 10px 20px;
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                    font-weight: normal;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                    color: black;
                }
            """)
            
            save_btn = QPushButton("Save Template")
            save_btn.clicked.connect(dialog.accept)
            save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4169E1;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #3158D3;
                    color: white;
                }
            """)
            save_btn.setDefault(True)
            
            buttons_layout.addStretch(1)
            buttons_layout.addWidget(cancel_btn)
            buttons_layout.addWidget(save_btn)
            
            layout.addLayout(buttons_layout)
            
            dialog.setLayout(layout)
            
            # Show dialog and get result
            if dialog.exec() == QDialog.Accepted:
                # Get template info
                template_name = name_input.text().strip()
                template_description = description_input.toPlainText().strip()
                
                if not template_name:
                    QMessageBox.warning(self, "Invalid Name", "Please provide a valid template name.")
                    return
                
                # Save the template directly
                self.save_template_directly(template_name, template_description)
            
        except Exception as e:
            print(f"[ERROR] Failed in save_template method: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Show error message to user if signal emission fails
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Error")
            msg.setText("Cannot save template")
            msg.setInformativeText(f"An error occurred: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()

    def save_template_directly(self, name, description):
        """Save the template directly to the database with actual parameters"""
        try:
            from database import InvoiceDatabase
            from PySide6.QtWidgets import QMessageBox, QApplication, QStackedWidget
            import os
            
            # Open database connection
            db = InvoiceDatabase()
            
            # Get the regions and column lines
            regions = self.regions
            column_lines = self.column_lines
            multi_table_mode = getattr(self, 'multi_table_mode', False)
            
            # Convert QRect objects to dictionaries for JSON serialization
            serializable_regions = {}
            for section, rects in regions.items():
                serializable_regions[section] = []
                for rect in rects:
                    # Get page dimensions for coordinate conversion
                    page = self.pdf_document[0]  # For single page
                    page_width = page.mediabox.width
                    page_height = page.mediabox.height
                    
                    # Get rendered dimensions
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    rendered_width = pix.width
                    rendered_height = pix.height
                    
                    # Calculate scaling factors
                    scale_x = page_width / rendered_width
                    scale_y = page_height / rendered_height
                    
                    # Convert QRect to bottom-left coordinate system
                    # In bottom-left system, y coordinates are measured from bottom up
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
            
            # Convert column lines to serializable format with scaled coordinates
            serializable_column_lines = {}
            for section, lines in column_lines.items():
                serializable_column_lines[section] = []
                for line in lines:
                    try:
                        # Convert line coordinates to bottom-left system with scaling
                        line_data = [
                            {
                                'x': line[0].x() * scale_x,
                                'y': page_height - (line[0].y() * scale_y)  # Convert to bottom-left
                            },
                            {
                                'x': line[1].x() * scale_x,
                                'y': page_height - (line[1].y() * scale_y)  # Convert to bottom-left
                            }
                        ]
                        if len(line) > 2:
                            line_data.append(line[2])  # Add region index if present
                        serializable_column_lines[section].append(line_data)
                    except Exception as e:
                        print(f"Warning: Error converting column line in section {section}: {str(e)}")
                        continue
                
            # Create the configuration object
            config = {
                "multi_table_mode": multi_table_mode
            }
            
            # Ensure we have extraction_params with proper default values if not set elsewhere
            if not hasattr(self, 'extraction_params'):
                print("\nInitializing default extraction parameters for template saving:")
                self.extraction_params = {
                    'header': {'row_tol': 5},    # Default for header
                    'items': {'row_tol': 15},    # Default for items
                    'summary': {'row_tol': 10},  # Default for summary
                    'split_text': True,
                    'strip_text': '\n',
                    'flavor': 'stream',
                    'regex_patterns': {          # Initialize empty regex patterns structure
                        'header': {},
                        'items': {},
                        'summary': {}
                    }
                }
                print(f"  Header row_tol: {self.extraction_params['header']['row_tol']}")
                print(f"  Items row_tol: {self.extraction_params['items']['row_tol']}")
                print(f"  Summary row_tol: {self.extraction_params['summary']['row_tol']}")
                
                # Try to get extraction params from main window as a fallback
                try:
                    from PySide6.QtWidgets import QApplication
                    from main import PDFHarvest
                    
                    for widget in QApplication.topLevelWidgets():
                        if isinstance(widget, PDFHarvest) and hasattr(widget, 'latest_extraction_params'):
                            latest_params = widget.latest_extraction_params
                            print("Found latest extraction parameters in main window, incorporating them")
                            
                            # Update section-specific parameters if they exist
                            for section in ['header', 'items', 'summary']:
                                if section in latest_params and 'row_tol' in latest_params[section]:
                                    self.extraction_params[section]['row_tol'] = latest_params[section]['row_tol']
                                    print(f"  Updated {section} row_tol to {latest_params[section]['row_tol']}")
                            
                            # Update global parameters if they exist
                            if 'split_text' in latest_params:
                                self.extraction_params['split_text'] = latest_params['split_text']
                            if 'strip_text' in latest_params:
                                self.extraction_params['strip_text'] = latest_params['strip_text']
                            
                            # Merge regex patterns if they exist
                            if 'regex_patterns' in latest_params:
                                print("  Found regex patterns in main window:")
                                for section, patterns in latest_params['regex_patterns'].items():
                                    if section in self.extraction_params['regex_patterns'] and patterns:
                                        for p_type, pattern in patterns.items():
                                            self.extraction_params['regex_patterns'][section][p_type] = pattern
                                            print(f"    Added {section} {p_type} pattern: {pattern}")
                            
                            break
                except Exception as e:
                    print(f"Could not get latest extraction params from main window: {str(e)}")
            else:
                # Make sure all section parameters exist with proper defaults
                if 'header' not in self.extraction_params:
                    self.extraction_params['header'] = {}
                if 'items' not in self.extraction_params:
                    self.extraction_params['items'] = {}
                if 'summary' not in self.extraction_params:
                    self.extraction_params['summary'] = {}
                
                # Set default row_tol values if not already set
                if 'row_tol' not in self.extraction_params['header']:
                    self.extraction_params['header']['row_tol'] = 5
                if 'row_tol' not in self.extraction_params['items']:
                    self.extraction_params['items']['row_tol'] = 15
                if 'row_tol' not in self.extraction_params['summary']:
                    self.extraction_params['summary']['row_tol'] = 10
                
                # Make sure global parameters exist
                if 'split_text' not in self.extraction_params:
                    self.extraction_params['split_text'] = True
                if 'strip_text' not in self.extraction_params:
                    self.extraction_params['strip_text'] = '\n'
                if 'flavor' not in self.extraction_params:
                    self.extraction_params['flavor'] = 'stream'
                
                # Make sure regex_patterns structure exists
                if 'regex_patterns' not in self.extraction_params:
                    self.extraction_params['regex_patterns'] = {
                        'header': {},
                        'items': {},
                        'summary': {}
                    }
                    
                    # Try to get regex patterns from main window as a fallback
                    try:
                        from PySide6.QtWidgets import QApplication
                        from main import PDFHarvest
                        
                        for widget in QApplication.topLevelWidgets():
                            if isinstance(widget, PDFHarvest) and hasattr(widget, 'latest_extraction_params'):
                                latest_params = widget.latest_extraction_params
                                
                                # Merge regex patterns if they exist
                                if 'regex_patterns' in latest_params:
                                    print("Found regex patterns in main window, incorporating them:")
                                    for section, patterns in latest_params['regex_patterns'].items():
                                        if patterns:
                                            for p_type, pattern in patterns.items():
                                                self.extraction_params['regex_patterns'][section][p_type] = pattern
                                                print(f"  Added {section} {p_type} pattern: {pattern}")
                                
                                break
                    except Exception as e:
                        print(f"Could not get regex patterns from main window: {str(e)}")
                else:
                    # Ensure all section keys exist in regex_patterns
                    for section in ['header', 'items', 'summary']:
                        if section not in self.extraction_params['regex_patterns']:
                            self.extraction_params['regex_patterns'][section] = {}
            
            # Add extraction parameters to config
            config['extraction_params'] = self.extraction_params
            
            print(f"\nFinal extraction parameters being saved to template:")
            for section in ['header', 'items', 'summary']:
                print(f"  {section.title()} row_tol: {self.extraction_params[section]['row_tol']}")
            
            print(f"  split_text: {self.extraction_params['split_text']}")
            print(f"  strip_text: {repr(self.extraction_params['strip_text'])}")
            print(f"  flavor: {self.extraction_params['flavor']}")
            
            # Print regex patterns if they exist
            if 'regex_patterns' in self.extraction_params:
                print("\nRegex patterns being saved to template:")
                for section, patterns in self.extraction_params['regex_patterns'].items():
                    if patterns:
                        print(f"  {section.title()} patterns:")
                        for pattern_type, pattern in patterns.items():
                            print(f"    {pattern_type}: {pattern}")
            
            # Save template to the database
            template_id = db.save_template(
                name=name,
                description=description,
                regions=serializable_regions,  # Now using properly scaled and converted coordinates
                column_lines=serializable_column_lines,  # Now using properly scaled and converted coordinates
                config=self.extraction_params,
                template_type="single",
                page_count=1
            )
            
            # Set this as the current template in the main window
            self.current_template_id = template_id
            
            # Try to also set it in the main window if available
            try:
                from PySide6.QtWidgets import QApplication
                from main import PDFHarvest
                
                for widget in QApplication.topLevelWidgets():
                    if isinstance(widget, PDFHarvest):
                        widget.current_template_id = template_id
                        break
            except Exception as e:
                print(f"Could not set template ID in main window: {str(e)}")
            
            # Show a brief success message
            brief_msg = QMessageBox(self)
            brief_msg.setWindowTitle("Template Saved")
            brief_msg.setText("Template saved successfully!")
            brief_msg.setInformativeText(f"Template '{name}' has been saved. Navigating to Template Manager...")
            brief_msg.setIcon(QMessageBox.Information)
            brief_msg.setStyleSheet("QLabel { color: black; }")
            brief_msg.setStandardButtons(QMessageBox.Ok)
            brief_msg.exec()
            
            # Close database connection
            db.close()
            
            # Navigate to template manager screen
            self.navigate_to_template_manager()
            
        except Exception as e:
            print(f"[ERROR] Failed to save template directly: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Show error message
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText("Failed to save template")
            msg_box.setInformativeText(f"An error occurred: {str(e)}")
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setStyleSheet("QLabel { color: black; }")
            msg_box.exec()
    
    def navigate_to_template_manager(self):
        """Navigate to the template manager screen"""
        try:
            from PySide6.QtWidgets import QApplication, QStackedWidget
            import logging
            
            print("\n[DEBUG] Attempting to navigate to template manager")
            
            # Method 1: Try to find main window via direct parent hierarchy
            main_window = self.window()
            if main_window:
                print("[DEBUG] Found main window via window() method")
            else:
                # Method 2: Try searching among top-level widgets
                for widget in QApplication.topLevelWidgets():
                    # Check if it has a stacked widget child - a good hint it's our main window
                    stacked_widget = widget.findChild(QStackedWidget)
                    if stacked_widget:
                        main_window = widget
                        print("[DEBUG] Found main window by searching top-level widgets")
                        break
            
            if not main_window:
                # Method 3: Last resort - use our current parent widget
                main_window = self.parent()
                while main_window and not main_window.findChild(QStackedWidget):
                    main_window = main_window.parent()
                
                if main_window:
                    print("[DEBUG] Found main window by walking up parent hierarchy")
                else:
                    print("[ERROR] Could not find main window - using workaround")
                    # Fallback method: Look for our own widget in the stack
                    self_parent = self.parent()
                    if isinstance(self_parent, QStackedWidget):
                        # We're directly in a stacked widget
                        stacked_widget = self_parent
                        print("[DEBUG] We're directly in a stacked widget - using that")
                    else:
                        print("[ERROR] No viable parent found, cannot navigate")
                        return
            
            # Find the stacked widget if we found the main window
            stacked_widget = None
            if main_window:
                stacked_widget = main_window.findChild(QStackedWidget)
                if stacked_widget:
                    print(f"[DEBUG] Found stacked widget with {stacked_widget.count()} screens")
                else:
                    print("[ERROR] No stacked widget found in main window")
                    return
            
            if stacked_widget:
                # Approach 1: Search for the template manager by checking each widget's methods
                template_manager_index = -1
                for i in range(stacked_widget.count()):
                    widget = stacked_widget.widget(i)
                    if hasattr(widget, 'load_templates'):  # A method unique to TemplateManager
                        template_manager_index = i
                        print(f"[DEBUG] Found template manager at index {i}")
                        break
                
                # Approach 2: If method 1 fails, look for widget with the right class name
                if template_manager_index == -1:
                    for i in range(stacked_widget.count()):
                        widget = stacked_widget.widget(i)
                        class_name = widget.__class__.__name__
                        if class_name == "TemplateManager" or "template_manager" in class_name.lower():
                            template_manager_index = i
                            print(f"[DEBUG] Found template manager by class name at index {i}")
                            break
                
                # Navigate if we found the template manager
                if template_manager_index >= 0:
                    # Try to refresh the template list before showing
                    template_manager = stacked_widget.widget(template_manager_index)
                    try:
                        if hasattr(template_manager, 'load_templates'):
                            template_manager.load_templates()
                            print("[DEBUG] Successfully refreshed template list")
                        else:
                            print("[WARNING] Template manager doesn't have load_templates method")
                    except Exception as refresh_error:
                        print(f"[WARNING] Error refreshing template list: {str(refresh_error)}")
                    
                    # Navigate to the template manager screen
                    stacked_widget.setCurrentIndex(template_manager_index)
                    print(f"[DEBUG] Successfully navigated to template manager at index {template_manager_index}")
                else:
                    print("[ERROR] Could not find template manager in the stacked widget")
            else:
                print("[ERROR] No stacked widget available")
                
        except Exception as e:
            print(f"[ERROR] Failed to navigate to template manager: {str(e)}")
            import traceback
            traceback.print_exc()

    def create_styled_messagebox(self, title, text, informative_text, detailed_text=None):
        """Create a styled QMessageBox with white text on dark background"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setInformativeText(informative_text)
        
        if detailed_text:
            msg.setDetailedText(detailed_text)
            
        # Apply styling for better visibility of text
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2c3e50;
                color: white;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QTextEdit {
                background-color: #34495e;
                color: white;
                border: 1px solid #3498db;
            }
        """)
        
        return msg

    def verify_extracted_data(self, tables, section, current_params):
        """Show a confirmation dialog to verify if the extracted data is correct"""
        # Skip the verification dialog and always return True
        # This prevents interrupting the extraction process
        return True
        
        # Original verification code (commented out)
        """
        # Create a formatted preview of the data for the user
        preview_text = f"Extracted {len(tables)} table(s) for {section.title()} section:\n\n"
        
        # Add preview of the first few rows from each table
        for i, df in enumerate(tables):
            preview_text += f"Table {i+1} ({len(df)} rows, {len(df.columns)} columns):\n"
            preview_text += str(df.head(3) if len(df) > 3 else df) + "\n\n"
        
        # Create confirmation dialog using our styled message box
        msg = self.create_styled_messagebox(
            title="Verify Extracted Data",
            text=f"Please verify the extracted {section} data",
            informative_text="Is the data correctly extracted?",
            detailed_text=preview_text
        )
        
        # Add buttons
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        
        # Store current section and areas for the custom settings button
        self.current_section = section
        self.current_table_areas = tables
        self.current_column_lines = current_params
        
        # Show the dialog and get user response
        result = msg.exec()
        return result == QMessageBox.Yes
        """

    def extract_with_new_params(self, section, table_areas, column_lines):
        """Show dialog to adjust extraction parameters and retry with new settings"""
        # Create a dialog for parameter adjustment
        param_dialog = QDialog(self)
        param_dialog.setWindowTitle(f"Adjust {section.title()} Extraction Parameters")
        param_dialog.setMinimumWidth(450)
        param_dialog.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
            }
            QLabel { 
                color: white; 
                margin: 2px 0;
            }
            QCheckBox { 
                color: white; 
            }
            QSpinBox {
                color: white;
                background-color: #34495e;
                border: 1px solid #3498db;
                border-radius: 3px;
                padding: 3px;
            }
            QLineEdit {
                color: white;
                background-color: #34495e;
                border: 1px solid #3498db;
                border-radius: 3px;
                padding: 3px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QCheckBox {
                color: white;
            }
        """)
        
        # Create form layout
        layout = QFormLayout(param_dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Add header text
        header_label = QLabel(f"Adjust parameters for {section.title()} section extraction")
        header_label.setFont(QFont("Arial", 11, QFont.Bold))
        header_label.setStyleSheet("color: white; margin-bottom: 10px;")
        layout.addRow(header_label)
        
        # Create explanation text
        explanation = QLabel("Modify these parameters to improve text extraction quality")
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color: #ecf0f1; margin: 5px 0 15px 0; font-style: italic;")
        layout.addRow(explanation)
        
        # Get the current row_tol if it exists in extraction_params
        current_row_tol = None
        if hasattr(self, 'extraction_params') and section in self.extraction_params:
            if 'row_tol' in self.extraction_params[section]:
                current_row_tol = self.extraction_params[section]['row_tol']
                print(f"Using existing row_tol={current_row_tol} for {section} section")
        
        # If no existing value, use the recommended defaults
        if current_row_tol is None:
            if section == 'header':
                current_row_tol = 5      # Default for header
            elif section == 'items':
                current_row_tol = 15     # Default for items
            else:  # summary
                current_row_tol = 10     # Default for summary
            print(f"Using default row_tol={current_row_tol} for {section} section")
        
        # Row tolerance parameter
        row_tol_input = QSpinBox()
        row_tol_input.setMinimum(1)
        row_tol_input.setMaximum(50)
        row_tol_input.setValue(current_row_tol)
        row_tol_input.setToolTip("Tolerance for grouping text into rows (higher value = more text in same row)")
        layout.addRow("Row Tolerance:", row_tol_input)
        
        # Add tooltip explanation
        row_tol_explanation = QLabel("Higher values group more text into the same row")
        row_tol_explanation.setStyleSheet("color: #bdc3c7; font-size: 9pt; font-style: italic;")
        layout.addRow("", row_tol_explanation)
        
        # Get current split_text value
        current_split_text = True
        if hasattr(self, 'extraction_params') and 'split_text' in self.extraction_params:
            current_split_text = self.extraction_params['split_text']
        
        # Split text parameter
        split_text_input = QCheckBox("Enable")
        split_text_input.setChecked(current_split_text)
        split_text_input.setToolTip("Split text that may contain multiple values")
        layout.addRow("Split Text:", split_text_input)
        
        # Get current strip_text value
        current_strip_text = "\\n"
        if hasattr(self, 'extraction_params') and 'strip_text' in self.extraction_params:
            # Convert newlines back to escaped form for display
            current_strip_text = repr(self.extraction_params['strip_text']).strip("'")
            if current_strip_text == "\\n":
                current_strip_text = "\\n"
        
        # Strip text parameter
        strip_text_input = QLineEdit()
        strip_text_input.setText(current_strip_text)
        strip_text_input.setToolTip("Characters to strip from text (use \\n for newlines)")
        layout.addRow("Strip Text:", strip_text_input)
        
        # Flavor parameter
        flavor_label = QLabel("Extraction Method: Stream")
        flavor_label.setToolTip("The extraction method is fixed to 'stream' for best results")
        layout.addRow("Extraction Method:", flavor_label)
        
        # Add a Test Regex button
        test_regex_btn = QPushButton("Test Regex Patterns")
        test_regex_btn.setToolTip("Test regex patterns for filtering table content")
        test_regex_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        test_regex_btn.clicked.connect(lambda: self.show_regex_test_dialog(section))
        
        # Add the regex button in its own row with a label
        regex_label = QLabel("Regex Patterns:")
        regex_label.setStyleSheet("color: white; margin-top: 10px;")
        layout.addRow(regex_label, test_regex_btn)
        
        # Add regex explanation
        regex_explanation = QLabel("Define patterns to identify table boundaries and filter content")
        regex_explanation.setStyleSheet("color: #bdc3c7; font-size: 9pt; font-style: italic;")
        layout.addRow("", regex_explanation)
        
        # Add buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = buttons.button(QDialogButtonBox.Ok)
        ok_button.setText("Extract")
        cancel_button = buttons.button(QDialogButtonBox.Cancel)
        buttons.accepted.connect(param_dialog.accept)
        buttons.rejected.connect(param_dialog.reject)
        
        # Add some spacing
        layout.addItem(QSpacerItem(20, 20))
        layout.addRow(buttons)
        
        # Show dialog and get result
        if param_dialog.exec() == QDialog.Accepted:
            # Get the new parameters
            new_params = {
                'row_tol': row_tol_input.value(),
                'split_text': split_text_input.isChecked(),
                'strip_text': strip_text_input.text().replace('\\n', '\n'),
                'flavor': 'stream'  # Keep this fixed
            }
            
            print(f"\nRetrying extraction with new parameters: {new_params}")
            
            # Create or update extraction_params with ACTUAL values, not defaults
            # This uses a more direct approach without initializing with defaults
            if not hasattr(self, 'extraction_params'):
                # If extraction_params doesn't exist yet, create it with minimal structure
                self.extraction_params = {}
            
            # Make sure all section dictionaries exist
            for sec in ['header', 'items', 'summary']:
                if sec not in self.extraction_params:
                    self.extraction_params[sec] = {}
            
            # Update the specific section parameters with the actual value
            self.extraction_params[section]['row_tol'] = new_params['row_tol']
            
            # Update global parameters with actual values
            self.extraction_params['split_text'] = new_params['split_text']
            self.extraction_params['strip_text'] = new_params['strip_text']
            self.extraction_params['flavor'] = new_params['flavor']
            
            # Make sure regex_patterns structure exists and is preserved
            if 'regex_patterns' not in self.extraction_params:
                self.extraction_params['regex_patterns'] = {
                    'header': {},
                    'items': {},
                    'summary': {}
                }
            else:
                # Ensure all section keys exist in regex_patterns
                for sec in ['header', 'items', 'summary']:
                    if sec not in self.extraction_params['regex_patterns']:
                        self.extraction_params['regex_patterns'][sec] = {}
            
            # Print current extraction parameters for debugging
            print(f"\nUpdated extraction parameters:")
            print(f"  {section.title()} row_tol: {self.extraction_params[section]['row_tol']}")
            print(f"  split_text: {self.extraction_params['split_text']}")
            print(f"  strip_text: {repr(self.extraction_params['strip_text'])}")
            
            # Print regex patterns if they exist
            print("\nRegex patterns in extraction parameters:")
            for sec, patterns in self.extraction_params['regex_patterns'].items():
                if patterns:
                    print(f"  {sec.title()} patterns:")
                    for pattern_type, pattern in patterns.items():
                        print(f"    {pattern_type}: {pattern}")
            
            # Also store in main window for reference during template saves
            try:
                from PySide6.QtWidgets import QApplication
                from main import PDFHarvest  # Import the main window class
                
                # Look specifically for the main application window
                for widget in QApplication.topLevelWidgets():
                    if isinstance(widget, PDFHarvest):
                        # Store the extraction_params on the main window
                        if not hasattr(widget, 'latest_extraction_params'):
                            widget.latest_extraction_params = {}
                            
                        # Ensure all section dictionaries exist in main window params
                        for sec in ['header', 'items', 'summary']:
                            if sec not in widget.latest_extraction_params:
                                widget.latest_extraction_params[sec] = {}
                        
                        # Update section parameters
                        widget.latest_extraction_params[section]['row_tol'] = new_params['row_tol']
                        
                        # Update global parameters
                        widget.latest_extraction_params['split_text'] = new_params['split_text']
                        widget.latest_extraction_params['strip_text'] = new_params['strip_text']
                        widget.latest_extraction_params['flavor'] = new_params['flavor']
                        
                        # Make sure regex_patterns structure exists in main window
                        if 'regex_patterns' not in widget.latest_extraction_params:
                            widget.latest_extraction_params['regex_patterns'] = {
                                'header': {},
                                'items': {},
                                'summary': {}
                            }
                        
                        # Copy over all regex patterns from our local extraction_params
                        if 'regex_patterns' in self.extraction_params:
                            for sec, patterns in self.extraction_params['regex_patterns'].items():
                                if sec not in widget.latest_extraction_params['regex_patterns']:
                                    widget.latest_extraction_params['regex_patterns'][sec] = {}
                                
                                # Copy patterns for this section
                                for p_type, pattern in patterns.items():
                                    widget.latest_extraction_params['regex_patterns'][sec][p_type] = pattern
                        
                        print("\nStored extraction parameters in main window for template saving")
                        break
            except Exception as e:
                print(f"Error storing extraction parameters in main window: {str(e)}")
                import traceback
                traceback.print_exc()
            
            # Process for multiple tables
            if len(table_areas) > 1:
                processed_tables = []
                
                for idx, (table_area, col_line) in enumerate(zip(table_areas, column_lines)):
                    print(f"\nRetrying extraction for {section.title()} Table {idx + 1}:")
                    try:
                        # Parameters for this single table with new values
                        single_table_params = {
                            'pages': '1',
                            'table_areas': [table_area],
                            'columns': [col_line] if col_line else None,
                            'split_text': new_params['split_text'],
                            'strip_text': new_params['strip_text'],
                            'flavor': new_params['flavor'],
                            'row_tol': new_params['row_tol']
                        }
                        
                        # Add regex patterns if defined
                        if hasattr(self, 'extraction_params') and 'regex_patterns' in self.extraction_params:
                            if section in self.extraction_params['regex_patterns']:
                                regex_patterns = self.extraction_params['regex_patterns'][section]
                                if regex_patterns:
                                    print(f"  Applying regex patterns: {regex_patterns}")
                                    
                                    # Apply start pattern if defined
                                    if 'start' in regex_patterns and regex_patterns['start']:
                                        single_table_params['start_regex'] = regex_patterns['start']
                                    
                                    # Apply end pattern if defined
                                    if 'end' in regex_patterns and regex_patterns['end']:
                                        single_table_params['end_regex'] = regex_patterns['end']
                                    
                                    # Apply skip pattern if defined
                                    if 'skip' in regex_patterns and regex_patterns['skip']:
                                        single_table_params['skip_regex'] = regex_patterns['skip']
                        
                        print(f"  Using parameters: {single_table_params}")
                        
                        # Extract just this table
                        table_result = pypdf_table_extraction.read_pdf(self.pdf_path, **single_table_params)
                        
                        if table_result and len(table_result) > 0 and table_result[0].df is not None:
                            table_df = table_result[0].df
                            
                            print(f"  Raw data extracted:")
                            print(table_df)
                            
                            # Clean up the DataFrame
                            table_df = table_df.replace(r'^\s*$', pd.NA, regex=True)
                            table_df = table_df.dropna(how='all')
                            table_df = table_df.dropna(axis=1, how='all')
                            
                            # Apply regex patterns directly to the dataframe
                            table_df = self.apply_regex_patterns_to_df(table_df, section)
                            
                            if not table_df.empty:
                                print(f"  Successfully extracted table with {len(table_df)} rows and {len(table_df.columns)} columns")
                                processed_tables.append(table_df)
                            else:
                                print(f"  No valid data found after cleaning and applying regex patterns")
                        else:
                            print(f"  No data extracted from table area")
                    except Exception as e:
                        print(f"  Error extracting table: {str(e)}")
                
                # Update the display with tables in the correct order
                if processed_tables:
                    print(f"\nSuccessfully processed {len(processed_tables)} {section} tables with new parameters")
                    
                    # Store the newly extracted data for later use (including JSON download)
                    if section == 'header':
                        self.header_df = processed_tables
                        self.update_data_table_for_header(processed_tables, section_type=section)
                    elif section == 'items':
                        self.item_details_df = processed_tables
                        # For items, we may want to combine the tables for display, but keep the original tables for JSON
                        self.update_data_table_for_header(processed_tables, section_type=section)
                    elif section == 'summary':
                        self.summary_df = processed_tables
                        self.update_data_table_for_header(processed_tables, section_type=section)
                else:
                    print(f"No valid {section} tables found with new parameters")
                    # Clear any existing data for this section
                    if section == 'header':
                        self.header_df = None
                    elif section == 'items':
                        self.item_details_df = None
                    elif section == 'summary':
                        self.summary_df = None
                    self.update_data_table(None, section)
            else:
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
                
                # Add regex patterns if defined
                if hasattr(self, 'extraction_params') and 'regex_patterns' in self.extraction_params:
                    if section in self.extraction_params['regex_patterns']:
                        regex_patterns = self.extraction_params['regex_patterns'][section]
                        if regex_patterns:
                            print(f"Applying regex patterns: {regex_patterns}")
                            
                            # Apply start pattern if defined
                            if 'start' in regex_patterns and regex_patterns['start']:
                                single_table_params['start_regex'] = regex_patterns['start']
                            
                            # Apply end pattern if defined
                            if 'end' in regex_patterns and regex_patterns['end']:
                                single_table_params['end_regex'] = regex_patterns['end']
                            
                            # Apply skip pattern if defined
                            if 'skip' in regex_patterns and regex_patterns['skip']:
                                single_table_params['skip_regex'] = regex_patterns['skip']
                
                print(f"\nRetrying single table extraction with new parameters: {single_table_params}")
                
                try:
                    # Extract table with new parameters
                    table_result = pypdf_table_extraction.read_pdf(self.pdf_path, **single_table_params)
                    
                    if table_result and len(table_result) > 0 and table_result[0].df is not None:
                        table_df = table_result[0].df
                        
                        print(f"Raw data extracted:")
                        print(table_df)
                        
                        # Clean up the DataFrame
                        table_df = table_df.replace(r'^\s*$', pd.NA, regex=True)
                        table_df = table_df.dropna(how='all')
                        table_df = table_df.dropna(axis=1, how='all')
                        
                        if not table_df.empty:
                            print(f"Successfully extracted table with {len(table_df)} rows and {len(table_df.columns)} columns")
                            
                            # Store the newly extracted data
                            if section == 'header':
                                self.header_df = table_df
                            elif section == 'items':
                                self.item_details_df = table_df
                            elif section == 'summary':
                                self.summary_df = table_df
                                
                            # Update the data table
                            self.update_data_table(table_df, section)
                        else:
                            print(f"No valid data found after cleaning")
                            # Clear any existing data for this section
                            if section == 'header':
                                self.header_df = None
                            elif section == 'items':
                                self.item_details_df = None
                            elif section == 'summary':
                                self.summary_df = None
                            self.update_data_table(None, section)
                    else:
                        print(f"No data extracted from table area")
                        
                except Exception as e:
                    print(f"Error extracting table: {str(e)}")
            
        return param_dialog.result() == QDialog.Accepted

    def show_custom_settings(self):
        """Show the custom settings dialog for the current section"""
        # Get the current section based on the navigation
        section_names = ['header', 'items', 'summary']
        current_section = section_names[self.current_page]
        
        # Initialize with empty data if needed
        table_areas = []
        column_lines = []
        
        if current_section in self.regions and self.regions[current_section]:
            # We need to convert the regions to the format expected by extract_with_new_params
            # This is similar to what's done in extract_and_update_section_data
            
            # Get the first page of the PDF to calculate scaling
            doc = fitz.open(self.pdf_path)
            page = doc[0]
            page_width = page.rect.width
            page_height = page.rect.height
            
            # Calculate scaling factors between display and PDF coordinates
            scale_x = page_width / self.pdf_label.pixmap().width()
            scale_y = page_height / self.pdf_label.pixmap().height()
            
            # Process each region for the current section
            for idx, rect in enumerate(self.regions[current_section]):
                # Convert rectangle coordinates to PDF space with proper scaling
                x1 = rect.x() * scale_x
                y1 = page_height - (rect.y() * scale_y)
                x2 = (rect.x() + rect.width()) * scale_x
                y2 = page_height - ((rect.y() + rect.height()) * scale_y)
                
                table_area = f"{x1},{y1},{x2},{y2}"
                table_areas.append(table_area)
                
                # Find column lines specific to this region
                region_columns = []
                if current_section in self.column_lines and self.column_lines[current_section]:
                    for line in self.column_lines[current_section]:
                        # Check if the line has a region index and matches current region
                        if len(line) == 3 and line[2] == idx:
                            region_columns.append(line[0].x() * scale_x)
                        # Handle old format without region index - associate with first region
                        elif len(line) == 2 and idx == 0:
                            region_columns.append(line[0].x() * scale_x)
                
                if region_columns:
                    # Sort column lines by x-coordinate and join as comma-separated string
                    col_str = ','.join([str(x) for x in sorted(region_columns)])
                    column_lines.append(col_str)
                else:
                    # Empty string for regions with no column lines
                    column_lines.append('')
        
        # Create a custom dialog for section settings with regex testing options
        if table_areas and current_section:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
            from PySide6.QtCore import Qt
            
            # Create a dialog for section settings options
            dialog = QDialog(self)
            dialog.setWindowTitle(f"{current_section.title()} Section Settings")
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #2c3e50;
                    color: white;
                }
                QLabel {
                    color: white;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    padding: 15px 30px;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: bold;
                    min-width: 240px;
                    margin: 10px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                #regexButton {
                    background-color: #f39c12;
                }
                #regexButton:hover {
                    background-color: #e67e22;
                }
            """)
            
            layout = QVBoxLayout(dialog)
            layout.setSpacing(20)
            layout.setContentsMargins(30, 30, 30, 30)
            
            # Add title
            title = QLabel(f"Settings for {current_section.title()} Section")
            title.setFont(QFont("Arial", 16, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
            
            # Add description
            description = QLabel("Choose which settings you want to adjust:")
            description.setAlignment(Qt.AlignCenter)
            layout.addWidget(description)
            
            # Add buttons
            buttons_layout = QVBoxLayout()
            buttons_layout.setSpacing(15)
            
            # Add "Adjust Extraction Parameters" button
            params_btn = QPushButton("Adjust Extraction Parameters")
            params_btn.setToolTip("Change row tolerance, text splitting, and other parameters")
            params_btn.clicked.connect(lambda: self.extract_with_new_params(current_section, table_areas, column_lines))
            params_btn.clicked.connect(dialog.accept)  # Close this dialog when clicked
            buttons_layout.addWidget(params_btn)
            
            # Add "Test Regex Patterns" button
            regex_btn = QPushButton("Test Regex Patterns")
            regex_btn.setObjectName("regexButton")  # For styling
            regex_btn.setToolTip("Test and define regex patterns for identifying table boundaries")
            regex_btn.clicked.connect(lambda: self.show_regex_test_dialog(current_section))
            regex_btn.clicked.connect(dialog.accept)  # Close this dialog when clicked
            buttons_layout.addWidget(regex_btn)
            
            # Add buttons layout to main layout
            layout.addLayout(buttons_layout)
            
            # Show the dialog
            dialog.exec()
        else:
            # If no table areas defined, go directly to extraction parameters
            self.extract_with_new_params(current_section, [], [])

    def show_regex_test_dialog(self, section):
        """Show dialog for testing regex patterns on current section data"""
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                      QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
                                      QHeaderView, QFormLayout, QComboBox, 
                                      QCheckBox, QGroupBox)
        from PySide6.QtGui import QColor, QFont
        from PySide6.QtCore import Qt
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Test Regex Patterns - {section.title()} Section")
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                color: black;
            }
        """)
        dialog.resize(600, 400)
        
        # Create main layout
        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add explanation
        explanation = QLabel("Test regex patterns against the current section data. "
                           "Patterns are used to identify table boundaries and filter content.")
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color: #666; margin-bottom: 10px;")
        main_layout.addWidget(explanation)
        
        # Create form for pattern input
        form_group = QGroupBox("Pattern Settings")
        form_layout = QFormLayout(form_group)
        
        # Pattern type selection
        pattern_type = QComboBox()
        pattern_type.addItems(["Start Pattern", "End Pattern", "Skip Pattern"])
        pattern_type.setToolTip("Start Pattern: identifies the first row of a table\n"
                              "End Pattern: identifies the last row of a table\n"
                              "Skip Pattern: identifies rows to exclude")
        form_layout.addRow("Pattern Type:", pattern_type)
        
        # Regex input with horizontal layout for input and test button
        pattern_layout = QHBoxLayout()
        
        pattern_input = QLineEdit()
        pattern_input.setPlaceholderText("Enter regex pattern (e.g., 'Item.*Description' or 'Total|Subtotal')")
        pattern_layout.addWidget(pattern_input, 1)
        
        test_button = QPushButton("Test Pattern")
        test_button.setDefault(True)
        pattern_layout.addWidget(test_button)
        
        form_layout.addRow("Regex Pattern:", pattern_layout)
        
        # Add explanation for common patterns
        pattern_examples = QLabel("Examples: 'Item.*Description' (header row), 'Total|Subtotal' (end row), 'Page \\d+' (skip row)")
        pattern_examples.setStyleSheet("color: #666; font-style: italic;")
        form_layout.addRow("", pattern_examples)
        
        # Checkbox to show highlighting on PDF
        highlight_pdf_check = QCheckBox("Highlight matches on PDF")
        highlight_pdf_check.setChecked(True)
        highlight_pdf_check.setToolTip("Show highlighted matches directly on the PDF")
        form_layout.addRow("Visualization:", highlight_pdf_check)
        
        main_layout.addWidget(form_group)
        
        # Add results table
        results_label = QLabel("Enter a pattern and click 'Test Pattern' to see results")
        results_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        main_layout.addWidget(results_label)
        
        results_table = QTableWidget()
        results_table.setColumnCount(3)
        results_table.setHorizontalHeaderLabels(["Pattern", "Matches", "Non-Matches"])
        results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        results_table.setAlternatingRowColors(True)
        main_layout.addWidget(results_table)
        
        # Add buttons at bottom
        buttons_layout = QHBoxLayout()
        
        # Add regex to template button
        add_to_template_btn = QPushButton("Apply to Template")
        add_to_template_btn.setEnabled(False)  # Enable after successful test
        add_to_template_btn.setToolTip("Save this regex pattern to the template configuration")
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.reject)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                color: #212529;
                border: 1px solid #ced4da;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        
        buttons_layout.addWidget(add_to_template_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # Store currently highlighted matches
        current_matches = []
        
        # Connect the test button click
        def on_test_clicked():
            nonlocal current_matches
            
            pattern = pattern_input.text().strip()
            if not pattern:
                results_label.setText("Please enter a pattern to test")
                results_label.setStyleSheet("color: #D32F2F; font-weight: bold;")
                results_table.setRowCount(0)
                add_to_template_btn.setEnabled(False)
                
                # Reset PDF view to original
                self.draw_sections()
                current_matches = []
                return
            
            # Get the pattern type
            p_type = pattern_type.currentText().split(" ")[0].lower()
            
            # Run the test
            matches, non_matches, error = self.test_regex_pattern(pattern, section, p_type)
            
            if error:
                results_label.setText(error)
                results_label.setStyleSheet("color: #D32F2F; font-weight: bold;")
                results_table.setRowCount(0)
                add_to_template_btn.setEnabled(False)
                
                # Reset PDF view to original
                self.draw_sections()
                current_matches = []
                return
            
            # Store current matches for highlighting
            current_matches = matches
            
            # Update results label
            results_label.setText(f"Pattern tested: Found {len(matches)} matches and {len(non_matches)} non-matches")
            results_label.setStyleSheet("color: black; font-weight: bold;")
            
            # Clear and populate results table
            results_table.setRowCount(0)
            
            # Add matches
            for table_idx, row_idx, row_text, is_first in matches:
                item = QTableWidgetItem(f"Table {table_idx + 1}, Row {row_idx}")
                item.setBackground(QColor("#E8F5E9"))  # Light green for matches
                results_table.insertRow(results_table.rowCount())
                results_table.setItem(results_table.rowCount() - 1, 0, item)
                
                # Add the text with highlighting if it's a first match
                text_item = QTableWidgetItem(row_text)
                if is_first:
                    text_item.setBackground(QColor("#C8E6C9"))  # Slightly darker green for first matches
                results_table.setItem(results_table.rowCount() - 1, 1, text_item)
                
                # Add empty cell for non-matches column
                results_table.setItem(results_table.rowCount() - 1, 2, QTableWidgetItem(""))
            
            # Add non-matches
            for table_idx, row_idx, row_text, _ in non_matches:
                item = QTableWidgetItem(f"Table {table_idx + 1}, Row {row_idx}")
                item.setBackground(QColor("#FFEBEE"))  # Light red for non-matches
                results_table.insertRow(results_table.rowCount())
                results_table.setItem(results_table.rowCount() - 1, 0, item)
                
                # Add empty cell for matches column
                results_table.setItem(results_table.rowCount() - 1, 1, QTableWidgetItem(""))
                
                # Add the text
                text_item = QTableWidgetItem(row_text)
                results_table.setItem(results_table.rowCount() - 1, 2, text_item)
            
            # Enable the Apply to Template button
            add_to_template_btn.setEnabled(True)
            
            # Update PDF view with highlights if enabled
            if highlight_pdf_check.isChecked():
                self.update_pdf_highlights(matches, non_matches, section)
        
        # Function to update PDF highlights
        def update_pdf_highlights(matches, non_matches, section):
            try:
                print(f"\n=== Starting PDF highlight update ===")
                print(f"Section: {section}")
                print(f"Number of matches: {len(matches)}")
                print(f"Number of non-matches: {len(non_matches)}")
                
                if not hasattr(self, 'drawing_pixmap') or self.drawing_pixmap is None:
                    print("Error: No drawing pixmap available")
                    return
                    
                print("Creating copy of drawing pixmap")
                highlighted_pixmap = self.drawing_pixmap.copy()
                painter = QPainter(highlighted_pixmap)
                
                print("Drawing base sections")
                self.draw_sections()
                
                # Set up colors for highlighting
                match_color = QColor(232, 245, 233, 100)  # Light green with transparency
                first_match_color = QColor(200, 230, 201, 150)  # Slightly darker green with transparency
                non_match_color = QColor(255, 235, 238, 100)  # Light red with transparency
                
                print("Processing matches")
                # Draw highlights for matches
                for table_idx, row_idx, _, is_first in matches:
                    try:
                        # Get the table area for this match
                        table_area = None
                        if section == 'header':
                            table_area = self.header_areas[table_idx] if self.header_areas else None
                        elif section == 'items':
                            table_area = self.item_areas[table_idx] if self.item_areas else None
                        elif section == 'summary':
                            table_area = self.summary_areas[table_idx] if self.summary_areas else None
                        
                        if table_area:
                            print(f"Processing match in table {table_idx + 1}, row {row_idx}")
                            # Calculate the y position for this row
                            df = None
                            if section == 'header':
                                df = self.header_df[table_idx] if isinstance(self.header_df, list) else self.header_df
                            elif section == 'items':
                                df = self.item_details_df[table_idx] if isinstance(self.item_details_df, list) else self.item_details_df
                            elif section == 'summary':
                                df = self.summary_df[table_idx] if isinstance(self.summary_df, list) else self.summary_df
                            
                            if df is not None and not df.empty:
                                row_height = table_area['height'] / df.shape[0]
                                y = table_area['y'] + (row_idx * row_height)
                                
                                print(f"Drawing highlight at y={y}, height={row_height}")
                                # Draw highlight rectangle
                                painter.fillRect(
                                    table_area['x'],
                                    y,
                                    table_area['width'],
                                    row_height,
                                    first_match_color if is_first else match_color
                                )
                            else:
                                print(f"Warning: No data available for table {table_idx + 1}")
                        else:
                            print(f"Warning: No table area found for table {table_idx + 1}")
                    except Exception as match_e:
                        print(f"Error processing match in table {table_idx + 1}, row {row_idx}: {str(match_e)}")
                        continue
                
                print("Processing non-matches")
                # Draw highlights for non-matches
                for table_idx, row_idx, _, _ in non_matches:
                    try:
                        # Get the table area for this non-match
                        table_area = None
                        if section == 'header':
                            table_area = self.header_areas[table_idx] if self.header_areas else None
                        elif section == 'items':
                            table_area = self.item_areas[table_idx] if self.item_areas else None
                        elif section == 'summary':
                            table_area = self.summary_areas[table_idx] if self.summary_areas else None
                        
                        if table_area:
                            print(f"Processing non-match in table {table_idx + 1}, row {row_idx}")
                            # Calculate the y position for this row
                            df = None
                            if section == 'header':
                                df = self.header_df[table_idx] if isinstance(self.header_df, list) else self.header_df
                            elif section == 'items':
                                df = self.item_details_df[table_idx] if isinstance(self.item_details_df, list) else self.item_details_df
                            elif section == 'summary':
                                df = self.summary_df[table_idx] if isinstance(self.summary_df, list) else self.summary_df
                            
                            if df is not None and not df.empty:
                                row_height = table_area['height'] / df.shape[0]
                                y = table_area['y'] + (row_idx * row_height)
                                
                                print(f"Drawing highlight at y={y}, height={row_height}")
                                # Draw highlight rectangle
                                painter.fillRect(
                                    table_area['x'],
                                    y,
                                    table_area['width'],
                                    row_height,
                                    non_match_color
                                )
                            else:
                                print(f"Warning: No data available for table {table_idx + 1}")
                        else:
                            print(f"Warning: No table area found for table {table_idx + 1}")
                    except Exception as non_match_e:
                        print(f"Error processing non-match in table {table_idx + 1}, row {row_idx}: {str(non_match_e)}")
                        continue
                
                print("Ending painter and updating pixmap")
                painter.end()
                self.pdf_label.setPixmap(highlighted_pixmap)
                print("PDF highlight update completed successfully")
                
            except Exception as e:
                print(f"\nError in update_pdf_highlights: {str(e)}")
                import traceback
                traceback.print_exc()
                # Ensure we always end the painter and restore the original view
                if painter:
                    painter.end()
                self.draw_sections()
        
        # Function to handle highlight checkbox toggle
        def on_highlight_toggled(checked):
            if checked and current_matches:
                # Re-run the test to get fresh matches and non-matches
                on_test_clicked()
            else:
                # Reset to original view
                self.draw_sections()
        
        # Connect the "Apply to Template" button
        def on_apply_to_template():
            pattern = pattern_input.text().strip()
            p_type = pattern_type.currentText().split(" ")[0].lower()
            
            # Make sure extraction_params and regex_patterns exist
            if not hasattr(self, 'extraction_params'):
                self.extraction_params = {'header': {}, 'items': {}, 'summary': {}}
            
            if 'regex_patterns' not in self.extraction_params:
                self.extraction_params['regex_patterns'] = {'header': {}, 'items': {}, 'summary': {}}
            
            if section not in self.extraction_params['regex_patterns']:
                self.extraction_params['regex_patterns'][section] = {}
            
            # Save the pattern
            self.extraction_params['regex_patterns'][section][p_type] = pattern
            
            # Apply the pattern to the current section data
            if section == 'header':
                if isinstance(self.header_df, list):
                    for i, df in enumerate(self.header_df):
                        if df is not None:
                            self.header_df[i] = self.apply_regex_patterns_to_df(df, section)
                else:
                    self.header_df = self.apply_regex_patterns_to_df(self.header_df, section)
            elif section == 'items':
                if isinstance(self.item_details_df, list):
                    for i, df in enumerate(self.item_details_df):
                        if df is not None:
                            self.item_details_df[i] = self.apply_regex_patterns_to_df(df, section)
                else:
                    self.item_details_df = self.apply_regex_patterns_to_df(self.item_details_df, section)
            elif section == 'summary':
                if isinstance(self.summary_df, list):
                    for i, df in enumerate(self.summary_df):
                        if df is not None:
                            self.summary_df[i] = self.apply_regex_patterns_to_df(df, section)
                else:
                    self.summary_df = self.apply_regex_patterns_to_df(self.summary_df, section)
            
            # Update the data table to show filtered results
            if section == 'header':
                self.update_data_table_for_header(self.header_df, 'header')
            elif section == 'items':
                self.update_data_table(self.item_details_df, 'items')
            elif section == 'summary':
                self.update_data_table(self.summary_df, 'summary')
            
            # Provide feedback
            results_label.setText(f"Pattern saved and applied: {p_type} pattern for {section} section set to '{pattern}'")
            results_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            
            # Also store in main window for reference during template saves
            try:
                from PySide6.QtWidgets import QApplication
                from main import PDFHarvest
                
                for widget in QApplication.topLevelWidgets():
                    if isinstance(widget, PDFHarvest):
                        # Make sure latest_extraction_params exists
                        if not hasattr(widget, 'latest_extraction_params'):
                            widget.latest_extraction_params = {}
                        
                        # Make sure regex_patterns exists
                        if 'regex_patterns' not in widget.latest_extraction_params:
                            widget.latest_extraction_params['regex_patterns'] = {'header': {}, 'items': {}, 'summary': {}}
                        
                        if section not in widget.latest_extraction_params['regex_patterns']:
                            widget.latest_extraction_params['regex_patterns'][section] = {}
                        
                        # Save the pattern
                        widget.latest_extraction_params['regex_patterns'][section][p_type] = pattern
                        
                        # Print info about what we've stored
                        print(f"\nStored regex pattern in main window:")
                        print(f"  Section: {section}, Type: {p_type}, Pattern: {pattern}")
                        
                        # Make sure we preserve existing extraction parameters too
                        if not hasattr(self, 'extraction_params'):
                            continue
                            
                        # Copy over other important extraction parameters
                        for sec in ['header', 'items', 'summary']:
                            if sec in self.extraction_params and 'row_tol' in self.extraction_params[sec]:
                                # Ensure section exists in main window params
                                if sec not in widget.latest_extraction_params:
                                    widget.latest_extraction_params[sec] = {}
                                
                                # Copy row_tol value
                                widget.latest_extraction_params[sec]['row_tol'] = self.extraction_params[sec]['row_tol']
                        
                        # Copy global parameters
                        for param in ['split_text', 'strip_text', 'flavor']:
                            if param in self.extraction_params:
                                widget.latest_extraction_params[param] = self.extraction_params[param]
                                
                        break
            except Exception as e:
                print(f"Could not store regex pattern in main window: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Connect button signals
        test_button.clicked.connect(on_test_clicked)
        add_to_template_btn.clicked.connect(on_apply_to_template)
        highlight_pdf_check.toggled.connect(on_highlight_toggled)
        
        # Also connect Enter key in regex input to test button
        pattern_input.returnPressed.connect(on_test_clicked)
        
        # Check if we have any existing patterns for this section
        if hasattr(self, 'extraction_params') and 'regex_patterns' in self.extraction_params:
            if section in self.extraction_params['regex_patterns']:
                # Get the pattern type from combobox
                initial_type = pattern_type.currentText().split(" ")[0].lower()
                
                # Check if we have a pattern for this type
                if initial_type in self.extraction_params['regex_patterns'][section]:
                    # Pre-fill the pattern input
                    existing_pattern = self.extraction_params['regex_patterns'][section][initial_type]
                    if existing_pattern:
                        pattern_input.setText(existing_pattern)
        
        # Connect pattern type change to update pattern input
        def on_pattern_type_changed():
            p_type = pattern_type.currentText().split(" ")[0].lower()
            if hasattr(self, 'extraction_params') and 'regex_patterns' in self.extraction_params:
                if section in self.extraction_params['regex_patterns']:
                    # Check if we have a pattern for this type
                    if p_type in self.extraction_params['regex_patterns'][section]:
                        # Pre-fill the pattern input
                        existing_pattern = self.extraction_params['regex_patterns'][section][p_type]
                        if existing_pattern:
                            pattern_input.setText(existing_pattern)
                            # Run test automatically if we have a pattern
                            on_test_clicked()
                        else:
                            pattern_input.clear()
                    else:
                        pattern_input.clear()
        
        pattern_type.currentIndexChanged.connect(on_pattern_type_changed)
        
        # Show the dialog
        dialog.exec()

    def highlight_regex_matches(self, matches, section):
        """Highlight regex pattern matches directly on the PDF for visual feedback"""
        if not matches or not self.pdf_document:
            return
        
        # Create a copy of the original pixmap for drawing
        highlighted_pixmap = self.original_pixmap.copy()
        
        # Create a painter for drawing highlights
        painter = QPainter(highlighted_pixmap)
        painter.setOpacity(0.4)  # Semi-transparent highlighting
        
        # Highlight color - bright yellow
        highlight_color = QColor(255, 255, 0, 120)  # Yellow with alpha
        painter.setBrush(highlight_color)
        painter.setPen(QPen(QColor(255, 165, 0), 2))  # Orange border
        
        # Get the table rects for this section
        rects = []
        if section in self.regions:
            rects = self.regions[section]
        
        if not rects:
            painter.end()
            return highlighted_pixmap
        
        # Convert matches (table_idx, row_idx, text) to screen coordinates
        try:
            # Determine how many rows are in each table by looking at the data
            table_row_counts = {}
            section_df = None
            
            if section == 'header':
                section_df = self.header_df
            elif section == 'items':
                section_df = self.item_details_df
            elif section == 'summary':
                section_df = self.summary_df
            
            # Calculate row counts for each table
            if isinstance(section_df, list):
                for i, df in enumerate(section_df):
                    if df is not None and not df.empty:
                        table_row_counts[i] = len(df)
            elif section_df is not None and not section_df.empty:
                table_row_counts[0] = len(section_df)
            
            # For each match, highlight the corresponding row in the PDF
            for table_idx, row_idx, _ in matches:
                if table_idx >= len(rects) or table_idx not in table_row_counts:
                    continue
                
                rect = rects[table_idx]
                row_count = table_row_counts[table_idx]
                
                if row_count <= 0:
                    continue
                
                # Calculate row height within the table
                row_height = rect.height() / row_count
                
                # Calculate row rect based on row_idx
                row_rect_y = rect.y() + (row_idx * row_height)
                row_rect_height = row_height - 1  # Slight gap between rows
                
                row_rect = QRect(
                    rect.x(), 
                    int(row_rect_y), 
                    rect.width(), 
                    int(row_rect_height)
                )
                
                # Draw the highlighted row
                painter.drawRect(row_rect)
                
                # Add row number label to the right of the highlight
                painter.setPen(QColor(255, 0, 0))  # Red text
                painter.setFont(QFont("Arial", 8, QFont.Bold))
                row_label = f"Row {row_idx+1}"
                painter.drawText(
                    rect.right() + 5, 
                    int(row_rect_y + row_rect_height/2 + 4),  # Vertically center the text
                    row_label
                )
        except Exception as e:
            print(f"Error highlighting matches: {str(e)}")
            import traceback
            traceback.print_exc()
        
        painter.end()
        return highlighted_pixmap

    def apply_regex_patterns_to_df(self, df, section):
        """Apply regex patterns to filter DataFrame content"""
        try:
            print(f"\n=== Applying regex patterns to {section} DataFrame ===")
            if df is None or df.empty:
                print("DataFrame is None or empty")
                return df
                
            print(f"Input DataFrame shape: {df.shape}")
            
            # Get patterns for this section
            patterns = {}
            if hasattr(self, 'extraction_params') and 'regex_patterns' in self.extraction_params:
                if section in self.extraction_params['regex_patterns']:
                    patterns = self.extraction_params['regex_patterns'][section]
                    print(f"Found patterns for {section}: {patterns}")
            
            if not patterns:
                print("No patterns found for this section")
                return df
            
            # Apply start pattern
            if 'start' in patterns:
                start_pattern = patterns['start']
                print(f"Applying start pattern: {start_pattern}")
                start_match_idx = None
                for idx, row in df.iterrows():
                    row_text = " ".join([str(val) for val in row if pd.notna(val)])
                    if re.search(start_pattern, row_text, re.IGNORECASE):
                        start_match_idx = idx
                        print(f"Found start row at index {idx}")
                        break
                
                if start_match_idx is not None:
                    df = df.loc[start_match_idx:]
                    print(f"DataFrame after start pattern: {df.shape}")
            
            # Apply end pattern
            if 'end' in patterns:
                end_pattern = patterns['end']
                print(f"Applying end pattern: {end_pattern}")
                end_match_idx = None
                for idx, row in df.iterrows():
                    row_text = " ".join([str(val) for val in row if pd.notna(val)])
                    if re.search(end_pattern, row_text, re.IGNORECASE):
                        end_match_idx = idx
                        print(f"Found end row at index {idx}")
                        break
                
                if end_match_idx is not None:
                    df = df.loc[:end_match_idx]
                    print(f"DataFrame after end pattern: {df.shape}")
            
            # Apply skip pattern
            if 'skip' in patterns:
                skip_pattern = patterns['skip']
                print(f"Applying skip pattern: {skip_pattern}")
                rows_to_keep = []
                for idx, row in df.iterrows():
                    row_text = " ".join([str(val) for val in row if pd.notna(val)])
                    if not re.search(skip_pattern, row_text, re.IGNORECASE):
                        rows_to_keep.append(idx)
                
                df = df.loc[rows_to_keep]
                print(f"DataFrame after skip pattern: {df.shape}")
            
            print(f"Final DataFrame shape: {df.shape}")
            return df
            
        except Exception as e:
            print(f"\nError in apply_regex_patterns_to_df: {str(e)}")
            import traceback
            traceback.print_exc()
            return df

    def test_regex_pattern(self, pattern, section, pattern_type):
        """Test a regex pattern against the current section data"""
        matches = []
        non_matches = []
        error = None
        
        try:
            print(f"\n=== Starting regex pattern test ===")
            print(f"Pattern: {pattern}")
            print(f"Section: {section}")
            print(f"Pattern Type: {pattern_type}")
            
            # Validate the regex pattern
            try:
                re.compile(pattern)
                print("Regex pattern validation successful")
            except re.error as e:
                print(f"Regex pattern validation failed: {str(e)}")
                return [], [], f"Invalid regex pattern: {str(e)}"
            
            # Get the data for this section
            section_data = None
            if section == 'header':
                section_data = self.header_df
                print("Using header_df data")
            elif section == 'items':
                section_data = self.item_details_df
                print("Using item_details_df data")
            elif section == 'summary':
                section_data = self.summary_df
                print("Using summary_df data")
            
            if section_data is None:
                print("No data available for this section")
                return [], [], "No data available for this section"
            
            print(f"Section data type: {type(section_data)}")
            if isinstance(section_data, list):
                print(f"Number of tables in section: {len(section_data)}")
            else:
                print(f"Single table with shape: {section_data.shape}")
            
            # Process the data for matching
            if isinstance(section_data, list):
                # Multiple tables
                for table_idx, df in enumerate(section_data):
                    print(f"\nProcessing table {table_idx + 1}")
                    if df is None or df.empty:
                        print(f"Table {table_idx + 1} is empty or None, skipping")
                        continue
                    
                    print(f"Table {table_idx + 1} shape: {df.shape}")
                    
                    # For each table, process according to the pattern type
                    if pattern_type == 'start':
                        print("Processing as start pattern")
                        # Find the first match in this table
                        first_match_idx = None
                        for row_idx, row in df.iterrows():
                            try:
                                row_text = " ".join([str(val) for val in row if pd.notna(val)])
                                if re.search(pattern, row_text, re.IGNORECASE):
                                    if first_match_idx is None:
                                        first_match_idx = row_idx
                                        print(f"Found first match at row {row_idx}")
                                    matches.append((table_idx, row_idx, row_text, row_idx == first_match_idx))
                                else:
                                    non_matches.append((table_idx, row_idx, row_text, False))
                            except Exception as row_e:
                                print(f"Error processing row {row_idx}: {str(row_e)}")
                                continue
                    
                    elif pattern_type == 'end':
                        print("Processing as end pattern")
                        # First find a simulated 'start' - either first row or first matching row
                        start_idx = df.index[0] if len(df.index) > 0 else None
                        print(f"Start index: {start_idx}")
                        
                        # Then find first match after start
                        first_match_after_start = None
                        for row_idx, row in df.iterrows():
                            try:
                                row_text = " ".join([str(val) for val in row if pd.notna(val)])
                                # Only consider rows after start
                                if start_idx is not None and row_idx >= start_idx:
                                    if re.search(pattern, row_text, re.IGNORECASE):
                                        if first_match_after_start is None:
                                            first_match_after_start = row_idx
                                            print(f"Found first match after start at row {row_idx}")
                                        matches.append((table_idx, row_idx, row_text, row_idx == first_match_after_start))
                                    else:
                                        non_matches.append((table_idx, row_idx, row_text, False))
                            except Exception as row_e:
                                print(f"Error processing row {row_idx}: {str(row_e)}")
                                continue
                    
                    elif pattern_type == 'skip':
                        print("Processing as skip pattern")
                        # All matches should be excluded
                        for row_idx, row in df.iterrows():
                            try:
                                row_text = " ".join([str(val) for val in row if pd.notna(val)])
                                if re.search(pattern, row_text, re.IGNORECASE):
                                    matches.append((table_idx, row_idx, row_text, True))  # True means it will be skipped
                                else:
                                    non_matches.append((table_idx, row_idx, row_text, False))
                            except Exception as row_e:
                                print(f"Error processing row {row_idx}: {str(row_e)}")
                                continue
                    
                    else:  # Default case - just match all
                        print("Processing as default pattern")
                        for row_idx, row in df.iterrows():
                            try:
                                row_text = " ".join([str(val) for val in row if pd.notna(val)])
                                if re.search(pattern, row_text, re.IGNORECASE):
                                    matches.append((table_idx, row_idx, row_text, True))
                                else:
                                    non_matches.append((table_idx, row_idx, row_text, False))
                            except Exception as row_e:
                                print(f"Error processing row {row_idx}: {str(row_e)}")
                                continue
            else:
                print("\nProcessing single table")
                # Single table - similar logic as above but for a single table
                if not section_data.empty:
                    print(f"Table shape: {section_data.shape}")
                    if pattern_type == 'start':
                        print("Processing as start pattern")
                        # Find the first match
                        first_match_idx = None
                        for row_idx, row in section_data.iterrows():
                            try:
                                row_text = " ".join([str(val) for val in row if pd.notna(val)])
                                if re.search(pattern, row_text, re.IGNORECASE):
                                    if first_match_idx is None:
                                        first_match_idx = row_idx
                                        print(f"Found first match at row {row_idx}")
                                    matches.append((0, row_idx, row_text, row_idx == first_match_idx))
                                else:
                                    non_matches.append((0, row_idx, row_text, False))
                            except Exception as row_e:
                                print(f"Error processing row {row_idx}: {str(row_e)}")
                                continue
                    
                    elif pattern_type == 'end':
                        print("Processing as end pattern")
                        # First find a simulated 'start' - either first row or first matching row
                        start_idx = section_data.index[0] if len(section_data.index) > 0 else None
                        print(f"Start index: {start_idx}")
                        
                        # Then find first match after start
                        first_match_after_start = None
                        for row_idx, row in section_data.iterrows():
                            try:
                                row_text = " ".join([str(val) for val in row if pd.notna(val)])
                                # Only consider rows after start
                                if start_idx is not None and row_idx >= start_idx:
                                    if re.search(pattern, row_text, re.IGNORECASE):
                                        if first_match_after_start is None:
                                            first_match_after_start = row_idx
                                            print(f"Found first match after start at row {row_idx}")
                                        matches.append((0, row_idx, row_text, row_idx == first_match_after_start))
                                    else:
                                        non_matches.append((0, row_idx, row_text, False))
                            except Exception as row_e:
                                print(f"Error processing row {row_idx}: {str(row_e)}")
                                continue
                    
                    elif pattern_type == 'skip':
                        print("Processing as skip pattern")
                        # All matches should be excluded
                        for row_idx, row in section_data.iterrows():
                            try:
                                row_text = " ".join([str(val) for val in row if pd.notna(val)])
                                if re.search(pattern, row_text, re.IGNORECASE):
                                    matches.append((0, row_idx, row_text, True))  # True means it will be skipped
                                else:
                                    non_matches.append((0, row_idx, row_text, False))
                            except Exception as row_e:
                                print(f"Error processing row {row_idx}: {str(row_e)}")
                                continue
                    
                    else:  # Default case - just match all
                        print("Processing as default pattern")
                        for row_idx, row in section_data.iterrows():
                            try:
                                row_text = " ".join([str(val) for val in row if pd.notna(val)])
                                if re.search(pattern, row_text, re.IGNORECASE):
                                    matches.append((0, row_idx, row_text, True))
                                else:
                                    non_matches.append((0, row_idx, row_text, False))
                            except Exception as row_e:
                                print(f"Error processing row {row_idx}: {str(row_e)}")
                                continue
                else:
                    print("Single table is empty")
            
            print(f"\nTest results:")
            print(f"Total matches found: {len(matches)}")
            print(f"Total non-matches: {len(non_matches)}")
            
        except Exception as e:
            error = f"Error testing pattern: {str(e)}"
            print(f"\nError in test_regex_pattern: {error}")
            import traceback
            traceback.print_exc()
        
        return matches, non_matches, error

    def download_json(self):
        """Download the extracted data as JSON file"""
        # Create a dictionary to store all the data
        export_data = {
            'header': [],
            'items': [],
            'summary': []
        }
        
        # Convert header data to JSON-serializable format
        if self.header_df is not None:
            if isinstance(self.header_df, list):
                for i, df in enumerate(self.header_df):
                    if df is not None and not df.empty:
                        export_data['header'].append(df.fillna('').to_dict('records'))
            elif not self.header_df.empty:
                export_data['header'].append(self.header_df.fillna('').to_dict('records'))
        
        # Convert items data to JSON-serializable format
        if self.item_details_df is not None:
            if isinstance(self.item_details_df, list):
                for i, df in enumerate(self.item_details_df):
                    if df is not None and not df.empty:
                        export_data['items'].append(df.fillna('').to_dict('records'))
            elif not self.item_details_df.empty:
                export_data['items'].append(self.item_details_df.fillna('').to_dict('records'))
        
        # Convert summary data to JSON-serializable format
        if self.summary_df is not None:
            if isinstance(self.summary_df, list):
                for i, df in enumerate(self.summary_df):
                    if df is not None and not df.empty:
                        export_data['summary'].append(df.fillna('').to_dict('records'))
            elif not self.summary_df.empty:
                export_data['summary'].append(self.summary_df.fillna('').to_dict('records'))
        
        # Get suggested filename from PDF path
        base_name = os.path.basename(self.pdf_path)
        file_name, _ = os.path.splitext(base_name)
        suggested_name = f"{file_name}_extracted.json"
        
        # Open file dialog to select save location
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save JSON Data",
            suggested_name,
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                # Ensure the file has .json extension
                if not file_path.lower().endswith('.json'):
                    file_path += '.json'
                
                # Write the data to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            
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

    def update_pdf_highlights(self, matches, non_matches, section):
        """Update the PDF view with regex pattern highlights"""
        try:
            print(f"\n=== Starting PDF highlight update ===")
            print(f"Section: {section}")
            print(f"Number of matches: {len(matches)}")
            print(f"Number of non-matches: {len(non_matches)}")
            
            if not hasattr(self, 'drawing_pixmap') or self.drawing_pixmap is None:
                print("Error: No drawing pixmap available")
                return
                
            print("Creating copy of drawing pixmap")
            highlighted_pixmap = self.drawing_pixmap.copy()
            painter = QPainter(highlighted_pixmap)
            
            # Set up colors for highlighting
            match_color = QColor(232, 245, 233, 100)  # Light green with transparency
            first_match_color = QColor(200, 230, 201, 150)  # Slightly darker green with transparency
            non_match_color = QColor(255, 235, 238, 100)  # Light red with transparency
            
            print("Processing matches")
            # Draw highlights for matches
            for table_idx, row_idx, _, is_first in matches:
                try:
                    # Get the table area for this match
                    table_area = None
                    if section == 'header':
                        table_area = self.header_areas[table_idx] if self.header_areas else None
                    elif section == 'items':
                        table_area = self.item_areas[table_idx] if self.item_areas else None
                    elif section == 'summary':
                        table_area = self.summary_areas[table_idx] if self.summary_areas else None
                    
                    if table_area:
                        print(f"Processing match in table {table_idx + 1}, row {row_idx}")
                        # Calculate the y position for this row
                        df = None
                        if section == 'header':
                            df = self.header_df[table_idx] if isinstance(self.header_df, list) else self.header_df
                        elif section == 'items':
                            df = self.item_details_df[table_idx] if isinstance(self.item_details_df, list) else self.item_details_df
                        elif section == 'summary':
                            df = self.summary_df[table_idx] if isinstance(self.summary_df, list) else self.summary_df
                        
                        if df is not None and not df.empty:
                            row_height = table_area['height'] / df.shape[0]
                            y = table_area['y'] + (row_idx * row_height)
                            
                            print(f"Drawing highlight at y={y}, height={row_height}")
                            # Draw highlight rectangle
                            painter.fillRect(
                                table_area['x'],
                                y,
                                table_area['width'],
                                row_height,
                                first_match_color if is_first else match_color
                            )
                        else:
                            print(f"Warning: No data available for table {table_idx + 1}")
                    else:
                        print(f"Warning: No table area found for table {table_idx + 1}")
                except Exception as match_e:
                    print(f"Error processing match in table {table_idx + 1}, row {row_idx}: {str(match_e)}")
                    continue
            
            print("Processing non-matches")
            # Draw highlights for non-matches
            for table_idx, row_idx, _, _ in non_matches:
                try:
                    # Get the table area for this non-match
                    table_area = None
                    if section == 'header':
                        table_area = self.header_areas[table_idx] if self.header_areas else None
                    elif section == 'items':
                        table_area = self.item_areas[table_idx] if self.item_areas else None
                    elif section == 'summary':
                        table_area = self.summary_areas[table_idx] if self.summary_areas else None
                    
                    if table_area:
                        print(f"Processing non-match in table {table_idx + 1}, row {row_idx}")
                        # Calculate the y position for this row
                        df = None
                        if section == 'header':
                            df = self.header_df[table_idx] if isinstance(self.header_df, list) else self.header_df
                        elif section == 'items':
                            df = self.item_details_df[table_idx] if isinstance(self.item_details_df, list) else self.item_details_df
                        elif section == 'summary':
                            df = self.summary_df[table_idx] if isinstance(self.summary_df, list) else self.summary_df
                        
                        if df is not None and not df.empty:
                            row_height = table_area['height'] / df.shape[0]
                            y = table_area['y'] + (row_idx * row_height)
                            
                            print(f"Drawing highlight at y={y}, height={row_height}")
                            # Draw highlight rectangle
                            painter.fillRect(
                                table_area['x'],
                                y,
                                table_area['width'],
                                row_height,
                                non_match_color
                            )
                        else:
                            print(f"Warning: No data available for table {table_idx + 1}")
                    else:
                        print(f"Warning: No table area found for table {table_idx + 1}")
                except Exception as non_match_e:
                    print(f"Error processing non-match in table {table_idx + 1}, row {row_idx}: {str(non_match_e)}")
                    continue
            
            print("Ending painter and updating pixmap")
            painter.end()
            self.pdf_label.setPixmap(highlighted_pixmap)
            print("PDF highlight update completed successfully")
            
        except Exception as e:
            print(f"\nError in update_pdf_highlights: {str(e)}")
            import traceback
            traceback.print_exc()
            # Ensure we always end the painter and restore the original view
            if painter:
                painter.end()
            self.draw_sections()

    def update_page_display(self, page_number):
        """Update the display for the current page"""
        if not self.is_multi_page:
            return
            
        # Update page label
        self.page_label.setText(f"Page {page_number}")
        
        # Load appropriate page data
        if page_number == 1:
            # First page - show header and items
            self.show_header_section(True)
            self.show_items_section(True)
            self.show_summary_section(False)
        elif page_number == self.total_pages:
            # Last page - show items and summary
            self.show_header_section(self.has_header_repeat)
            self.show_items_section(True)
            self.show_summary_section(True)
        else:
            # Middle page - show items only (and header if repeating)
            self.show_header_section(self.has_header_repeat)
            self.show_items_section(True)
            self.show_summary_section(False)