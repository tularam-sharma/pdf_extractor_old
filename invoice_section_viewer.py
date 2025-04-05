from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QScrollArea, QFrame, QStackedWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QDialog, QFormLayout, 
                             QSpinBox, QCheckBox, QLineEdit, QMessageBox, QDialogButtonBox, QSpacerItem)
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import (QFont, QImage, QPixmap, QCursor, QPainter, 
                          QPen, QColor)
import fitz
from PIL import Image
import io
import pandas as pd
import re
import pypdf_table_extraction

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
    
    def __init__(self, pdf_path, header_df, item_details_df, summary_df, regions, column_lines):
        super().__init__()
        self.pdf_path = pdf_path
        self.header_df = header_df
        self.item_details_df = item_details_df
        self.summary_df = summary_df
        self.regions = regions
        self.column_lines = column_lines
        self.current_page = 0
        self.initUI()
        self.load_pdf()

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
        painter = QPainter(self.drawing_pixmap)
        
        # Define section colors
        colors = {
            'header': QColor(255, 0, 0, 127),    # Red
            'items': QColor(0, 255, 0, 127),     # Green
            'summary': QColor(0, 0, 255, 127)    # Blue
        }
        
        # Define section titles
        titles = {
            'header': "Header",
            'items': "Items",
            'summary': "Summary"
        }
        
        # Draw only the current section
        sections = ['header', 'items', 'summary']
        if 0 <= self.current_page < len(sections):
            section = sections[self.current_page]
            if section in self.regions and self.regions[section]:
                # Get color for the current section
                color = colors[section]
                pen = QPen(color, 2, Qt.SolidLine)
                painter.setPen(pen)
                
                # Draw all regions for the current section
                for i, rect in enumerate(self.regions[section]):
                    # Draw the rectangle
                    painter.drawRect(rect)
                    
                    # Draw the label text above the rectangle
                    painter.setPen(Qt.black)
                    font = QFont("Arial", 10, QFont.Bold)
                    painter.setFont(font)
                    
                    # Create label text with section name and table number if multiple tables exist
                    label_text = titles[section]
                    if len(self.regions[section]) > 1:
                        label_text += f" Table #{i+1}"
                    
                    # Calculate position for the label (above the rectangle)
                    label_x = rect.left()
                    label_y = rect.top() - 20  # 20px above the rectangle
                    
                    # Draw a small line connecting the label to the rectangle
                    connecting_line_start = QPoint(label_x + 5, label_y + 15)
                    connecting_line_end = QPoint(label_x + 5, rect.top())
                    painter.drawLine(connecting_line_start, connecting_line_end)
                    
                    # Draw the label text
                    text_rect = QRect(label_x, label_y, rect.width(), 20)
                    painter.drawText(text_rect, Qt.AlignLeft, label_text)
                    
                    # Also draw small table number inside the rectangle for easy reference
                    if len(self.regions[section]) > 1:
                        painter.drawText(rect.adjusted(5, 5, -5, -5), 
                                       Qt.AlignLeft | Qt.AlignTop,
                                       f"{i+1}")
                    
                    # Reset pen color for the next rectangle
                    painter.setPen(pen)
                
                # Log info about the regions
                for i, rect in enumerate(self.regions[section]):
                    print(f"{section.title()} region {i+1}: x={rect.x()}, y={rect.y()}, "
                         f"width={rect.width()}, height={rect.height()}")

        painter.end()

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
                        
                        # Define default extraction parameters
                        extraction_params = {
                            'row_tol': 5,
                            'split_text': True,
                            'strip_text': '\n',
                            'flavor': 'stream'
                        }
                        
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
                        
                        # Set default extraction parameters based on section
                        extraction_params = {
                            'row_tol': 15 if section == 'items' else 10 if section == 'summary' else 5,
                            'split_text': True,
                            'strip_text': '\n',
                            'flavor': 'stream'
                        }
                        
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

    def update_data_table_for_header(self, table_list, section_type='header'):
        # Method to display multiple tables of a section type (header or summary)
        # Clear existing table
        self.data_table.clear()
        self.data_table.setRowCount(0)
        self.data_table.setColumnCount(0)
        
        # Check if we have tables to display
        if not table_list or len(table_list) == 0:
            self.section_title.setText(f"No {section_type.title()} Data Available")
            
            # Add a message row
            self.data_table.setColumnCount(2)
            self.data_table.setHorizontalHeaderLabels(["Key", "Value"])
            self.data_table.insertRow(0)
            message_item = QTableWidgetItem(f"No data available for the {section_type} section")
            self.data_table.setItem(0, 0, message_item)
            self.data_table.setSpan(0, 0, 1, 2)  # Span across both columns
            return
        
        # Set up the table with two columns for JSON-like display
        self.data_table.setColumnCount(2)
        self.data_table.setHorizontalHeaderLabels(["Key", "Value"])
        
        # Log tables for debugging
        print(f"\nDISPLAYING {section_type.upper()} TABLES IN JSON FORMAT")
        print(f"Number of {section_type} tables: {len(table_list)}")
        
        # Update section title
        self.section_title.setText(f"{section_type.title()} Section - JSON Format ({len(table_list)} Tables)")
        
        row_count = 0
        
        # Process each table in the list
        for table_idx, df in enumerate(table_list):
            # Add a header row for this table
            self.data_table.insertRow(row_count)
            table_header = QTableWidgetItem(f"TABLE {table_idx + 1}")
            table_header.setBackground(QColor(200, 220, 240))  # Light blue background
            table_header.setFont(QFont("Arial", 10, QFont.Bold))
            table_value = QTableWidgetItem(f"{len(df)} rows, {len(df.columns)} columns")
            self.data_table.setItem(row_count, 0, table_header)
            self.data_table.setItem(row_count, 1, table_value)
            row_count += 1
            
            # Process differently based on section type and table structure
            if section_type == 'header' or section_type == 'summary':
                # Process as key-value pairs where first column is key, others are values
                
                for df_row_idx, row in df.iterrows():
                    # Skip processing if row is empty
                    if row.isna().all():
                        continue
                    
                    # Get the key from the first column
                    key = str(row.iloc[0]) if not pd.isna(row.iloc[0]) else f"Row {df_row_idx+1}"
                    
                    # For tables with only one column, show as direct key-value
                    if len(row) == 1:
                        self.data_table.insertRow(row_count)
                        key_item = QTableWidgetItem(f"  {key}")
                        value_item = QTableWidgetItem("<single column table>")
                        self.data_table.setItem(row_count, 0, key_item)
                        self.data_table.setItem(row_count, 1, value_item)
                        row_count += 1
                    else:
                        # For multi-column tables, first column is key, others are values in JSON-like format
                        values = {}
                        for col_idx in range(1, len(row)):
                            col_name = f"C{col_idx}" if isinstance(df.columns[col_idx], int) else str(df.columns[col_idx])
                            value = str(row.iloc[col_idx]) if not pd.isna(row.iloc[col_idx]) else ""
                            if value:  # Only add non-empty values
                                values[col_name] = value
                        
                        if values:  # Only add if there are values
                            self.data_table.insertRow(row_count)
                            key_item = QTableWidgetItem(f"  {key}")
                            value_item = QTableWidgetItem(str(values))
                            self.data_table.setItem(row_count, 0, key_item)
                            self.data_table.setItem(row_count, 1, value_item)
                            row_count += 1
            
            elif section_type == 'items':
                # For items tables, look for section headers (rows with many NULL values)
                current_section = f"Items in Table {table_idx + 1}"
                section_items = []
                
                for df_row_idx, row in df.iterrows():
                    # Check if this is a section header (3+ NULL values)
                    null_count = row.isna().sum()
                    if null_count >= 3 or (len(row) > 2 and null_count >= len(row) / 2):
                        # First, add the previous section if it has items
                        if section_items:
                            # Add a row for the section
                            self.data_table.insertRow(row_count)
                            section_key = QTableWidgetItem(f"  SECTION: {current_section}")
                            section_key.setBackground(QColor(230, 230, 250))  # Light purple background
                            section_value = QTableWidgetItem(f"{len(section_items)} items")
                            self.data_table.setItem(row_count, 0, section_key)
                            self.data_table.setItem(row_count, 1, section_value)
                            row_count += 1
                            
                            # Add rows for each item in the section
                            for idx, item in enumerate(section_items):
                                self.data_table.insertRow(row_count)
                                item_key = QTableWidgetItem(f"    Item {idx+1}")
                                item_value = QTableWidgetItem(str(item))
                                self.data_table.setItem(row_count, 0, item_key)
                                self.data_table.setItem(row_count, 1, item_value)
                                row_count += 1
                            
                            # Reset for new section
                            section_items = []
                        
                        # Extract the new section name - concatenate all non-null values
                        section_parts = [
                            str(val) for val in row if not pd.isna(val) and str(val).strip()
                        ]
                        current_section = " ".join(section_parts) if section_parts else f"Unnamed Section in Table {table_idx + 1}"
                    else:
                        # This is a regular item row - create a dictionary of column values
                        item_data = {}
                        for col_idx, value in enumerate(row):
                            col_name = f"C{col_idx+1}" if isinstance(df.columns[col_idx], int) else str(df.columns[col_idx])
                            if not pd.isna(value) and str(value).strip():
                                item_data[col_name] = str(value)
                        
                        if item_data:  # Only add if there's data
                            section_items.append(item_data)
                
                # Add the last section if it has items
                if section_items:
                    self.data_table.insertRow(row_count)
                    section_key = QTableWidgetItem(f"  SECTION: {current_section}")
                    section_key.setBackground(QColor(230, 230, 250))  # Light purple background
                    section_value = QTableWidgetItem(f"{len(section_items)} items")
                    self.data_table.setItem(row_count, 0, section_key)
                    self.data_table.setItem(row_count, 1, section_value)
                    row_count += 1
                    
                    for idx, item in enumerate(section_items):
                        self.data_table.insertRow(row_count)
                        item_key = QTableWidgetItem(f"    Item {idx+1}")
                        item_value = QTableWidgetItem(str(item))
                        self.data_table.setItem(row_count, 0, item_key)
                        self.data_table.setItem(row_count, 1, item_value)
                        row_count += 1
            
            # Add a separator after each table except the last one
            if table_idx < len(table_list) - 1:
                self.data_table.insertRow(row_count)
                separator = QTableWidgetItem("────────────────────────────")
                separator.setBackground(QColor(240, 240, 240))  # Light gray background
                self.data_table.setItem(row_count, 0, separator)
                self.data_table.setSpan(row_count, 0, 1, 2)  # Span across both columns
                row_count += 1
        
        # Apply styling
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
        
        # Adjust column widths for better readability
        header = self.data_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

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
                # ITEMS SECTION: Group rows into sections if 3+ NULL values found
                self.section_title.setText("Items Section - Structured Format")
                
                row_count = 0
                current_section = "General"
                section_items = []
                
                for df_row_idx, row in df.iterrows():
                    # Check if this is a section header (3+ NULL values)
                    null_count = row.isna().sum()
                    if null_count >= 3 or (len(row) > 2 and null_count >= len(row) / 2):
                        # First, add the previous section if it has items
                        if section_items:
                            # Add a row for the section
                            self.data_table.insertRow(row_count)
                            section_key = QTableWidgetItem(f"SECTION: {current_section}")
                            section_key.setBackground(QColor(230, 230, 250))  # Light purple background
                            section_value = QTableWidgetItem(f"{len(section_items)} items")
                            self.data_table.setItem(row_count, 0, section_key)
                            self.data_table.setItem(row_count, 1, section_value)
                            row_count += 1
                            
                            # Add rows for each item in the section
                            for idx, item in enumerate(section_items):
                                self.data_table.insertRow(row_count)
                                item_key = QTableWidgetItem(f"  Item {idx+1}")
                                item_value = QTableWidgetItem(str(item))
                                self.data_table.setItem(row_count, 0, item_key)
                                self.data_table.setItem(row_count, 1, item_value)
                                row_count += 1
                            
                            # Reset for new section
                            section_items = []
                        
                        # Extract the new section name - concatenate all non-null values
                        section_parts = [
                            str(val) for val in row if not pd.isna(val) and str(val).strip()
                        ]
                        current_section = " ".join(section_parts) if section_parts else "Unnamed Section"
                    else:
                        # This is a regular item row - create a dictionary of column values
                        item_data = {}
                        for col_idx, value in enumerate(row):
                            col_name = f"C{col_idx+1}" if isinstance(df.columns[col_idx], int) else str(df.columns[col_idx])
                            if not pd.isna(value) and str(value).strip():
                                item_data[col_name] = str(value)
                        
                        if item_data:  # Only add if there's data
                            section_items.append(item_data)
                
                # Add the last section if it has items
                if section_items:
                    self.data_table.insertRow(row_count)
                    section_key = QTableWidgetItem(f"SECTION: {current_section}")
                    section_key.setBackground(QColor(230, 230, 250))  # Light purple background
                    section_value = QTableWidgetItem(f"{len(section_items)} items")
                    self.data_table.setItem(row_count, 0, section_key)
                    self.data_table.setItem(row_count, 1, section_value)
                    row_count += 1
                    
                    for idx, item in enumerate(section_items):
                        self.data_table.insertRow(row_count)
                        item_key = QTableWidgetItem(f"  Item {idx+1}")
                        item_value = QTableWidgetItem(str(item))
                        self.data_table.setItem(row_count, 0, item_key)
                        self.data_table.setItem(row_count, 1, item_value)
                        row_count += 1
            
            elif section == 'summary':
                # SUMMARY SECTION: First column as key, second as value
                self.section_title.setText("Summary Section - Key-Value Format")
                
                row_count = 0
                # Check if the dataframe has 2 or more columns
                if len(df.columns) >= 2:
                    # Use first column as key, second as value
                    for df_row_idx, row in df.iterrows():
                        key = str(row.iloc[0]) if not pd.isna(row.iloc[0]) else "Unknown"
                        value = str(row.iloc[1]) if not pd.isna(row.iloc[1]) else ""
                        
                        if key.strip():  # Only add if the key is not empty
                            self.data_table.insertRow(row_count)
                            key_item = QTableWidgetItem(key)
                            value_item = QTableWidgetItem(value)
                            self.data_table.setItem(row_count, 0, key_item)
                            self.data_table.setItem(row_count, 1, value_item)
                            row_count += 1
                else:
                    # Just label the columns
                    for col_idx, col_name in enumerate(df.columns):
                        col_label = f"C{col_idx+1}" if isinstance(col_name, int) else str(col_name)
                        
                        self.data_table.insertRow(row_count)
                        key_item = QTableWidgetItem("Column Name")
                        value_item = QTableWidgetItem(col_label)
                        self.data_table.setItem(row_count, 0, key_item)
                        self.data_table.setItem(row_count, 1, value_item)
                        row_count += 1
                        
                        # Add sample values from this column
                        for df_row_idx, value in enumerate(df[col_name]):
                            if not pd.isna(value):
                                self.data_table.insertRow(row_count)
                                key_item = QTableWidgetItem(f"  Row {df_row_idx+1}")
                                value_item = QTableWidgetItem(str(value))
                                self.data_table.setItem(row_count, 0, key_item)
                                self.data_table.setItem(row_count, 1, value_item)
                                row_count += 1
            
            # Apply tree-like styling to the first column
            for row in range(self.data_table.rowCount()):
                item = self.data_table.item(row, 0)
                if item and (item.text().startswith('  ') or item.text().startswith('SECTION:')):
                    font = item.font()
                    if item.text().startswith('SECTION:'):
                        font.setBold(True)
                    item.setFont(font)
            
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
        print("\n[DEBUG] Emitting save_template_signal from save_template method")
        
        # PySide6 signals don't have a receivers() method
        # We have to just emit the signal and hope something is connected
        try:
            # Emit the signal - in PySide6 we can't check if anyone is listening
            self.save_template_signal.emit()
            print("[DEBUG] save_template_signal emitted")
        except Exception as e:
            print(f"[ERROR] Failed to emit save_template_signal: {str(e)}")
            # Show error message to user if signal emission fails
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Error")
            msg.setText("Cannot save template")
            msg.setInformativeText(f"An error occurred: {str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()

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
        
        # Default values depend on section
        default_row_tol = 15 if section == 'items' else 10 if section == 'summary' else 5
        
        # Row tolerance parameter
        row_tol_input = QSpinBox()
        row_tol_input.setMinimum(1)
        row_tol_input.setMaximum(50)
        row_tol_input.setValue(default_row_tol)
        row_tol_input.setToolTip("Tolerance for grouping text into rows (higher value = more text in same row)")
        layout.addRow("Row Tolerance:", row_tol_input)
        
        # Add tooltip explanation
        row_tol_explanation = QLabel("Higher values group more text into the same row")
        row_tol_explanation.setStyleSheet("color: #bdc3c7; font-size: 9pt; font-style: italic;")
        layout.addRow("", row_tol_explanation)
        
        # Split text parameter
        split_text_input = QCheckBox("Enable")
        split_text_input.setChecked(True)
        split_text_input.setToolTip("Split text that may contain multiple values")
        layout.addRow("Split Text:", split_text_input)
        
        # Strip text parameter
        strip_text_input = QLineEdit()
        strip_text_input.setText("\\n")  # Default value
        strip_text_input.setToolTip("Characters to strip from text (use \\n for newlines)")
        layout.addRow("Strip Text:", strip_text_input)
        
        # Flavor parameter
        flavor_label = QLabel("Extraction Method: Stream")
        flavor_label.setToolTip("The extraction method is fixed to 'stream' for best results")
        layout.addRow("Extraction Method:", flavor_label)
        
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
                
                print(f"\nRetrying single table extraction with new parameters: {single_table_params}")
                
                try:
                    # Extract data
                    tables = pypdf_table_extraction.read_pdf(self.pdf_path, **single_table_params)
                    
                    if tables and len(tables) > 0 and tables[0].df is not None:
                        df = tables[0].df
                        
                        print(f"\nRaw extracted data for {section} with new parameters:")
                        print(df)
                        
                        # Clean up the DataFrame
                        df = df.replace(r'^\s*$', pd.NA, regex=True)
                        df = df.dropna(how='all')
                        df = df.dropna(axis=1, how='all')
                        
                        if not df.empty:
                            print(f"\nSuccessfully extracted {section} data with new parameters")
                            print(f"Final DataFrame shape: {df.shape}")
                            
                            # Store the newly extracted data for later use (including JSON download)
                            if section == 'header':
                                self.header_df = [df]  # Store as list for consistency
                            elif section == 'items':
                                self.item_details_df = [df]  # Store as list for consistency
                            elif section == 'summary':
                                self.summary_df = [df]  # Store as list for consistency
                            
                            self.update_data_table(df, section)
                        else:
                            print(f"\nNo valid data found in {section} section after cleaning")
                            # Clear any existing data for this section
                            if section == 'header':
                                self.header_df = None
                            elif section == 'items':
                                self.item_details_df = None
                            elif section == 'summary':
                                self.summary_df = None
                            self.update_data_table(None, section)
                    else:
                        print(f"\nNo data found in {section} section with new parameters")
                        # Clear any existing data for this section
                        if section == 'header':
                            self.header_df = None
                        elif section == 'items':
                            self.item_details_df = None
                        elif section == 'summary':
                            self.summary_df = None
                        self.update_data_table(None, section)
                except Exception as e:
                    print(f"\nError extracting {section} data with new parameters: {str(e)}")
                    self.update_data_table(None, section)
        else:
            # User canceled parameter adjustment
            print("\nUser canceled parameter adjustment")
            # Still need to display the original data
            if section == 'header':
                if self.header_df is not None:
                    if isinstance(self.header_df, list):
                        self.update_data_table_for_header(self.header_df, section_type=section)
                    else:
                        self.update_data_table(self.header_df, section)
                else:
                    self.update_data_table(None, section)
            elif section == 'items':
                if self.item_details_df is not None:
                    if isinstance(self.item_details_df, list):
                        self.update_data_table_for_header(self.item_details_df, section_type=section)
                    else:
                        self.update_data_table(self.item_details_df, section)
                else:
                    self.update_data_table(None, section)
            elif section == 'summary':
                if self.summary_df is not None:
                    if isinstance(self.summary_df, list):
                        self.update_data_table_for_header(self.summary_df, section_type=section)
                    else:
                        self.update_data_table(self.summary_df, section)
                else:
                    self.update_data_table(None, section)

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
        
        # If we have the necessary data, call extract_with_new_params
        if table_areas and current_section:
            print(f"\nShowing custom extraction settings for {current_section}")
            self.extract_with_new_params(current_section, table_areas, column_lines)
        else:
            # Show a message if no regions are defined
            msg = self.create_styled_messagebox(
                title="No Regions Defined",
                text="No table regions are defined for the current section.",
                informative_text="Please define table regions before adjusting extraction parameters."
            )
            msg.setIcon(QMessageBox.Information)
            msg.exec()

    def download_json(self):
        """Save the current section data as a JSON file"""
        from PySide6.QtWidgets import QFileDialog
        import json
        import os

        # Get the current section based on the navigation
        sections = ['header', 'items', 'summary']
        current_section = sections[self.current_page]
        
        # Get the dataframe for the current section
        df_to_save = None
        if current_section == 'header':
            df_to_save = self.header_df
        elif current_section == 'items':
            df_to_save = self.item_details_df
        elif current_section == 'summary':
            df_to_save = self.summary_df
        
        if df_to_save is None:
            # Show an error message if no data is available
            msg = self.create_styled_messagebox(
                title="No Data Available",
                text="No data available for the current section.",
                informative_text="Please extract data before trying to download."
            )
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
            return
        
        # Determine default filename based on section
        pdf_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
        default_filename = f"{pdf_name}_{current_section}.json"
        
        # Open file dialog to get save location
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save JSON File",
            default_filename,
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return  # User canceled
        
        try:
            # Convert dataframe to JSON
            if isinstance(df_to_save, list):
                # For new format (list of dataframes)
                json_data = []
                for i, df in enumerate(df_to_save):
                    table_dict = {'table_index': i}
                    # Convert DataFrame to dict for serialization
                    records = df.to_dict(orient='records')
                    table_dict['data'] = records
                    json_data.append(table_dict)
            else:
                # For old format (single dataframe)
                json_data = df_to_save.to_dict(orient='records')
            
            # Save the JSON to file
            with open(file_path, 'w') as f:
                json.dump(json_data, f, indent=2)
            
            # Show success message
            msg = self.create_styled_messagebox(
                title="JSON Saved",
                text=f"JSON data for {current_section} section saved successfully.",
                informative_text=f"File saved to:\n{file_path}"
            )
            msg.setIcon(QMessageBox.Information)
            msg.exec()
            
        except Exception as e:
            # Show error message if something went wrong
            msg = self.create_styled_messagebox(
                title="Error Saving JSON",
                text=f"An error occurred while saving the JSON file:",
                informative_text=str(e)
            )
            msg.setIcon(QMessageBox.Critical)
            msg.exec() 