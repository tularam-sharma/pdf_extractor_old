from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QScrollArea, QFrame, QStackedWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
                             QSpinBox, QCheckBox, QLineEdit, QMessageBox, QDialogButtonBox, QSpacerItem,
                             QComboBox, QGroupBox, QFileDialog)
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import (QFont, QImage, QPixmap, QCursor, QPainter,
                          QPen, QColor, QBrush)
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
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(1, 1)  # Ensure minimum size to prevent deletion
        self._pixmap = None
        self.offset = QPoint(0, 0)  # Initialize offset
        self.scaled_pixmap = None  # Initialize scaled_pixmap

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        super().setPixmap(pixmap)
        self.adjustPixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjustPixmap()

    def adjustPixmap(self):
        if self._pixmap is not None:
            self.scaled_pixmap = self._pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            super().setPixmap(self.scaled_pixmap)

    def mapToPixmap(self, pos):
        if self._pixmap is None:
            return pos

        # Get the current displayed pixmap size
        current_size = self.pixmap().size()
        original_size = self._pixmap.size()

        # Calculate scaling factors
        scale_x = original_size.width() / current_size.width()
        scale_y = original_size.height() / current_size.height()

        # Scale the position
        return QPoint(
            int(pos.x() * scale_x),
            int(pos.y() * scale_y)
        )

    def mapFromPixmap(self, pos):
        if self._pixmap is None:
            return pos

        # Get the current displayed pixmap size
        current_size = self.pixmap().size()
        original_size = self._pixmap.size()

        # Calculate scaling factors
        scale_x = current_size.width() / original_size.width()
        scale_y = current_size.height() / original_size.height()

        # Scale the position
        return QPoint(
            int(pos.x() * scale_x),
            int(pos.y() * scale_y)
        )

    def paintEvent(self, event):
        if self._pixmap is not None:
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
        self.current_section = 'header'.lower()  # Default to header section (lowercase)
        self.current_page = 0  # Initialize current_page to 0 (header section)

        # Initialize PDF-related attributes
        self.pdf_document = None
        self.pdf_label = None
        self.drawing_pixmap = None

        # Initialize UI-related attributes
        self.data_table = None
        self.section_label = None
        self.nav_buttons = None
        self.back_button = None
        self.save_template_btn = None
        self.download_json_btn = None
        self.section_title = None
        self.retry_btn = None

        # Initialize extraction parameters
        self.extraction_params = {
            'header': {'row_tol': 5},
            'items': {'row_tol': 15},
            'summary': {'row_tol': 10},
            'split_text': True,
            'strip_text': '\n',
            'flavor': 'stream'
        }

        # Initialize UI
        self.initUI()

        # Set the initial section title
        self.section_title.setText("Header Section")

        # Load the PDF
        self.load_pdf()

        # Show initial data based on current section
        try:
            if self.current_section == 'header' and self.header_df is not None:
                # Check if header_df is a list or DataFrame
                if isinstance(self.header_df, list):
                    self.update_data_table_for_header(self.header_df, section_type='header')
                else:
                    self.update_data_table(self.header_df, 'header')
            elif self.current_section == 'items' and self.item_details_df is not None:
                # Check if item_details_df is a list or DataFrame
                if isinstance(self.item_details_df, list):
                    self.update_data_table_for_header(self.item_details_df, section_type='items')
                else:
                    self.update_data_table(self.item_details_df, 'items')
            elif self.current_section == 'summary' and self.summary_df is not None:
                # Check if summary_df is a list or DataFrame
                if isinstance(self.summary_df, list):
                    self.update_data_table_for_header(self.summary_df, section_type='summary')
                else:
                    self.update_data_table(self.summary_df, 'summary')
        except Exception as e:
            print(f"Error displaying initial data: {str(e)}")
            import traceback
            traceback.print_exc()

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

        self.setLayout(layout)

    def load_pdf(self):
        """Load and display the PDF"""
        try:
            # Open the PDF document
            self.pdf_document = fitz.open(self.pdf_path)

            # Get the first page
            page = self.pdf_document[0]

            # Render the page to a pixmap
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

            # Convert to QImage and then to QPixmap
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            self.drawing_pixmap = QPixmap.fromImage(img)

            # Set the pixmap to the PDF label
            if self.pdf_label is not None:
                self.pdf_label.setPixmap(self.drawing_pixmap)

            # Draw the sections
            self.draw_sections()

            # Extract and update data for the current section
            self.extract_and_update_section_data()

        except Exception as e:
            print(f"Error loading PDF: {str(e)}")
            import traceback
            traceback.print_exc()

    def draw_sections(self):
        """Draw sections on the PDF view"""
        try:
            pixmap = self.drawing_pixmap.copy()
            painter = QPainter(pixmap)

            # Set up the painter
            painter.setRenderHint(QPainter.Antialiasing)

            # Draw each section
            for section, color in [('header', QColor(255, 0, 0, 100)),
                                 ('items', QColor(0, 255, 0, 100)),
                                 ('summary', QColor(0, 0, 255, 100))]:

                if section in self.regions:
                    for rect in self.regions[section]:
                        # Draw the rectangle directly using QRect object
                        painter.setPen(QPen(color, 2))
                        painter.setBrush(QBrush(color))
                        painter.drawRect(rect)

                        # Optionally add a label
                        painter.setPen(Qt.black)
                        font = QFont("Arial", 10, QFont.Bold)
                        painter.setFont(font)
                        label = f"{section[0].upper()}"  # H, I, S, etc.
                        painter.drawText(rect.topLeft() + QPoint(5, 15), label)

            # End painting
            painter.end()

            # Update the PDF label
            if self.pdf_label is not None:
                self.pdf_label.setPixmap(pixmap)

        except Exception as e:
            print(f"Error in draw_sections: {str(e)}")
            import traceback
            traceback.print_exc()

    def extract_and_update_section_data(self):
        sections = ['header', 'items', 'summary']
        if hasattr(self, 'current_page') and 0 <= self.current_page < len(sections):
            section = sections[self.current_page]
            # Make sure current_section is in sync with current_page
            self.current_section = section.lower()  # Ensure lowercase

            # Update the section title in the UI
            if section.lower() == 'header':
                self.section_title.setText("Header Section")
            elif section.lower() == 'items':
                self.section_title.setText("Items Section")
            elif section.lower() == 'summary':
                self.section_title.setText("Summary Section")

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

                                    # # Clean up the DataFrame
                                    # table_df = table_df.replace(r'^\s*$', pd.NA, regex=True)
                                    # table_df = table_df.dropna(how='all')
                                    # table_df = table_df.dropna(axis=1, how='all')

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

                                        # # Clean up the DataFrame
                                        # table_df = table_df.replace(r'^\s*$', pd.NA, regex=True)
                                        # table_df = table_df.dropna(how='all')
                                        # table_df = table_df.dropna(axis=1, how='all')

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

                                # # Clean up the DataFrame
                                # df = df.replace(r'^\s*$', pd.NA, regex=True)  # Replace empty strings with NA
                                # df = df.dropna(how='all')  # Drop rows that are all NA
                                # df = df.dropna(axis=1, how='all')  # Drop columns that are all NA

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
                'flavor': 'stream'
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

        # Check if df is a list (multiple tables)
        if isinstance(df, list):
            # Handle list of DataFrames
            if df and any(isinstance(item, pd.DataFrame) and not item.empty for item in df):
                # Use the special multi-table display method
                self.update_data_table_for_header(df, section_type=section)
                return
            else:
                # Empty list or list with empty DataFrames, show no data
                self.section_title.setText(f"No {section.title()} Data Available")
                self.data_table.setColumnCount(2)
                self.data_table.setHorizontalHeaderLabels(["Key", "Value"])
                self.data_table.insertRow(0)
                message_item = QTableWidgetItem(f"No data available for the {section} section")
                self.data_table.setItem(0, 0, message_item)
                self.data_table.setSpan(0, 0, 1, 2)  # Span across both columns
                return

        # If df is a DataFrame and not empty, continue with normal processing
        if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
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
        sections = ['header', 'items', 'summary']
        self.current_section = sections[self.current_page].lower()  # Ensure lowercase

        # Update the section title in the UI
        if self.current_section == 'header':
            self.section_title.setText("Header Section")
        elif self.current_section == 'items':
            self.section_title.setText("Items Section")
        elif self.current_section == 'summary':
            self.section_title.setText("Summary Section")

        self.load_pdf()

        # Update the data table based on the current section
        try:
            if self.current_section == 'header' and self.header_df is not None:
                # Check if header_df is a list or DataFrame
                if isinstance(self.header_df, list):
                    self.update_data_table_for_header(self.header_df, section_type='header')
                else:
                    self.update_data_table(self.header_df, 'header')
            elif self.current_section == 'items' and self.item_details_df is not None:
                # Check if item_details_df is a list or DataFrame
                if isinstance(self.item_details_df, list):
                    self.update_data_table_for_header(self.item_details_df, section_type='items')
                else:
                    self.update_data_table(self.item_details_df, 'items')
            elif self.current_section == 'summary' and self.summary_df is not None:
                # Check if summary_df is a list or DataFrame
                if isinstance(self.summary_df, list):
                    self.update_data_table_for_header(self.summary_df, section_type='summary')
                else:
                    self.update_data_table(self.summary_df, 'summary')
        except Exception as e:
            print(f"Error updating data table in next_section: {str(e)}")
            import traceback
            traceback.print_exc()

    def prev_section(self):
        self.current_page = (self.current_page - 1) % 3
        sections = ['header', 'items', 'summary']
        self.current_section = sections[self.current_page].lower()  # Ensure lowercase

        # Update the section title in the UI
        if self.current_section == 'header':
            self.section_title.setText("Header Section")
        elif self.current_section == 'items':
            self.section_title.setText("Items Section")
        elif self.current_section == 'summary':
            self.section_title.setText("Summary Section")

        self.load_pdf()

        # Update the data table based on the current section
        try:
            if self.current_section == 'header' and self.header_df is not None:
                # Check if header_df is a list or DataFrame
                if isinstance(self.header_df, list):
                    self.update_data_table_for_header(self.header_df, section_type='header')
                else:
                    self.update_data_table(self.header_df, 'header')
            elif self.current_section == 'items' and self.item_details_df is not None:
                # Check if item_details_df is a list or DataFrame
                if isinstance(self.item_details_df, list):
                    self.update_data_table_for_header(self.item_details_df, section_type='items')
                else:
                    self.update_data_table(self.item_details_df, 'items')
            elif self.current_section == 'summary' and self.summary_df is not None:
                # Check if summary_df is a list or DataFrame
                if isinstance(self.summary_df, list):
                    self.update_data_table_for_header(self.summary_df, section_type='summary')
                else:
                    self.update_data_table(self.summary_df, 'summary')
        except Exception as e:
            print(f"Error updating data table in prev_section: {str(e)}")
            import traceback
            traceback.print_exc()

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
                    'flavor': 'stream'
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

            # Add extraction parameters to config
            config['extraction_params'] = self.extraction_params

            print(f"\nFinal extraction parameters being saved to template:")
            for section in ['header', 'items', 'summary']:
                print(f"  {section.title()} row_tol: {self.extraction_params[section]['row_tol']}")

            print(f"  split_text: {self.extraction_params['split_text']}")
            print(f"  strip_text: {repr(self.extraction_params['strip_text'])}")
            print(f"  flavor: {self.extraction_params['flavor']}")

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
        # Ensure section is a string and is one of the valid sections
        if not isinstance(section, str):
            section = str(section)

        # Normalize section name to one of the valid options
        valid_sections = ['header', 'items', 'summary']
        if section.lower() not in valid_sections:
            print(f"Warning: Invalid section name '{section}'. Using 'header' as default.")
            section = 'header'
        else:
            section = section.lower()

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
        current_strip_text = "\n"
        if hasattr(self, 'extraction_params') and 'strip_text' in self.extraction_params:
            # Convert newlines back to escaped form for display
            current_strip_text = repr(self.extraction_params['strip_text']).strip("'")
            if current_strip_text == "\n":
                current_strip_text = "\n"

        # Strip text parameter
        strip_text_input = QLineEdit()
        strip_text_input.setText(current_strip_text)
        strip_text_input.setToolTip("Characters to strip from text (use \n for newlines)")
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
                'strip_text': strip_text_input.text(),
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


            # Print current extraction parameters for debugging
            print(f"\nUpdated extraction parameters:")
            print(f"  {section.title()} row_tol: {self.extraction_params[section]['row_tol']}")
            print(f"  split_text: {self.extraction_params['split_text']}")
            print(f"  strip_text: {repr(self.extraction_params['strip_text'])}")

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

                        break
            except Exception as e:
                print(f"Error storing extraction parameters in main window: {str(e)}")
                import traceback
                traceback.print_exc()

            # Get the existing table areas and column lines from the current section
            existing_table_areas = []
            existing_column_lines = []

            # Use the table_areas and column_lines passed to this method
            # These should be the same as defined in the section
            if table_areas and column_lines:
                existing_table_areas = table_areas
                existing_column_lines = column_lines
                print(f"Using provided table areas and column lines for {section}")
            # If no table areas or column lines provided, try to get them from the current section
            elif section in self.regions and self.regions[section]:
                # Get the first page of the PDF to calculate scaling
                doc = fitz.open(self.pdf_path)
                page = doc[0]
                page_width = page.rect.width
                page_height = page.rect.height

                # Calculate scaling factors between display and PDF coordinates
                scale_x = page_width / self.pdf_label.pixmap().width()
                scale_y = page_height / self.pdf_label.pixmap().height()

                # Process each region for the current section
                for idx, rect in enumerate(self.regions[section]):
                    # Convert rectangle coordinates to PDF space with proper scaling
                    x1 = rect.x() * scale_x
                    y1 = page_height - (rect.y() * scale_y)
                    x2 = (rect.x() + rect.width()) * scale_x
                    y2 = page_height - ((rect.y() + rect.height()) * scale_y)

                    table_area = f"{x1},{y1},{x2},{y2}"
                    existing_table_areas.append(table_area)

                    # Find column lines specific to this region
                    region_columns = []
                    if section in self.column_lines and self.column_lines[section]:
                        for line in self.column_lines[section]:
                            # Check if the line has a region index and matches current region
                            if len(line) == 3 and line[2] == idx:
                                region_columns.append(line[0].x() * scale_x)
                            # Handle old format without region index - associate with first region
                            elif len(line) == 2 and idx == 0:
                                region_columns.append(line[0].x() * scale_x)

                    if region_columns:
                        # Sort column lines by x-coordinate and join as comma-separated string
                        col_str = ','.join([str(x) for x in sorted(region_columns)])
                        existing_column_lines.append(col_str)
                    else:
                        # Empty string for regions with no column lines
                        existing_column_lines.append('')

                print(f"Using existing table areas and column lines for {section}")

            # Process for multiple tables
            if len(existing_table_areas) > 1:
                processed_tables = []

                for idx, (table_area, col_line) in enumerate(zip(existing_table_areas, existing_column_lines)):
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

                            # # Clean up the DataFrame
                            # table_df = table_df.replace(r'^\s*$', pd.NA, regex=True)
                            # table_df = table_df.dropna(how='all')
                            # table_df = table_df.dropna(axis=1, how='all')


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
            elif len(existing_table_areas) == 1:
                # Single table extraction with new parameters
                single_table_params = {
                    'pages': '1',
                    'table_areas': existing_table_areas,
                    'columns': existing_column_lines if existing_column_lines else None,
                    'split_text': new_params['split_text'],
                    'strip_text': new_params['strip_text'],
                    'flavor': new_params['flavor'],
                    'row_tol': new_params['row_tol']
                }
                print(f"\nRetrying single table extraction with new parameters: {single_table_params}")

                try:
                    # Extract table with new parameters
                    table_result = pypdf_table_extraction.read_pdf(self.pdf_path, **single_table_params)
                except Exception as e:
                    print(f"Error extracting table: {str(e)}")
            else:
                print(f"No table areas defined for {section} section")
                return False

                if table_result and len(table_result) > 0 and table_result[0].df is not None:
                    table_df = table_result[0].df

                    print(f"Raw data extracted:")
                    print(table_df)

                    # # Clean up the DataFrame
                    # table_df = table_df.replace(r'^\s*$', pd.NA, regex=True)
                    # table_df = table_df.dropna(how='all')
                    # table_df = table_df.dropna(axis=1, how='all')

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

            return True

        return False

    def show_custom_settings(self):
        """Show the custom settings dialog for the current section"""
        # Get the current section directly
        current_section = self.current_section

        # Ensure current_section is a string and is one of the valid sections
        if not isinstance(current_section, str):
            current_section = str(current_section)

        # Normalize section name to one of the valid options
        valid_sections = ['header', 'items', 'summary']
        if current_section.lower() not in valid_sections:
            print(f"Warning: Invalid section name '{current_section}'. Using 'header' as default.")
            current_section = 'header'
        else:
            current_section = current_section.lower()

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

            # Store the result of extract_with_new_params when the button is clicked
            result = [False]  # Use a list to store the result (mutable)

            def on_params_btn_clicked():
                # Call extract_with_new_params and store the result
                result[0] = self.extract_with_new_params(current_section, table_areas, column_lines)
                dialog.accept()  # Close this dialog when clicked

            params_btn.clicked.connect(on_params_btn_clicked)
            buttons_layout.addWidget(params_btn)

            # Add buttons layout to main layout
            layout.addLayout(buttons_layout)

            # Show the dialog
            dialog.exec()

            # Return the result from extract_with_new_params
            return result[0]
        else:
            # If no table areas defined, go directly to extraction parameters
            return self.extract_with_new_params(current_section, [], [])



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
                    if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
                        export_data['header'].append(df.fillna('').to_dict('records'))
            elif isinstance(self.header_df, pd.DataFrame) and not self.header_df.empty:
                export_data['header'].append(self.header_df.fillna('').to_dict('records'))

        # Convert items data to JSON-serializable format
        if self.item_details_df is not None:
            if isinstance(self.item_details_df, list):
                for i, df in enumerate(self.item_details_df):
                    if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
                        export_data['items'].append(df.fillna('').to_dict('records'))
            elif isinstance(self.item_details_df, pd.DataFrame) and not self.item_details_df.empty:
                export_data['items'].append(self.item_details_df.fillna('').to_dict('records'))

        # Convert summary data to JSON-serializable format
        if self.summary_df is not None:
            if isinstance(self.summary_df, list):
                for i, df in enumerate(self.summary_df):
                    if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
                        export_data['summary'].append(df.fillna('').to_dict('records'))
            elif isinstance(self.summary_df, pd.DataFrame) and not self.summary_df.empty:
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