from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QScrollArea, QFrame, QStackedWidget)
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import (QFont, QImage, QPixmap, QCursor, QPainter, 
                          QPen, QColor)

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

    def mousePressEvent(self, event):
        if self.parent and event.button() == Qt.LeftButton:
            pos = event.pos()
            if self.isInDrawableArea(pos):
                mapped_pos = self.mapToPixmap(pos)
                self.parent.handle_mouse_press(mapped_pos)

    def mouseMoveEvent(self, event):
        if self.parent:
            pos = event.pos()
            if self.isInDrawableArea(pos):
                mapped_pos = self.mapToPixmap(pos)
                self.parent.handle_mouse_move(mapped_pos)

    def mouseReleaseEvent(self, event):
        if self.parent and event.button() == Qt.LeftButton:
            pos = event.pos()
            if self.isInDrawableArea(pos):
                mapped_pos = self.mapToPixmap(pos)
                self.parent.handle_mouse_release(mapped_pos)

    def isInDrawableArea(self, pos):
        if not self.scaled_pixmap:
            return False
        # Check if the position is within the scaled pixmap area
        relative_pos = pos - self.offset
        return (0 <= relative_pos.x() <= self.scaled_pixmap.width() and
                0 <= relative_pos.y() <= self.scaled_pixmap.height())

    def paintEvent(self, event):
        if not self.scaled_pixmap:
            super().paintEvent(event)
            return
            
        painter = QPainter(self)
        painter.drawPixmap(self.offset, self.scaled_pixmap)
        
        # Draw regions
        if self.parent:
            # Draw existing regions
            regions_to_draw = self.parent.regions[self.parent.current_page_type]
            for region_type, rects in regions_to_draw.items():
                color = self.parent.get_region_color(region_type)
                pen = QPen(color, 2, Qt.SolidLine)
                painter.setPen(pen)
                
                for rect in rects:
                    scaled_rect = QRect(
                        self.mapFromPixmap(rect.topLeft()),
                        self.mapFromPixmap(rect.bottomRight())
                    )
                    painter.drawRect(scaled_rect)
            
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

class MultiPageProcessor(QWidget):
    config_completed = Signal(dict)  # Emits the multi-page configuration when done
    go_back = Signal()  # Signal to go back to previous screen

    def __init__(self, pdf_path, has_middle_pages=True):
        super().__init__()
        self.pdf_path = pdf_path
        self.has_middle_pages = has_middle_pages
        self.current_page = 1  # Start with second page (middle page)
        self.regions = {
            'middle_page': {
                RegionType.ITEMS: []  # Only items region for middle pages
            },
            'last_page': {
                RegionType.ITEMS: [],
                RegionType.SUMMARY: []  # Items and summary regions for last page
            }
        }
        self.current_region_type = None
        self.current_page_type = 'middle_page' if has_middle_pages else 'last_page'
        self.drawing = False
        self.start_point = None
        self.current_rect = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Title
        title = QLabel("Multi-page Invoice Configuration")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #333333; margin: 20px 0;")
        layout.addWidget(title)

        # Instructions
        if self.has_middle_pages:
            instructions_text = (
                "Please configure the regions for your multi-page invoice:\n\n"
                "1. First, select the repeating items region that appears on middle pages\n"
                "2. Then, configure the items and summary regions on the last page"
            )
        else:
            instructions_text = (
                "Please configure the regions for your multi-page invoice:\n\n"
                "Since this invoice type doesn't have repeating middle pages, "
                "you only need to configure the items and summary regions on the last page."
            )

        instructions = QLabel(instructions_text)
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666666; font-size: 16px; margin: 10px 0;")
        instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions)

        # Create main content area
        content = QWidget()
        content_layout = QVBoxLayout(content)

        # Page type indicator
        if self.has_middle_pages:
            page_type_text = "Currently configuring: Middle Page (Repeating Content)"
        else:
            page_type_text = "Currently configuring: Last Page"
        
        self.page_type_label = QLabel(page_type_text)
        self.page_type_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.page_type_label.setAlignment(Qt.AlignCenter)
        self.page_type_label.setStyleSheet("color: #333333; margin: 10px 0; padding: 10px; background-color: #f0f0f0; border-radius: 4px;")
        content_layout.addWidget(self.page_type_label)

        # Toolbar for region selection
        toolbar = QHBoxLayout()
        
        # Items button (always visible)
        self.items_btn = QPushButton("Select Items Region")
        self.items_btn.clicked.connect(lambda: self.start_region_selection(RegionType.ITEMS))
        self.items_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3158D3;
            }
        """)
        toolbar.addWidget(self.items_btn)

        # Summary button (only for last page)
        self.summary_btn = QPushButton("Select Summary Region")
        self.summary_btn.clicked.connect(lambda: self.start_region_selection(RegionType.SUMMARY))
        self.summary_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3158D3;
            }
        """)
        if self.has_middle_pages:
            self.summary_btn.hide()
        toolbar.addWidget(self.summary_btn)

        # Clear button
        clear_btn = QPushButton("Clear Selection")
        clear_btn.clicked.connect(self.clear_current_selection)
        clear_btn.setStyleSheet("""
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
        toolbar.addWidget(clear_btn)

        content_layout.addLayout(toolbar)

        # PDF display area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(600)
        
        self.pdf_label = PDFLabel(self)
        self.pdf_label.setAlignment(Qt.AlignCenter)
        self.pdf_label.setStyleSheet("QLabel { background-color: #f0f0f0; }")
        
        self.scroll_area.setWidget(self.pdf_label)
        content_layout.addWidget(self.scroll_area)

        # Navigation
        nav_layout = QHBoxLayout()
        
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.go_back.emit)
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
        
        if self.has_middle_pages:
            next_text = "Next: Configure Last Page →"
        else:
            next_text = "Complete Configuration →"
            
        self.next_btn = QPushButton(next_text)
        self.next_btn.clicked.connect(self.next_step)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3158D3;
            }
        """)
        
        nav_layout.addWidget(back_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_btn)
        
        content_layout.addLayout(nav_layout)
        layout.addWidget(content)
        self.setLayout(layout)

        # Load the PDF
        self.load_pdf()

    def load_pdf(self):
        if not self.pdf_path:
            return
            
        import fitz
        from PIL import Image
        import io
        
        # Open the PDF
        self.pdf_document = fitz.open(self.pdf_path)
        
        # Get the page (either middle or last)
        if self.current_page_type == 'middle_page':
            # Use the second page as an example of a middle page
            page = self.pdf_document[1]
        else:
            # Use the last page
            page = self.pdf_document[-1]
            
        # Render the page
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

    def start_region_selection(self, region_type):
        self.current_region_type = region_type
        self.pdf_label.setCursor(Qt.CrossCursor)
        self.drawing = False
        self.start_point = None
        self.current_rect = None

    def clear_current_selection(self):
        if self.current_page_type == 'middle_page':
            self.regions['middle_page'][RegionType.ITEMS] = []
        else:
            self.regions['last_page'][self.current_region_type] = []
        self.pdf_label.update()

    def next_step(self):
        if self.current_page_type == 'middle_page' and self.has_middle_pages:
            if not self.regions['middle_page'][RegionType.ITEMS]:
                # Show error message - need to select items region
                return
                
            # Switch to last page configuration
            self.current_page_type = 'last_page'
            self.current_page = -1  # Last page
            self.page_type_label.setText("Currently configuring: Last Page")
            self.items_btn.show()
            self.summary_btn.show()
            self.next_btn.setText("Complete Configuration →")
            self.load_pdf()
        else:
            if not self.regions['last_page'][RegionType.ITEMS] or \
               not self.regions['last_page'][RegionType.SUMMARY]:
                # Show error message - need to select both regions
                return
            
            # If no middle pages, remove middle page config
            if not self.has_middle_pages:
                del self.regions['middle_page']
                
            # Emit the configuration
            self.config_completed.emit(self.regions)

    def handle_mouse_press(self, pos):
        if self.current_region_type:
            self.drawing = True
            self.start_point = pos
            self.current_rect = None
            self.pdf_label.update()

    def handle_mouse_move(self, pos):
        if self.drawing and self.start_point:
            from PySide6.QtCore import QRect
            self.current_rect = QRect(self.start_point, pos).normalized()
            self.pdf_label.update()

    def handle_mouse_release(self, pos):
        if self.drawing and self.start_point:
            from PySide6.QtCore import QRect
            if self.current_page_type == 'middle_page':
                self.regions['middle_page'][self.current_region_type].append(
                    QRect(self.start_point, pos).normalized()
                )
            else:
                self.regions['last_page'][self.current_region_type].append(
                    QRect(self.start_point, pos).normalized()
                )
            
            self.drawing = False
            self.start_point = None
            self.current_rect = None
            self.pdf_label.update()

    def get_region_color(self, region_type):
        colors = {
            RegionType.ITEMS: QColor(0, 255, 0, 127),   # Green
            RegionType.SUMMARY: QColor(0, 0, 255, 127)  # Blue
        }
        return colors.get(region_type, QColor(0, 0, 0, 127)) 