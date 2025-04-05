import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFileDialog, QScrollArea, QStackedWidget, QMessageBox, QDialog, QRadioButton, QButtonGroup)
from PySide6.QtCore import Qt, QRect, QPoint, QSize
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QImage, QFont
import fitz  # PyMuPDF
from PIL import Image
import io
from PySide6.QtCore import Signal
from invoice_section_viewer import InvoiceSectionViewer
import pandas as pd
import pypdf_table_extraction

class RegionType:
    HEADER = "header"
    ITEMS = "items"
    SUMMARY = "summary"

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

    def mousePressEvent(self, event):
        if self.parent and event.button() == Qt.LeftButton:
            pos = event.pos()
            if (pos - self.offset).x() >= 0 and (pos - self.offset).y() >= 0:
                self.parent.handle_mouse_press(self.mapToPixmap(pos))

    def mouseMoveEvent(self, event):
        if self.parent:
            pos = event.pos()
            if (pos - self.offset).x() >= 0 and (pos - self.offset).y() >= 0:
                self.parent.handle_mouse_move(self.mapToPixmap(pos))

    def mouseReleaseEvent(self, event):
        if self.parent and event.button() == Qt.LeftButton:
            pos = event.pos()
            if (pos - self.offset).x() >= 0 and (pos - self.offset).y() >= 0:
                self.parent.handle_mouse_release(self.mapToPixmap(pos))

    def paintEvent(self, event):
        if not self.scaled_pixmap:
            super().paintEvent(event)
            return
            
        painter = QPainter(self)
        painter.drawPixmap(self.offset, self.scaled_pixmap)
        
        # Draw regions
        if self.parent:
            # Define section titles for labels - shorter versions
            titles = {
                'header': "H",
                'items': "I",
                'summary': "S"
            }
            
            # First draw all regions from the regions dict (for backward compatibility)
            for region_type, rects in self.parent.regions.items():
                color = self.parent.get_region_color(region_type)
                pen = QPen(color, 2, Qt.SolidLine)
                painter.setPen(pen)
                
                for i, rect in enumerate(rects):
                    # Convert dictionary to QRect if needed
                    if isinstance(rect, dict):
                        if 'x' in rect and 'y' in rect and 'width' in rect and 'height' in rect:
                            rect = QRect(rect['x'], rect['y'], rect['width'], rect['height'])
                        elif 'x1' in rect and 'y1' in rect and 'x2' in rect and 'y2' in rect:
                            rect = QRect(rect['x1'], rect['y1'], rect['x2'] - rect['x1'], rect['y2'] - rect['y1'])
                    
                    scaled_rect = QRect(
                        self.mapFromPixmap(rect.topLeft()),
                        self.mapFromPixmap(rect.bottomRight())
                    )
                    
                    # If drawing a column and this is the active rectangle, use a stronger fill
                    if (self.parent.drawing_column and hasattr(self.parent, 'active_rect_index') and
                        hasattr(self.parent, 'active_region_type') and
                        region_type == self.parent.active_region_type and i == self.parent.active_rect_index):
                        # Highlight the active rectangle with a semi-transparent fill
                        painter.fillRect(scaled_rect, QColor(color.red(), color.green(), color.blue(), 50))
                    
                    # Draw the rectangle
                    painter.drawRect(scaled_rect)
                    
                    # Draw label text on the left side of the rectangle
                    painter.setPen(Qt.black)
                    font = QFont("Arial", 10, QFont.Bold)
                    painter.setFont(font)
                    
                    # Create short label with section type and table number
                    label_text = titles.get(region_type, region_type[0].upper())
                    label_text += str(i+1)  # Add table number
                    
                    # Position the label on the left side of the rectangle
                    label_x = scaled_rect.left() - 30  # 30px to the left of the rectangle
                    label_y = scaled_rect.top() + scaled_rect.height() // 2  # Center vertically
                    
                    # Draw connecting line from label to rectangle
                    connecting_line_start = QPoint(label_x + 25, label_y)
                    connecting_line_end = QPoint(scaled_rect.left(), label_y)
                    painter.drawLine(connecting_line_start, connecting_line_end)
                    
                    # Create a background for the label for better readability
                    label_bg_rect = QRect(label_x, label_y - 10, 25, 20)
                    label_bg_color = QColor(255, 255, 255, 200)  # Semi-transparent white
                    painter.fillRect(label_bg_rect, label_bg_color)
                    
                    # Draw a border around the label background
                    painter.setPen(Qt.black)
                    painter.drawRect(label_bg_rect)
                    
                    # Draw the label text
                    painter.drawText(label_bg_rect, Qt.AlignCenter, label_text)
                    
                    # Reset pen color for next rectangle
                    painter.setPen(pen)
            
            # Draw column lines using the structured table_areas data if available
            # This ensures column lines are properly associated with their tables
            if hasattr(self.parent, 'table_areas') and self.parent.table_areas:
                # Draw column lines for all tables
                for table_label, table_info in self.parent.table_areas.items():
                    region_type = table_info['type']
                    rect = table_info['rect']
                    columns = table_info.get('columns', [])
                    
                    if columns:
                        color = self.parent.get_region_color(region_type)
                        pen = QPen(color, 2, Qt.DashLine)
                        painter.setPen(pen)
                        
                        # Draw each column line
                        for col_idx, x_pos in enumerate(sorted(columns)):
                            start_point = QPoint(x_pos, rect.top())
                            end_point = QPoint(x_pos, rect.bottom())
                            
                            start = self.mapFromPixmap(start_point)
                            end = self.mapFromPixmap(end_point)
                            painter.drawLine(start, end)
                            
                            # Add a column number label at the top of the line
                            painter.setPen(Qt.black)
                            font = QFont("Arial", 8, QFont.Bold)
                            painter.setFont(font)
                            
                            # Draw column number label
                            label_text = f"C{col_idx+1}"
                            label_x = start.x() + 2  # Slightly to the right of the line
                            label_y = start.y() - 15  # Above the line
                            
                            # Create a small background for the column label
                            label_bg_rect = QRect(label_x, label_y, 20, 15)
                            label_bg_color = QColor(255, 255, 255, 200)  # Semi-transparent white
                            painter.fillRect(label_bg_rect, label_bg_color)
                            
                            # Draw the label text
                            painter.drawText(label_bg_rect, Qt.AlignCenter, label_text)
                            
                            # Reset pen for next line
                            painter.setPen(pen)
            else:
                # Fall back to old method for drawing column lines
                for region_type, lines in self.parent.column_lines.items():
                    color = self.parent.get_region_color(region_type)
                    pen = QPen(color, 2, Qt.DashLine)
                    painter.setPen(pen)
                    
                    # Group lines by rectangle they belong to
                    lines_by_rect = {}
                    for idx, line in enumerate(lines):
                        # Check if line has rect_index (new format)
                        if len(line) == 3:
                            start, end, rect_index = line
                            if rect_index not in lines_by_rect:
                                lines_by_rect[rect_index] = []
                            lines_by_rect[rect_index].append((idx, start, end))
                        else:
                            start, end = line
                            # Default to rectangle 0 for old format
                            if 0 not in lines_by_rect:
                                lines_by_rect[0] = []
                            lines_by_rect[0].append((idx, start, end))
                        
                        # Convert dictionary points to QPoint if needed
                        if isinstance(start, dict) and 'x' in start:
                            start = QPoint(start['x'], start['y'])
                        if isinstance(end, dict) and 'x' in end:
                            end = QPoint(end['x'], end['y'])
                        
                        start = self.mapFromPixmap(start)
                        end = self.mapFromPixmap(end)
                        painter.drawLine(start, end)
                        
                        # Add a column number label at the top of the line
                        painter.setPen(Qt.black)
                        font = QFont("Arial", 8, QFont.Bold)
                        painter.setFont(font)
                        
                        # Calculate column number within its rectangle group
                        col_number = 1
                        if len(line) == 3:
                            rect_idx = line[2]
                            # Count how many lines in this rectangle have x position less than this one
                            col_number = sum(1 for l in lines if len(l) == 3 and l[2] == rect_idx and l[0].x() < line[0].x()) + 1
                        
                        # Draw column number label
                        label_text = f"C{col_number}"
                        label_x = start.x() + 2  # Slightly to the right of the line
                        label_y = start.y() - 15  # Above the line
                        
                        # Create a small background for the column label
                        label_bg_rect = QRect(label_x, label_y, 20, 15)
                        label_bg_color = QColor(255, 255, 255, 200)  # Semi-transparent white
                        painter.fillRect(label_bg_rect, label_bg_color)
                        
                        # Draw the label text
                        painter.drawText(label_bg_rect, Qt.AlignCenter, label_text)
                        
                        # Reset pen for next line
                        painter.setPen(pen)
            
            # Draw current rectangle if drawing
            if self.parent.drawing and self.parent.start_point and self.parent.current_rect:
                color = self.parent.get_region_color(self.parent.current_region_type)
                pen = QPen(color, 2, Qt.SolidLine)
                painter.setPen(pen)
                scaled_rect = QRect(
                    self.mapFromPixmap(self.parent.current_rect.topLeft()),
                    self.mapFromPixmap(self.parent.current_rect.bottomRight())
                )
                painter.drawRect(scaled_rect)
                
                # Also show label for rectangle being drawn
                if self.parent.current_region_type:
                    painter.setPen(Qt.black)
                    font = QFont("Arial", 10, QFont.Bold)
                    painter.setFont(font)
                    
                    # Create short label text
                    region_type = self.parent.current_region_type
                    label_text = titles.get(region_type, region_type[0].upper())
                    if region_type == 'header' and self.parent.multi_table_mode:
                        label_text += str(len(self.parent.regions[region_type]) + 1)
                    else:
                        label_text += "1"
                    
                    # Position and draw the label on the left side of the rectangle being drawn
                    label_x = scaled_rect.left() - 30
                    label_y = scaled_rect.top() + scaled_rect.height() // 2
                    
                    # Create label background
                    label_bg_rect = QRect(label_x, label_y - 10, 25, 20)
                    label_bg_color = QColor(255, 255, 255, 200)
                    painter.fillRect(label_bg_rect, label_bg_color)
                    
                    # Draw border around label background
                    painter.setPen(Qt.black)
                    painter.drawRect(label_bg_rect)
                    
                    # Draw connecting line from label to rectangle
                    connecting_line_start = QPoint(label_x + 25, label_y)
                    connecting_line_end = QPoint(scaled_rect.left(), label_y)
                    painter.drawLine(connecting_line_start, connecting_line_end)
                    
                    # Draw the label text
                    painter.drawText(label_bg_rect, Qt.AlignCenter, label_text)
            
            # Draw current column line if drawing
            if (self.parent.drawing_column and self.parent.start_point and 
                hasattr(self.parent, 'current_pos') and hasattr(self.parent, 'current_rect')):
                # Use a dashed blue line for column preview
                pen = QPen(QColor(65, 105, 225), 2, Qt.DashLine)
                painter.setPen(pen)
                
                # Draw vertical line from top to bottom of the rectangle at mouse x position
                rect = self.parent.current_rect
                if rect:
                    # Keep x position within the rectangle boundaries
                    x_pos = max(rect.left(), min(self.parent.current_pos.x(), rect.right()))
                    start = self.mapFromPixmap(QPoint(x_pos, rect.top()))
                    end = self.mapFromPixmap(QPoint(x_pos, rect.bottom()))
                    painter.drawLine(start, end)
                    
                    # Add column number label for the preview
                    if hasattr(self.parent, 'active_region_type') and hasattr(self.parent, 'active_rect_index'):
                        region_type = self.parent.active_region_type
                        rect_idx = self.parent.active_rect_index
                        
                        if region_type and rect_idx is not None:
                            # Find the correct table in the table_areas
                            column_number = 1
                            for table_label, table_info in self.parent.table_areas.items():
                                if (table_info['type'] == region_type and 
                                    table_info['index'] == rect_idx):
                                    # Count columns to the left of the current position
                                    column_number = sum(1 for col_x in table_info.get('columns', []) 
                                                     if col_x < x_pos) + 1
                                    break
                            
                            # Draw the column number label
                            painter.setPen(Qt.black)
                            font = QFont("Arial", 8, QFont.Bold)
                            painter.setFont(font)
                            label_text = f"C{column_number}"
                            
                            # Create label with background
                            label_x = start.x() + 2
                            label_y = start.y() - 15
                            label_bg_rect = QRect(label_x, label_y, 20, 15)
                            label_bg_color = QColor(255, 255, 255, 200)
                            painter.fillRect(label_bg_rect, label_bg_color)
                            
                            # Draw the label text
                            painter.drawText(label_bg_rect, Qt.AlignCenter, label_text)

class PDFProcessor(QWidget):
    next_clicked = Signal()  # Signal to indicate next button was clicked

    def __init__(self):
        super().__init__()
        self.pdf_path = None
        self.multi_page_mode = False  # Track if we're in multi-page mode
        self.current_page_index = 0  # Track current page being configured
        self.page_regions = {}  # Store regions for each page
        self.page_column_lines = {}  # Store column lines for each page
        
        # Updated data structure for regions
        # Instead of a simple list, we'll use a dictionary to track tables in order
        self.regions = {
            'header': [],
            'items': [],
            'summary': []
        }
        
        # Store table info in a more structured way - will be populated when tables are drawn
        # Format: {table_label: {rect: QRect object, columns: list of x-coordinates}}
        self.table_areas = {}
        
        self.current_region_type = None
        self.drawing = False
        self.start_point = None
        self.current_rect = None
        
        # We'll keep column_lines for backward compatibility but use the table_areas for actual processing
        self.column_lines = {
            RegionType.HEADER: [],
            RegionType.ITEMS: [],
            RegionType.SUMMARY: []
        }
        
        self.drawing_column = False
        self.active_button = None
        self.multi_table_mode = False
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        
        # Top toolbar
        toolbar = QHBoxLayout()
        
        # Region selection buttons
        self.header_btn = QPushButton("Select Header Region")
        self.header_btn.clicked.connect(lambda: self.start_region_selection(RegionType.HEADER))
        self.items_btn = QPushButton("Select Items Region")
        self.items_btn.clicked.connect(lambda: self.start_region_selection(RegionType.ITEMS))
        self.summary_btn = QPushButton("Select Summary Region")
        self.summary_btn.clicked.connect(lambda: self.start_region_selection(RegionType.SUMMARY))
        
        # Multi-table mode button for header
        self.multi_table_btn = QPushButton("Multi-Table Mode: OFF")
        self.multi_table_btn.clicked.connect(self.toggle_multi_table_mode)
        self.multi_table_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 150px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:checked {
                background-color: #4169E1;
                color: white;
                border-color: #3159C1;
            }
        """)
        
        # Set button styles
        button_style = """
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 150px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:checked {
                background-color: #4169E1;
                color: white;
                border-color: #3159C1;
            }
        """
        self.header_btn.setStyleSheet(button_style)
        self.items_btn.setStyleSheet(button_style)
        self.summary_btn.setStyleSheet(button_style)
        
        toolbar.addWidget(self.header_btn)
        toolbar.addWidget(self.items_btn)
        toolbar.addWidget(self.summary_btn)
        toolbar.addWidget(self.multi_table_btn)
        
        # Column line button
        self.column_btn = QPushButton("Add Column Lines")
        self.column_btn.clicked.connect(self.start_column_drawing)
        self.column_btn.setStyleSheet(button_style)
        toolbar.addWidget(self.column_btn)
        
        # Clear current page button
        clear_page_btn = QPushButton("Clear Current Page")
        clear_page_btn.clicked.connect(self.clear_current_page)
        clear_page_btn.setStyleSheet(button_style)
        toolbar.addWidget(clear_page_btn)
        
        # Reset button (for full reset)
        reset_btn = QPushButton("Reset All")
        reset_btn.clicked.connect(self.clear_all)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #B71C1C;
            }
        """)
        toolbar.addWidget(reset_btn)
        
        layout.addLayout(toolbar)
        
        # Create a container for the PDF display and upload area
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        
        # PDF display area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(600)
        
        # Create upload area widget
        self.upload_area = QWidget()
        self.upload_area.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 2px dashed #ccc;
                border-radius: 8px;
                padding: 20px;
            }
            QLabel {
                color: #666;
                font-size: 16px;
            }
        """)
        upload_layout = QVBoxLayout(self.upload_area)
        
        # Add upload icon and text
        upload_icon = QLabel("📄")
        upload_icon.setAlignment(Qt.AlignCenter)
        upload_icon.setStyleSheet("font-size: 48px;")
        upload_text = QLabel("Drag and drop PDF file here\nor click to browse")
        upload_text.setAlignment(Qt.AlignCenter)
        upload_text.setWordWrap(True)
        
        upload_layout.addWidget(upload_icon)
        upload_layout.addWidget(upload_text)
        
        # Set up drag and drop
        self.upload_area.setAcceptDrops(True)
        self.upload_area.dragEnterEvent = self.dragEnterEvent
        self.upload_area.dropEvent = self.dropEvent
        self.upload_area.mousePressEvent = lambda e: self.load_pdf()
        
        # Add upload area to content layout
        content_layout.addWidget(self.upload_area)
        
        # PDF label
        self.pdf_label = PDFLabel(self)
        self.pdf_label.setAlignment(Qt.AlignCenter)
        self.pdf_label.setStyleSheet("QLabel { background-color: #f0f0f0; }")
        self.pdf_label.hide()  # Hide initially
        
        self.scroll_area.setWidget(self.pdf_label)
        content_layout.addWidget(self.scroll_area)
        
        layout.addWidget(content_container)
        
        # Status label to show information about multi-table mode
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; padding: 5px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Bottom toolbar
        bottom_toolbar = QHBoxLayout()
        
        # Add back button at bottom left
        bottom_back_btn = QPushButton("← Back")
        bottom_back_btn.clicked.connect(self.go_back)
        bottom_back_btn.setStyleSheet("""
            QPushButton {
                background-color: #666666;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        bottom_toolbar.addWidget(bottom_back_btn)
        
        # Add reset button next to back button
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.clear_all)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #B71C1C;
            }
        """)
        bottom_toolbar.addWidget(reset_btn)
        
        # Add page navigation buttons in the center
        self.prev_page_btn = QPushButton("← Previous Page")
        self.prev_page_btn.clicked.connect(self.go_to_previous_page)
        self.prev_page_btn.hide()  # Hidden by default
        self.prev_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #3159C1;
            }
        """)
        
        self.next_page_btn = QPushButton("Next Page →")
        self.next_page_btn.clicked.connect(self.go_to_next_page)
        self.next_page_btn.hide()  # Hidden by default
        self.next_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #3159C1;
            }
        """)
        
        # Add Apply to Remaining Pages button
        self.apply_to_remaining_btn = QPushButton("Apply to Remaining Pages")
        self.apply_to_remaining_btn.clicked.connect(self.apply_to_remaining_pages)
        self.apply_to_remaining_btn.hide()  # Hidden by default
        self.apply_to_remaining_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                min-width: 180px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        
        # Add stretch to push navigation buttons to center
        bottom_toolbar.addStretch()
        
        # Add navigation buttons in the center
        bottom_toolbar.addWidget(self.prev_page_btn)
        bottom_toolbar.addWidget(self.next_page_btn)
        
        # Add Apply to Remaining Pages button
        bottom_toolbar.addWidget(self.apply_to_remaining_btn)
        
        # Add another stretch to maintain center alignment
        bottom_toolbar.addStretch()
        
        # Add Next button at bottom right
        next_btn = QPushButton("Next →")
        next_btn.clicked.connect(self.next_step)
        next_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #3159C1;
            }
        """)
        bottom_toolbar.addWidget(next_btn)
        
        layout.addLayout(bottom_toolbar)
        
        self.setLayout(layout)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files and files[0].lower().endswith('.pdf'):
            self.load_pdf_file(files[0])

    def load_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF File", "", "PDF Files (*.pdf)"
        )
        if file_path:
            self.load_pdf_file(file_path)

    def load_pdf_file(self, file_path):
        self.pdf_path = file_path
        self.pdf_document = fitz.open(file_path)
        self.current_page_index = 0
        self.page_regions = {}
        self.page_column_lines = {}
        
        # Check if PDF has multiple pages
        if len(self.pdf_document) > 1:
            # Create a dialog box for user configuration
            dialog = QDialog(self)
            dialog.setWindowTitle("Multi-page PDF Configuration")
            dialog.setMinimumWidth(400)
            
            layout = QVBoxLayout(dialog)
            
            # Add explanation text
            explanation = QLabel("This PDF has multiple pages. How would you like to configure the invoice template?")
            explanation.setWordWrap(True)
            layout.addWidget(explanation)
            
            # Create radio buttons
            button_group = QButtonGroup(dialog)
            
            first_page_radio = QRadioButton("Configure template for first page only")
            all_pages_radio = QRadioButton("Configure template for all pages")
            
            # Set first page as default
            first_page_radio.setChecked(True)
            
            button_group.addButton(first_page_radio)
            button_group.addButton(all_pages_radio)
            
            layout.addWidget(first_page_radio)
            layout.addWidget(all_pages_radio)
            
            # Add buttons
            button_layout = QHBoxLayout()
            ok_button = QPushButton("OK")
            cancel_button = QPushButton("Cancel")
            
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            # Connect signals
            ok_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)
            
            # Show dialog and get result
            if dialog.exec_() == QDialog.Accepted:
                if first_page_radio.isChecked():
                    self.multi_page_mode = False
                    self.prev_page_btn.hide()
                    self.next_page_btn.hide()
                    self.apply_to_remaining_btn.hide()
                else:
                    self.multi_page_mode = True
                    self.prev_page_btn.show()
                    self.next_page_btn.show()
                    self.apply_to_remaining_btn.show()
                    # Initialize regions and column lines for first page
                    self.page_regions[0] = {
                        'header': [],
                        'items': [],
                        'summary': []
                    }
                    self.page_column_lines[0] = {
                        RegionType.HEADER: [],
                        RegionType.ITEMS: [],
                        RegionType.SUMMARY: []
                    }
            else:
                # User cancelled, close the PDF and return
                self.pdf_document.close()
                self.pdf_document = None
                self.pdf_path = None
                return
        
        # Display the current page
        self.display_current_page()
        self.upload_area.hide()
        self.pdf_label.show()

    def display_current_page(self):
        if not self.pdf_document:
            return
            
        # Get the current page based on multi_page_mode
        if self.multi_page_mode:
            page = self.pdf_document[self.current_page_index]
            # Update status label to indicate current page
            self.status_label.setText(f"Configuring page {self.current_page_index + 1} of {len(self.pdf_document)}")
            # Load regions and column lines for current page if they exist
            if self.current_page_index in self.page_regions:
                self.regions = self.page_regions[self.current_page_index].copy()
            else:
                # Initialize empty regions for new page
                self.regions = {
                    'header': [],
                    'items': [],
                    'summary': []
                }
            
            if self.current_page_index in self.page_column_lines:
                self.column_lines = self.page_column_lines[self.current_page_index].copy()
                # Update table_areas with column lines for current page
                self.update_table_areas_with_columns()
            else:
                # Initialize empty column lines for new page
                self.column_lines = {
                    RegionType.HEADER: [],
                    RegionType.ITEMS: [],
                    RegionType.SUMMARY: []
                }
                self.table_areas = {}  # Reset table_areas for new page
        else:
            page = self.pdf_document[0]
            self.status_label.setText("Single-page mode: Template will be applied to first page only")
            
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        
        # Convert PyMuPDF pixmap to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Convert PIL Image to QPixmap
        bytes_io = io.BytesIO()
        img.save(bytes_io, format='PNG')
        qimg = QImage.fromData(bytes_io.getvalue())
        pixmap = QPixmap.fromImage(qimg)
        
        self.pdf_label.setPixmap(pixmap)
        self.pdf_label.adjustPixmap()  # Make sure to call adjustPixmap after setting the pixmap

    def update_table_areas_with_columns(self):
        """Update table_areas with column lines for the current page"""
        self.table_areas = {}
        
        # Process header regions
        for i, rect in enumerate(self.regions['header']):
            table_label = f"header_table_{i+1}"
            columns = []
            # Get column lines for this table
            for start, end, rect_idx in self.column_lines[RegionType.HEADER]:
                if rect_idx == i:
                    columns.append(start.x())
            
            self.table_areas[table_label] = {
                'type': 'header',
                'index': i,
                'rect': rect,
                'columns': sorted(columns)
            }
        
        # Process items region
        if self.regions['items']:
            rect = self.regions['items'][0]
            table_label = "items_table_1"
            columns = []
            # Get column lines for items table
            for start, end, rect_idx in self.column_lines[RegionType.ITEMS]:
                if rect_idx == 0:
                    columns.append(start.x())
            
            self.table_areas[table_label] = {
                'type': 'items',
                'index': 0,
                'rect': rect,
                'columns': sorted(columns)
            }
        
        # Process summary region
        if self.regions['summary']:
            rect = self.regions['summary'][0]
            table_label = "summary_table_1"
            columns = []
            # Get column lines for summary table
            for start, end, rect_idx in self.column_lines[RegionType.SUMMARY]:
                if rect_idx == 0:
                    columns.append(start.x())
            
            self.table_areas[table_label] = {
                'type': 'summary',
                'index': 0,
                'rect': rect,
                'columns': sorted(columns)
            }

    def get_region_color(self, region_type):
        colors = {
            RegionType.HEADER: QColor(255, 0, 0, 127),  # Red
            RegionType.ITEMS: QColor(0, 255, 0, 127),   # Green
            RegionType.SUMMARY: QColor(0, 0, 255, 127)  # Blue
        }
        return colors.get(region_type, QColor(0, 0, 0, 127))

    def start_region_selection(self, region_type):
        # Set active button
        self.current_region_type = region_type
        self.drawing_column = False
        
        # Define default button style
        default_style = """
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 150px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """
        
        # Define selected button style
        selected_style = """
            QPushButton {
                background-color: #4169E1;
                color: white;
                border: 1px solid #3159C1;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 150px;
            }
        """
        
        # Reset all buttons first
        for btn in [self.header_btn, self.items_btn, self.summary_btn, self.column_btn]:
            btn.setChecked(False)
            btn.setStyleSheet(default_style)
        
        # Highlight the selected button
        if region_type == RegionType.HEADER:
            self.header_btn.setChecked(True)
            self.header_btn.setStyleSheet(selected_style)
        elif region_type == RegionType.ITEMS:
            self.items_btn.setChecked(True)
            self.items_btn.setStyleSheet(selected_style)
        elif region_type == RegionType.SUMMARY:
            self.summary_btn.setChecked(True)
            self.summary_btn.setStyleSheet(selected_style)
        
        self.column_btn.setEnabled(True)

    def start_column_drawing(self):
        # Set drawing state
        self.drawing_column = True
        self.drawing = False
        self.current_region_type = None
        
        # Define default button style
        default_style = """
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 150px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """
        
        # Define selected button style
        selected_style = """
            QPushButton {
                background-color: #4169E1;
                color: white;
                border: 1px solid #3159C1;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 150px;
            }
        """
        
        # Reset all buttons first
        for btn in [self.header_btn, self.items_btn, self.summary_btn, self.column_btn]:
            btn.setChecked(False)
            btn.setStyleSheet(default_style)
        
        # Highlight the column button
        self.column_btn.setChecked(True)
        self.column_btn.setStyleSheet(selected_style)
        
        # Ensure section buttons are enabled
        for btn in [self.header_btn, self.items_btn, self.summary_btn]:
            btn.setEnabled(True)
            
        # Show instructions in the status label
        if self.multi_table_mode and len(self.regions.get(RegionType.HEADER, [])) > 1:
            self.status_label.setText("Click inside a table to add column lines. Each line belongs only to its specific table.")
        else:
            self.status_label.setText("Click inside a table region to add column lines.")
            
        # Reset active rectangle tracking
        if hasattr(self, 'active_region_type'):
            self.active_region_type = None
        if hasattr(self, 'active_rect_index'):
            self.active_rect_index = None

    def clear_current_page(self):
        """Clear drawings only for the current page"""
        if not self.pdf_document:
            return
            
        # Reset regions and column lines for current page
        self.regions = {
            RegionType.HEADER: [],
            RegionType.ITEMS: [],
            RegionType.SUMMARY: []
        }
        self.column_lines = {
            RegionType.HEADER: [],
            RegionType.ITEMS: [],
            RegionType.SUMMARY: []
        }
        
        # Reset table_areas for current page
        self.table_areas = {}
        
        # Reset drawing state
        self.current_region_type = None
        self.drawing = False
        self.drawing_column = False
        self.start_point = None
        self.current_rect = None
        
        # Reset multi-table mode
        self.multi_table_mode = False
        self.multi_table_btn.setText("Multi-Table Mode: OFF")
        self.multi_table_btn.setChecked(False)
        
        # Update stored regions and column lines for current page if in multi-page mode
        if self.multi_page_mode:
            self.page_regions[self.current_page_index] = self.regions.copy()
            self.page_column_lines[self.current_page_index] = self.column_lines.copy()
            self.status_label.setText(f"Cleared drawings for page {self.current_page_index + 1} of {len(self.pdf_document)}")
        else:
            self.status_label.setText("Cleared all drawings")
        
        # Reset button styles
        button_style = """
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 150px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """
        
        # Reset all buttons and their styles
        for btn in [self.header_btn, self.items_btn, self.summary_btn, self.column_btn, self.multi_table_btn]:
            btn.setChecked(False)
            btn.setStyleSheet(button_style)
            btn.setEnabled(True)
        
        # Update the display
        self.pdf_label.update()

    def clear_all(self):
        """Reset everything and remove the uploaded PDF"""
        # Reset regions and column lines
        self.regions = {
            RegionType.HEADER: [],
            RegionType.ITEMS: [],
            RegionType.SUMMARY: []
        }
        self.column_lines = {
            RegionType.HEADER: [],
            RegionType.ITEMS: [],
            RegionType.SUMMARY: []
        }
        
        # Reset our structured table_areas dictionary
        self.table_areas = {}
        
        # Reset drawing state
        self.current_region_type = None
        self.drawing = False
        self.drawing_column = False
        self.start_point = None
        self.current_rect = None
        
        # Reset multi-table mode
        self.multi_table_mode = False
        self.multi_table_btn.setText("Multi-Table Mode: OFF")
        self.multi_table_btn.setChecked(False)
        
        # Reset multi-page mode
        self.multi_page_mode = False
        self.current_page_index = 0
        self.page_regions = {}
        self.page_column_lines = {}
        
        # Hide navigation buttons
        self.prev_page_btn.hide()
        self.next_page_btn.hide()
        self.apply_to_remaining_btn.hide()
        
        # Reset status label
        self.status_label.setText("")
        
        # Define default button style
        button_style = """
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 150px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """
        
        # Reset all buttons and their styles
        for btn in [self.header_btn, self.items_btn, self.summary_btn, self.column_btn, self.multi_table_btn]:
            btn.setChecked(False)
            btn.setStyleSheet(button_style)
            btn.setEnabled(True)
        
        # Reset PDF display state
        self.pdf_path = None
        if hasattr(self, 'pdf_document'):
            self.pdf_document.close()
            self.pdf_document = None
        
        # Clear the PDF label and show upload area
        self.pdf_label.clear()
        self.pdf_label.hide()
        self.upload_area.show()
        
        # Update the display
        self.pdf_label.update()

    def handle_mouse_press(self, pos):
        if self.current_region_type or self.drawing_column:
            self.drawing = True
            self.start_point = pos
            self.current_pos = pos
            
            # If drawing column lines, identify which rectangle is active
            if self.drawing_column:
                self.active_region_type = None
                self.active_rect_index = None
                
                # Find which rectangle contains the start point
                for region_type, rects in self.regions.items():
                    for i, rect in enumerate(rects):
                        if rect.contains(pos):
                            self.active_region_type = region_type
                            self.active_rect_index = i
                            self.current_rect = rect
                            
                            # Better information when selecting a table for column drawing
                            table_info = ""
                            if len(self.regions[region_type]) > 1:
                                table_info = f" (Table #{i + 1} of {len(self.regions[region_type])})"
                            
                            self.status_label.setText(f"Now drawing columns for {region_type.title()} section{table_info}. Click to add column dividers.")
                            
                            # Debug information about existing column lines for this table
                            existing_cols = [line for line in self.column_lines[region_type] if len(line) == 3 and line[2] == i]
                            if existing_cols:
                                x_positions = sorted([line[0].x() for line in existing_cols])
                                print(f"Table {region_type.title()}{table_info} already has {len(existing_cols)} columns at x positions: {x_positions}")
                            else:
                                print(f"No existing columns for {region_type.title()}{table_info}")
                            
                            # Also debug the structured data
                            for label, info in self.table_areas.items():
                                if info['type'] == region_type and info['index'] == i:
                                    if info['columns']:
                                        print(f"Table {label} has {len(info['columns'])} columns at x positions: {sorted(info['columns'])}")
                                    else:
                                        print(f"Table {label} has no columns yet")
                            break
                    if self.active_region_type:
                        break

    def handle_mouse_move(self, pos):
        if self.drawing and self.start_point:
            if self.current_region_type:
                # Drawing region rectangle
                self.current_rect = QRect(self.start_point, pos).normalized()
            elif self.drawing_column:
                # When drawing column lines, just update the current position for visual feedback
                self.current_pos = pos
                
                # Use the already identified active rectangle from mouse_press
                if hasattr(self, 'active_region_type') and hasattr(self, 'active_rect_index'):
                    if self.active_region_type and self.active_rect_index is not None:
                        try:
                            # Get the active rect for drawing preview
                            self.current_rect = self.regions[self.active_region_type][self.active_rect_index]
                        except (IndexError, KeyError):
                            pass
            self.pdf_label.update()

    def handle_mouse_release(self, pos):
        if self.drawing and self.start_point:
            if self.current_region_type:
                # Add new rectangle to regions
                new_rect = QRect(self.start_point, pos).normalized()
                
                # In multi-table mode for header, we add multiple regions
                # For other sections or when multi-table mode is off, we replace the regions
                if self.current_region_type == RegionType.HEADER and self.multi_table_mode:
                    # Add the new rectangle to the regions list
                    self.regions[self.current_region_type].append(new_rect)
                    
                    # Create a unique label for this table
                    table_index = len(self.regions[self.current_region_type])
                    table_label = f"{self.current_region_type}_table_{table_index}"
                    
                    # Add to our structured table_areas dictionary
                    self.table_areas[table_label] = {
                        'type': self.current_region_type,
                        'index': table_index - 1,  # 0-based index
                        'rect': new_rect,
                        'columns': []  # Will be filled when columns are drawn
                    }
                    
                    print(f"Created new table: {table_label} at position {table_index}")
                else:
                    # For other section types or when multi-table mode is off
                    # Clear existing regions before adding new one
                    if self.current_region_type == RegionType.HEADER and not self.multi_table_mode:
                        # Replace the first header table when not in multi-table mode
                        self.regions[self.current_region_type] = [new_rect]
                        
                        # Create/Update the table label
                        table_label = f"{self.current_region_type}_table_1"
                        
                        # Update table_areas
                        self.table_areas[table_label] = {
                            'type': self.current_region_type,
                            'index': 0,
                            'rect': new_rect,
                            'columns': []
                        }
                    elif self.current_region_type in [RegionType.ITEMS, RegionType.SUMMARY]:
                        # For items and summary, we only have one table
                        self.regions[self.current_region_type] = [new_rect]
                        
                        # Create/Update the table label
                        table_label = f"{self.current_region_type}_table_1"
                        
                        # Update table_areas
                        self.table_areas[table_label] = {
                            'type': self.current_region_type,
                            'index': 0,
                            'rect': new_rect,
                            'columns': []
                        }
                        
                # Update status label to show the number of tables drawn
                if self.current_region_type == RegionType.HEADER:
                    num_tables = len(self.regions[RegionType.HEADER])
                    if num_tables > 1:
                        self.status_label.setText(f"Header section: {num_tables} tables drawn")
                    else:
                        self.status_label.setText("Header section: 1 table drawn")
            
            elif self.drawing_column and hasattr(self, 'active_region_type') and hasattr(self, 'active_rect_index'):
                # Only add column line if we have an active region
                if self.active_region_type and self.active_rect_index is not None:
                    try:
                        rect = self.regions[self.active_region_type][self.active_rect_index]
                        
                        # Make sure the x-coordinate stays within the rectangle's bounds
                        x_pos = max(rect.left(), min(pos.x(), rect.right()))
                        
                        # Create vertical line from top to bottom of the rectangle
                        start_point = QPoint(x_pos, rect.top())
                        end_point = QPoint(x_pos, rect.bottom())
                        
                        # Store the rectangle index along with the column line (for backward compatibility)
                        self.column_lines[self.active_region_type].append(
                            (start_point, end_point, self.active_rect_index)
                        )
                        print(f"Added column line at x={x_pos} for {self.active_region_type} table with index {self.active_rect_index}")
                        
                        # Now also store in our structured format
                        # Find the correct table label for this rectangle
                        table_found = False
                        for table_label, table_info in self.table_areas.items():
                            if (table_info['type'] == self.active_region_type and 
                                table_info['index'] == self.active_rect_index):
                                # Add the column x-coordinate to this table's columns list
                                # This is the unscaled value directly from the PDF coordinates
                                table_info['columns'].append(x_pos)
                                print(f"Added column at x={x_pos} to {table_label} (index: {self.active_rect_index})")
                                table_found = True
                                break
                        
                        if not table_found:
                            print(f"WARNING: No matching table found for {self.active_region_type} with index {self.active_rect_index}")
                        
                        # Clear the status label
                        self.status_label.setText("")
                    except (IndexError, KeyError):
                        pass
            
            # Reset drawing state
            self.drawing = False
            self.start_point = None
            self.current_rect = None
            if hasattr(self, 'active_region_type'):
                self.active_region_type = None
            if hasattr(self, 'active_rect_index'):
                self.active_rect_index = None
            self.pdf_label.update()

    def next_step(self):
        if not self.pdf_path:
            QMessageBox.warning(self, "Warning", "Please load a PDF file first.")
            return

        try:
            # Check if this is a multi-page PDF
            pdf_document = fitz.open(self.pdf_path)
            total_pages = len(pdf_document)
            pdf_document.close()

            if total_pages > 1:
                # Show dialog to ask user if they want to configure all pages
                reply = QMessageBox.question(
                    self,
                    "Multi-page PDF Detected",
                    f"This PDF has {total_pages} pages. Would you like to configure all pages?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    # Create multi-page section viewer
                    from multi_page_section_viewer import MultiPageSectionViewer
                    
                    # Save current page's regions and column lines before proceeding
                    if self.multi_page_mode:
                        self.page_regions[self.current_page_index] = self.regions.copy()
                        self.page_column_lines[self.current_page_index] = self.column_lines.copy()
                    
                    # Extract data from all pages
                    all_pages_data = []
                    for page_idx in range(total_pages):
                        header_df, item_details_df, summary_df = self.extract_page_data(page_idx, 'page')
                        all_pages_data.append({
                            'header': header_df,
                            'items': item_details_df,
                            'summary': summary_df
                        })
                    
                    # Create the viewer with all page data
                    viewer = MultiPageSectionViewer(
                        self.pdf_path,
                        all_pages_data,
                        self.page_regions if self.multi_page_mode else self.regions,
                        self.page_column_lines if self.multi_page_mode else self.column_lines
                    )
                    
                    # Add to stacked widget and show
                    main_window = self.window()
                    if hasattr(main_window, 'stacked_widget'):
                        main_window.stacked_widget.addWidget(viewer)
                        main_window.stacked_widget.setCurrentWidget(viewer)
                else:
                    # Use single page viewer
                    from invoice_section_viewer import InvoiceSectionViewer
                    
                    # Extract data from first page (index 0)
                    header_df, item_details_df, summary_df = self.extract_page_data(0, 'first_page')
                    
                    # Create the viewer with only current page data
                    viewer = InvoiceSectionViewer(
                        self.pdf_path,
                        header_df,
                        item_details_df,
                        summary_df,
                        self.regions,
                        self.column_lines
                    )
                    
                    # Add to stacked widget and show
                    main_window = self.window()
                    if hasattr(main_window, 'stacked_widget'):
                        main_window.stacked_widget.addWidget(viewer)
                        main_window.stacked_widget.setCurrentWidget(viewer)
            else:
                # Single page PDF - use regular viewer
                from invoice_section_viewer import InvoiceSectionViewer
                
                # Extract data from the page (index 0)
                header_df, item_details_df, summary_df = self.extract_page_data(0, 'first_page')
                
                # Create the viewer with single page data
                viewer = InvoiceSectionViewer(
                    self.pdf_path,
                    header_df,
                    item_details_df,
                    summary_df,
                    self.regions,
                    self.column_lines
                )
                
                # Add to stacked widget and show
                main_window = self.window()
                if hasattr(main_window, 'stacked_widget'):
                    main_window.stacked_widget.addWidget(viewer)
                    main_window.stacked_widget.setCurrentWidget(viewer)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create viewer: {str(e)}")
            import traceback
            traceback.print_exc()

    def go_back(self):
        # Get the main window and go back one screen
        main_window = self.window()
        if main_window:
            stacked_widget = main_window.findChild(QStackedWidget)
            if stacked_widget:
                current_index = stacked_widget.currentIndex()
                stacked_widget.setCurrentIndex(current_index - 1)

    def toggle_multi_table_mode(self):
        self.multi_table_mode = not self.multi_table_mode
        
        if self.multi_table_mode:
            self.multi_table_btn.setText("Multi-Table Mode: ON")
            self.multi_table_btn.setChecked(True)
            self.multi_table_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4169E1;
                    color: white;
                    border: 1px solid #3159C1;
                    padding: 8px 16px;
                    border-radius: 4px;
                    min-width: 150px;
                }
            """)
            self.status_label.setText("Multi-Table Mode: You can draw multiple tables in header section")
        else:
            self.multi_table_btn.setText("Multi-Table Mode: OFF")
            self.multi_table_btn.setChecked(False)
            self.multi_table_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #ddd;
                    padding: 8px 16px;
                    border-radius: 4px;
                    min-width: 150px;
                    color: #333333;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            self.status_label.setText("")
            
            # When turning off multi-table mode, if we have multiple header tables,
            # convert to single table mode by keeping only the first table
            if len(self.regions[RegionType.HEADER]) > 1:
                print("Switching to single table mode, keeping only the first header table")
                # Keep only the first header table
                first_header = self.regions[RegionType.HEADER][0]
                self.regions[RegionType.HEADER] = [first_header]
                
                # Update column_lines to keep only lines for the first table
                new_column_lines = []
                for line in self.column_lines[RegionType.HEADER]:
                    if len(line) == 3 and line[2] == 0:  # Only keep lines for the first table
                        new_column_lines.append(line)
                self.column_lines[RegionType.HEADER] = new_column_lines
                
                # Update table_areas to keep only the first header table
                # Find and remove all header tables except the first one
                header_table_labels = [label for label, info in self.table_areas.items() 
                                     if info['type'] == 'header']
                
                if header_table_labels:
                    # Find first table to keep
                    first_header_label = None
                    for label in header_table_labels:
                        info = self.table_areas[label]
                        if info['index'] == 0:
                            first_header_label = label
                            break
                    
                    # Remove all header tables
                    for label in header_table_labels:
                        if label != first_header_label:
                            if label in self.table_areas:
                                del self.table_areas[label]
        
        # Force header selection when multi-table mode is toggled
        if self.multi_table_mode:
            self.start_region_selection(RegionType.HEADER)

    def extract_page_data(self, page_index, page_type):
        """Extract data from a specific page"""
        if not self.pdf_document:
            return None, None, None
        
        try:
            # Get regions for current page
            current_regions = self.page_regions.get(page_index, self.regions)
            
            # Create empty DataFrames with proper structure
            header_df = pd.DataFrame(columns=['Field', 'Value'])
            item_details_df = pd.DataFrame(columns=['Description', 'Quantity', 'Unit Price', 'Amount'])
            summary_df = pd.DataFrame(columns=['Field', 'Value'])
            
            return header_df, item_details_df, summary_df
        
        except Exception as e:
            print(f"Error extracting data from page {page_index}: {str(e)}")
            import traceback
            traceback.print_exc()
            # Return empty DataFrames instead of None
            return pd.DataFrame(columns=['Field', 'Value']), pd.DataFrame(columns=['Description', 'Quantity', 'Unit Price', 'Amount']), pd.DataFrame(columns=['Field', 'Value'])

    def extract_region_data(self, page, regions):
        """Extract data from a specific region of the page"""
        if not regions:
            return None
            
        try:
            # For header and summary regions, we expect a list of rectangles
            # For items region, we expect a single rectangle
            if isinstance(regions, list):
                # Return empty DataFrame for header/summary
                return pd.DataFrame(columns=['Field', 'Value'])
            else:
                # Return empty DataFrame for items
                return pd.DataFrame(columns=['Description', 'Quantity', 'Unit Price', 'Amount'])
                
        except Exception as e:
            print(f"Error extracting region data: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def extract_multi_page_invoice(self):
        """Handle extraction of multi-page invoice"""
        all_data = {
            'header': None,
            'items': [],
            'summary': None
        }
        
        # Extract first page
        first_page_data = self.extract_page_data(0, 'first_page')
        if first_page_data:
            all_data['header'] = first_page_data.get('header')
            all_data['items'].extend(first_page_data.get('items', []))
        
        # Extract middle pages
        for page_num in range(1, len(self.pdf_document) - 1):
            middle_page_data = self.extract_page_data(page_num, 'middle_page')
            if middle_page_data:
                all_data['items'].extend(middle_page_data.get('items', []))
        
        # Extract last page
        last_page_data = self.extract_page_data(-1, 'last_page')
        if last_page_data:
            all_data['items'].extend(last_page_data.get('items', []))
            all_data['summary'] = last_page_data.get('summary')
        
        return all_data 

    def go_to_next_page(self):
        if self.multi_page_mode and self.current_page_index < len(self.pdf_document) - 1:
            # Save current regions and column lines before moving to next page
            self.page_regions[self.current_page_index] = self.regions.copy()
            self.page_column_lines[self.current_page_index] = self.column_lines.copy()
            self.current_page_index += 1
            self.display_current_page()

    def go_to_previous_page(self):
        if self.multi_page_mode and self.current_page_index > 0:
            # Save current regions and column lines before moving to previous page
            self.page_regions[self.current_page_index] = self.regions.copy()
            self.page_column_lines[self.current_page_index] = self.column_lines.copy()
            self.current_page_index -= 1
            self.display_current_page()

    def apply_to_remaining_pages(self):
        """Apply current page's regions and column lines to all remaining pages"""
        if not self.multi_page_mode or not self.pdf_document:
            return
            
        # Get current page's regions and column lines
        current_regions = self.regions.copy()
        current_column_lines = self.column_lines.copy()
        
        # Calculate remaining pages
        remaining_pages = len(self.pdf_document) - (self.current_page_index + 1)
        
        if remaining_pages <= 0:
            QMessageBox.information(self, "No Remaining Pages", 
                                  "There are no remaining pages to apply the template to.")
            return
            
        # Ask for confirmation
        reply = QMessageBox.question(self, "Apply to Remaining Pages",
                                   f"This will apply the current page's template to {remaining_pages} remaining pages.\n"
                                   "Are you sure you want to continue?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # Apply to all remaining pages
                for page_num in range(self.current_page_index + 1, len(self.pdf_document)):
                    # Create new regions dictionary for this page
                    new_regions = {
                        'header': [],
                        'items': [],
                        'summary': []
                    }
                    
                    # Copy regions properly
                    for region_type in ['header', 'items', 'summary']:
                        for rect in current_regions[region_type]:
                            # Create new QRect with the same coordinates
                            new_rect = QRect(rect.x(), rect.y(), rect.width(), rect.height())
                            new_regions[region_type].append(new_rect)
                    
                    # Store the new regions
                    self.page_regions[page_num] = new_regions
                    
                    # Create new column lines dictionary for this page
                    new_column_lines = {
                        RegionType.HEADER: [],
                        RegionType.ITEMS: [],
                        RegionType.SUMMARY: []
                    }
                    
                    # Copy column lines properly
                    for region_type in [RegionType.HEADER, RegionType.ITEMS, RegionType.SUMMARY]:
                        for start, end, rect_idx in current_column_lines[region_type]:
                            # Create new QPoints with the same coordinates
                            new_start = QPoint(start.x(), start.y())
                            new_end = QPoint(end.x(), end.y())
                            new_column_lines[region_type].append((new_start, new_end, rect_idx))
                    
                    # Store the new column lines
                    self.page_column_lines[page_num] = new_column_lines
                
                QMessageBox.information(self, "Success", 
                                      f"Template has been applied to {remaining_pages} remaining pages.")
                
                # Update status label
                self.status_label.setText(f"Template applied to {remaining_pages} remaining pages")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", 
                                   f"An error occurred while applying the template: {str(e)}")
                print(f"Error applying template: {str(e)}")
                import traceback
                traceback.print_exc() 