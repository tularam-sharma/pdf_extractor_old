from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QScrollArea, QFrame, QLineEdit, QTextEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
                             QFormLayout, QMessageBox, QInputDialog, QDialogButtonBox,
                             QApplication, QTabWidget, QCheckBox, QComboBox)
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QFont, QIcon
from database import InvoiceDatabase
import os
import datetime
import json

class SaveTemplateDialog(QDialog):
    """Dialog for saving a new template"""
    
    def __init__(self, parent=None, template_name=None, template_description=None):
        super().__init__(parent)
        self.setWindowTitle("Save Invoice Template")
        self.setMinimumWidth(450)  # Make the dialog wider
        
        # Set global style for this dialog
        self.setStyleSheet("""
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
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter a descriptive name for your template")
        self.name_input.setStyleSheet("color: black; background-color: white;")
        if template_name:
            self.name_input.setText(template_name)
        
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Describe the purpose or usage of this template (optional)")
        self.description_input.setMinimumHeight(100)
        self.description_input.setStyleSheet("color: black; background-color: white;")
        if template_description:
            self.description_input.setText(template_description)
        
        form_layout.addRow(name_label, self.name_input)
        form_layout.addRow(desc_label, self.description_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
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
        save_btn.clicked.connect(self.accept)
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
        
        self.setLayout(layout)
    
    def get_template_data(self):
        """Get the template name and description entered by the user"""
        return {
            "name": self.name_input.text().strip(),
            "description": self.description_input.toPlainText().strip()
        }

class EditTemplateDialog(QDialog):
    """Dialog for editing template settings and configuration"""
    
    def __init__(self, parent=None, template_data=None):
        super().__init__(parent)
        self.template_data = template_data
        self.setWindowTitle("Edit Template Settings")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # Set global style for this dialog
        self.setStyleSheet("""
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
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                color: black;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #ddd;
                font-weight: bold;
                color: black;
            }
        """)
        
        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Add header
        header_label = QLabel("Template Settings")
        header_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_label.setStyleSheet("color: #333;")
        main_layout.addWidget(header_label)
        
        # Create tab widget for different sections
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
            QTabBar::tab {
                background: #f0f0f0;
                border: 1px solid #ddd;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: none;
                margin-bottom: -1px;
            }
        """)
        
        # Add tabs
        tab_widget.addTab(self.create_general_tab(), "General")
        tab_widget.addTab(self.create_regions_tab(), "Table Regions")
        tab_widget.addTab(self.create_columns_tab(), "Column Lines")
        tab_widget.addTab(self.create_config_tab(), "Configuration")
        
        main_layout.addWidget(tab_widget)
        
        # Add buttons
        buttons_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
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
        
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self.accept)
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
        
        main_layout.addLayout(buttons_layout)
        
        self.setLayout(main_layout)
    
    def create_general_tab(self):
        """Create the general settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # Template name
        name_layout = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setText(self.template_data.get("name", ""))
        name_layout.addRow("Template Name:", self.name_input)
        
        # Description
        desc_layout = QFormLayout()
        self.desc_input = QTextEdit()
        self.desc_input.setMinimumHeight(100)
        self.desc_input.setText(self.template_data.get("description", ""))
        desc_layout.addRow("Description:", self.desc_input)
        
        # Template type
        type_layout = QFormLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Single-page", "Multi-page"])
        self.type_combo.setCurrentText("Multi-page" if self.template_data.get("template_type") == "multi" else "Single-page")
        type_layout.addRow("Template Type:", self.type_combo)
        
        layout.addLayout(name_layout)
        layout.addLayout(desc_layout)
        layout.addLayout(type_layout)
        layout.addStretch()
        
        return tab
    
    def create_regions_tab(self):
        """Create the table regions tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # Create table for regions
        self.regions_table = QTableWidget()
        self.regions_table.setColumnCount(7)
        self.regions_table.setHorizontalHeaderLabels([
            "Section", "Table #", "X", "Y", "Width", "Height", "Scaled Format"
        ])
        self.regions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.regions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.regions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.regions_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.regions_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.regions_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.regions_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        
        # Add regions from template data
        regions = self.template_data.get("regions", {})
        row = 0
        for section, rects in regions.items():
            for i, rect in enumerate(rects):
                self.regions_table.insertRow(row)
                self.regions_table.setItem(row, 0, QTableWidgetItem(section.title()))
                self.regions_table.setItem(row, 1, QTableWidgetItem(str(i + 1)))
                
                # Handle both QRect objects and dictionary format from JSON
                if isinstance(rect, QRect):
                    # Already a QRect
                    x = rect.x()
                    y = rect.y()
                    width = rect.width()
                    height = rect.height()
                elif isinstance(rect, dict) and 'x' in rect:
                    # Dictionary format from JSON
                    x = rect['x']
                    y = rect['y']
                    width = rect['width'] 
                    height = rect['height']
                else:
                    # Unknown format, skip
                    continue
                
                # Calculate scaled format (x1,y1,x2,y2)
                x1 = x
                y1 = y
                x2 = x + width
                y2 = y + height
                
                # Store drawn format (x,y,width,height)
                self.regions_table.setItem(row, 2, QTableWidgetItem(str(x)))
                self.regions_table.setItem(row, 3, QTableWidgetItem(str(y)))
                self.regions_table.setItem(row, 4, QTableWidgetItem(str(width)))
                self.regions_table.setItem(row, 5, QTableWidgetItem(str(height)))
                
                # Store scaled format (x1,y1,x2,y2)
                scaled_text = f"({x1}, {y1}, {x2}, {y2})"
                scaled_item = QTableWidgetItem(scaled_text)
                scaled_item.setToolTip("Format: x1, y1, x2, y2")
                self.regions_table.setItem(row, 6, scaled_item)
                
                row += 1
        
        layout.addWidget(self.regions_table)
        
        # Add buttons for region management
        buttons_layout = QHBoxLayout()
        add_btn = QPushButton("Add Region")
        edit_btn = QPushButton("Edit Region")
        delete_btn = QPushButton("Delete Region")
        
        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(edit_btn)
        buttons_layout.addWidget(delete_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        return tab
    
    def create_columns_tab(self):
        """Create the column lines tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # Create table for column lines
        self.columns_table = QTableWidget()
        self.columns_table.setColumnCount(4)
        self.columns_table.setHorizontalHeaderLabels(["Section", "Table #", "X Position", "Description"])
        self.columns_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.columns_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.columns_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.columns_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        
        # Add column lines from template data
        column_lines = self.template_data.get("column_lines", {})
        row = 0
        for section, lines in column_lines.items():
            for i, line in enumerate(lines):
                self.columns_table.insertRow(row)
                self.columns_table.setItem(row, 0, QTableWidgetItem(section.title()))
                self.columns_table.setItem(row, 1, QTableWidgetItem(str(i + 1)))
                
                # Handle both QPoint objects and dictionary format from JSON
                if len(line) >= 2:
                    first_point = line[0]
                    x_position = 0
                    
                    if isinstance(first_point, QPoint):
                        x_position = first_point.x()
                    elif isinstance(first_point, dict) and 'x' in first_point:
                        x_position = first_point['x']
                    
                    self.columns_table.setItem(row, 2, QTableWidgetItem(str(x_position)))
                    self.columns_table.setItem(row, 3, QTableWidgetItem("Column separator line"))
                
                row += 1
        
        layout.addWidget(self.columns_table)
        
        # Add buttons for column line management
        buttons_layout = QHBoxLayout()
        add_btn = QPushButton("Add Column Line")
        edit_btn = QPushButton("Edit Column Line")
        delete_btn = QPushButton("Delete Column Line")
        
        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(edit_btn)
        buttons_layout.addWidget(delete_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        return tab
    
    def create_config_tab(self):
        """Create the configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # Create form for configuration settings
        config_layout = QFormLayout()
        
        # Multi-table mode
        self.multi_table_mode = QCheckBox()
        self.multi_table_mode.setChecked(self.template_data.get("config", {}).get("multi_table_mode", False))
        config_layout.addRow("Multi-table Mode:", self.multi_table_mode)
        
        # Add other configuration options here
        
        layout.addLayout(config_layout)
        layout.addStretch()
        
        return tab
    
    def get_template_data(self):
        """Get the updated template data"""
        regions = {}
        
        # Process regions from the table
        for row in range(self.regions_table.rowCount()):
            section = self.regions_table.item(row, 0).text().lower()
            if section not in regions:
                regions[section] = []
            
            # Get drawn format (x,y,width,height)
            x = int(self.regions_table.item(row, 2).text())
            y = int(self.regions_table.item(row, 3).text())
            width = int(self.regions_table.item(row, 4).text())
            height = int(self.regions_table.item(row, 5).text())
            
            # Create QRect for the region
            rect = QRect(x, y, width, height)
            regions[section].append(rect)
        
        # Get column lines from the template data to preserve structure
        # We're keeping the original column_lines structure as much as possible
        column_lines = self.template_data.get("column_lines", {})
        
        # Convert QRect objects to dictionaries for JSON serialization
        serializable_regions = {}
        for section, rects in regions.items():
            serializable_regions[section] = []
            for rect in rects:
                # Convert QRect to a dictionary
                serializable_regions[section].append({
                    'x': rect.x(),
                    'y': rect.y(),
                    'width': rect.width(),
                    'height': rect.height()
                })
        
        # Convert column lines to serializable format
        serializable_column_lines = {}
        for section, lines in column_lines.items():
            serializable_column_lines[section] = []
            for line in lines:
                # Format depends on the structure of line
                if len(line) == 2:  # Simple start-end point format
                    # Convert QPoint objects or dictionaries to dictionaries
                    start_point = line[0]
                    end_point = line[1]
                    
                    start_dict = {}
                    end_dict = {}
                    
                    if isinstance(start_point, QPoint):
                        start_dict = {'x': start_point.x(), 'y': start_point.y()}
                    elif isinstance(start_point, dict) and 'x' in start_point:
                        start_dict = start_point
                    
                    if isinstance(end_point, QPoint):
                        end_dict = {'x': end_point.x(), 'y': end_point.y()}
                    elif isinstance(end_point, dict) and 'x' in end_point:
                        end_dict = end_point
                    
                    serializable_column_lines[section].append([start_dict, end_dict])
                    
                elif len(line) == 3:  # Format with rect_index
                    # Convert QPoint objects or dictionaries to dictionaries
                    start_point = line[0]
                    end_point = line[1]
                    rect_index = line[2]
                    
                    start_dict = {}
                    end_dict = {}
                    
                    if isinstance(start_point, QPoint):
                        start_dict = {'x': start_point.x(), 'y': start_point.y()}
                    elif isinstance(start_point, dict) and 'x' in start_point:
                        start_dict = start_point
                    
                    if isinstance(end_point, QPoint):
                        end_dict = {'x': end_point.x(), 'y': end_point.y()}
                    elif isinstance(end_point, dict) and 'x' in end_point:
                        end_dict = end_point
                    
                    serializable_column_lines[section].append([start_dict, end_dict, rect_index])
        
        return {
            "name": self.name_input.text().strip(),
            "description": self.desc_input.toPlainText().strip(),
            "template_type": "multi" if self.type_combo.currentText() == "Multi-page" else "single",
            "regions": serializable_regions,
            "column_lines": serializable_column_lines,
            "config": {
                "multi_table_mode": self.multi_table_mode.isChecked()
            }
        }

class TemplateManager(QWidget):
    """Widget for managing invoice templates"""
    
    template_selected = Signal(dict)  # Emits when a template is selected for use
    go_back = Signal()  # Signal to go back to previous screen
    
    def __init__(self, pdf_processor=None):
        # Ensure QApplication exists before creating widgets
        if QApplication.instance() is None:
            print("Creating QApplication instance because none exists")
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
            
        super().__init__()
        self.pdf_processor = pdf_processor
        self.db = InvoiceDatabase()
        
        # Set global stylesheet to ensure all text is visible
        self.setStyleSheet("""
            QWidget {
                color: black;
                background-color: white;
            }
            QLabel {
                color: #333333;
            }
            QTableWidgetItem {
                color: black;
            }
            QMessageBox {
                color: black;
            }
            QMessageBox QLabel {
                color: black;
            }
        """)
        
        self.initUI()
        self.load_templates()
    
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Invoice Template Management")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #333333; margin: 20px 0;")
        layout.addWidget(title)
        
        # Description
        description = QLabel("Create, manage and apply invoice extraction templates")
        description.setWordWrap(True)
        description.setStyleSheet("color: #666666; font-size: 16px; margin: 10px 0;")
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)
        
        # Actions toolbar
        actions_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Current Template")
        save_btn.clicked.connect(self.save_current_template)
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
            }
        """)
        
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self.load_templates)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3E8E41;
            }
        """)
        
        actions_layout.addWidget(save_btn)
        actions_layout.addWidget(refresh_btn)
        actions_layout.addStretch()
        
        layout.addLayout(actions_layout)
        
        # Templates table
        table_container = QFrame()
        table_container.setFrameShape(QFrame.StyledPanel)
        table_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(10, 10, 10, 10)
        
        # Add a header label for the table
        templates_header = QLabel("Your Templates")
        templates_header.setFont(QFont("Arial", 14, QFont.Bold))
        templates_header.setStyleSheet("color: #333; margin-bottom: 10px;")
        table_layout.addWidget(templates_header)
        
        self.templates_table = QTableWidget()
        self.templates_table.setColumnCount(5)
        self.templates_table.setHorizontalHeaderLabels(["Name", "Description", "Type", "Created", "Actions"])
        self.templates_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.templates_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.templates_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.templates_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.templates_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.templates_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.templates_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.templates_table.setAlternatingRowColors(True)
        self.templates_table.verticalHeader().setVisible(False)
        self.templates_table.setShowGrid(True)
        self.templates_table.setStyleSheet("""
            QTableWidget {
                border: none;
                gridline-color: #e0e0e0;
                selection-background-color: #f0f7ff;
                selection-color: #000;
                color: #000000; /* Ensuring text is black */
                background-color: white;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
                color: #000000; /* Ensuring text is black */
                background-color: white;
            }
            QTableWidget::item:selected {
                background-color: #f0f7ff;
                color: #000000; /* Ensuring selected text is black */
            }
            QHeaderView::section {
                background-color: #f8f8f8;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #e0e0e0;
                font-weight: bold;
                color: #333;
                font-size: 13px;
            }
            QTableWidget::item:alternate {
                background-color: #f9f9f9;
                color: #000000; /* Ensuring text is black */
            }
            QTableWidget::item:alternate:selected {
                background-color: #f0f7ff;
                color: #000000; /* Ensuring selected text is black */
            }
        """)
        
        table_layout.addWidget(self.templates_table)
        
        layout.addWidget(table_container)
        
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
        
        nav_layout.addWidget(back_btn)
        nav_layout.addStretch()
        
        # Add Reset Database button
        reset_db_btn = QPushButton("Reset Database")
        reset_db_btn.clicked.connect(self.reset_database)
        reset_db_btn.setStyleSheet("""
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
        nav_layout.addWidget(reset_db_btn)
        
        layout.addLayout(nav_layout)
        
        self.setLayout(layout)
    
    def get_template_id_from_row(self, row):
        """Get the template ID for the given row"""
        if 0 <= row < self.templates_table.rowCount():
            # Assuming template ID is stored in the table or can be retrieved from the database
            templates = self.db.get_all_templates()
            if row < len(templates):
                return templates[row]["id"]
        return None
    
    def show_context_menu(self, position):
        """Show context menu for the templates table"""
        menu = QMenu(self)
        
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        
        # Get the row under the cursor
        row = self.templates_table.rowAt(position.y())
        
        # Only enable actions if a valid row is clicked
        edit_action.setEnabled(row >= 0)
        delete_action.setEnabled(row >= 0)
        
        # Connect actions to slots with lambda functions that ignore the 'checked' parameter
        if row >= 0:
            template_id = self.get_template_id_from_row(row)
            if template_id:
                edit_action.triggered.connect(lambda checked=False: self.edit_template(template_id))
                delete_action.triggered.connect(lambda checked=False: self.delete_template(template_id))
        
        menu.exec_(self.templates_table.mapToGlobal(position))
    
    def edit_template(self, template_id):
        """Edit the selected template settings and configuration"""
        try:
            # Get template for editing
            template = self.db.get_template(template_id=template_id)
            if not template:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Template Not Found")
                msg_box.setText("The selected template could not be found.")
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setStyleSheet("QLabel { color: black; }")
                msg_box.exec()
                return
            
            # Show edit dialog
            dialog = EditTemplateDialog(self, template_data=template)
            
            # Set a more descriptive window title
            dialog.setWindowTitle(f"Edit Template - {template['name']}")
            
            if dialog.exec() == QDialog.Accepted:
                updated_data = dialog.get_template_data()
                new_name = updated_data["name"]
                new_description = updated_data["description"]
                
                if not new_name:
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("Invalid Name")
                    msg_box.setText("Please provide a valid template name.")
                    msg_box.setIcon(QMessageBox.Warning)
                    msg_box.setStyleSheet("QLabel { color: black; }")
                    msg_box.exec()
                    return
                
                # Show a progress/wait message
                wait_msg = QMessageBox(self)
                wait_msg.setWindowTitle("Updating Template")
                wait_msg.setText("Updating Template...")
                wait_msg.setInformativeText("Please wait while we update your template.")
                wait_msg.setStandardButtons(QMessageBox.NoButton)
                wait_msg.setStyleSheet("QLabel { color: black; }")
                wait_msg.show()
                
                # Process events to ensure the message is displayed
                QApplication.processEvents()
                
                try:
                    # Check if new name exists (if changed)
                    if new_name != template["name"]:
                        # Need to delete old template and create new one with new name
                        self.db.delete_template(template_id=template_id)
                        new_id = self.db.save_template(
                            name=new_name,
                            description=new_description,
                            regions=updated_data["regions"],
                            column_lines=updated_data["column_lines"],
                            config=updated_data["config"],
                            template_type=updated_data["template_type"]
                        )
                    else:
                        # Just update the template data
                        self.db.save_template(
                            name=new_name,
                            description=new_description,
                            regions=updated_data["regions"],
                            column_lines=updated_data["column_lines"],
                            config=updated_data["config"],
                            template_type=updated_data["template_type"]
                        )
                    
                    # Close the wait message
                    wait_msg.close()
                    
                    # Show success message with details
                    success_message = f"""
<h3>Template Updated Successfully</h3>
<p>The template has been updated with the following information:</p>
<ul>
    <li><b>Name:</b> {new_name}</li>
    <li><b>Description:</b> {new_description or "No description"}</li>
    <li><b>Type:</b> {updated_data["template_type"].title()}</li>
    <li><b>Multi-table Mode:</b> {"Enabled" if updated_data["config"]["multi_table_mode"] else "Disabled"}</li>
</ul>
<p><b>Regions:</b></p>
<ul>
"""
                    # Add region information
                    for section, rects in updated_data["regions"].items():
                        success_message += f"    <li>{section.title()}: {len(rects)} table(s)</li>"
                    
                    success_message += """
</ul>
<p><b>Column Lines:</b></p>
<ul>
"""
                    # Add column line information
                    for section, lines in updated_data["column_lines"].items():
                        success_message += f"    <li>{section.title()}: {len(lines)} line(s)</li>"
                    
                    success_message += """
</ul>
"""
                    
                    success_msg = QMessageBox(self)
                    success_msg.setWindowTitle("Template Updated")
                    success_msg.setText("Template Updated")
                    success_msg.setInformativeText(success_message)
                    success_msg.setIcon(QMessageBox.Information)
                    success_msg.setStyleSheet("QLabel { color: black; }")
                    success_msg.exec()
                    
                    # Refresh the template list
                    self.load_templates()
                except Exception as inner_e:
                    # Close the wait message
                    wait_msg.close()
                    raise inner_e
        
        except Exception as e:
            error_message = f"""
<h3>Error Updating Template</h3>
<p>An error occurred while trying to update the template:</p>
<p style='color: #D32F2F;'>{str(e)}</p>
<p>Please try again or contact support if this issue persists.</p>
"""
            error_dialog = QMessageBox(self)
            error_dialog.setWindowTitle("Error")
            error_dialog.setText("Error Updating Template")
            error_dialog.setInformativeText(error_message)
            error_dialog.setIcon(QMessageBox.Critical)
            error_dialog.setStyleSheet("QLabel { color: black; }")
            error_dialog.exec()
            
            # Print detailed error information to help with debugging
            import traceback
            traceback.print_exc()
    
    def delete_template(self, template_id):
        """Delete the selected template from the database"""
        try:
            # Get template name for confirmation
            template = self.db.get_template(template_id=template_id)
            if not template:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Template Not Found")
                msg_box.setText("The selected template could not be found.")
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setStyleSheet("QLabel { color: black; }")
                msg_box.exec()
                return
            
            # Create a more detailed confirmation message
            confirmation_message = f"""
<h3>Confirm Template Deletion</h3>

<p style='color: #D32F2F;'><b>Warning:</b> This action cannot be undone.</p>

<p>You are about to delete the following template:</p>
<ul>
    <li><b>Name:</b> {template.get('name', 'Unnamed Template')}</li>
    <li><b>Type:</b> {template.get('template_type', 'Unknown').title()}</li>
    <li><b>Regions:</b> {sum(len(rects) for rects in template.get('regions', {}).values())} table(s)</li>
</ul>

<p>Are you sure you want to proceed?</p>
"""
            
            # Create a custom confirmation dialog
            confirm_dialog = QMessageBox(self)
            confirm_dialog.setWindowTitle("Confirm Deletion")
            confirm_dialog.setText("Delete Template?")
            confirm_dialog.setInformativeText(confirmation_message)
            confirm_dialog.setIcon(QMessageBox.Warning)
            confirm_dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            confirm_dialog.setDefaultButton(QMessageBox.No)
            confirm_dialog.setStyleSheet("QLabel { color: black; }")
            
            # Set button texts
            yes_button = confirm_dialog.button(QMessageBox.Yes)
            yes_button.setText("Delete")
            no_button = confirm_dialog.button(QMessageBox.No)
            no_button.setText("Cancel")
            
            # Show the dialog
            result = confirm_dialog.exec()
            
            if result == QMessageBox.Yes:
                # Delete the template
                self.db.delete_template(template_id=template_id)
                
                # Show success message
                success_msg = QMessageBox(self)
                success_msg.setWindowTitle("Template Deleted")
                success_msg.setText("Template Successfully Deleted")
                success_msg.setInformativeText(f"The template '{template.get('name', 'Unnamed Template')}' has been permanently deleted.")
                success_msg.setIcon(QMessageBox.Information)
                success_msg.setStyleSheet("QLabel { color: black; }")
                success_msg.exec()
                
                # Refresh the template list
                self.load_templates()
        
        except Exception as e:
            error_message = f"""
<h3>Error Deleting Template</h3>
<p>An error occurred while trying to delete the template:</p>
<p style='color: #D32F2F;'>{str(e)}</p>
<p>Please try again or contact support if this issue persists.</p>
"""
            error_dialog = QMessageBox(self)
            error_dialog.setWindowTitle("Error")
            error_dialog.setText("Error Deleting Template")
            error_dialog.setInformativeText(error_message)
            error_dialog.setIcon(QMessageBox.Critical)
            error_dialog.setStyleSheet("QLabel { color: black; }")
            error_dialog.exec()
    
    def load_templates(self):
        """Load all templates from the database and display them in the table"""
        templates = self.db.get_all_templates()
        
        self.templates_table.setRowCount(len(templates))
        
        for row, template in enumerate(templates):
            # Template name
            name_item = QTableWidgetItem(template["name"])
            name_item.setToolTip(template["name"])
            name_item.setForeground(Qt.black)  # Explicitly set text color to black
            self.templates_table.setItem(row, 0, name_item)
            
            # Description
            desc_item = QTableWidgetItem(template["description"] if template["description"] else "")
            desc_item.setToolTip(template["description"] if template["description"] else "")
            desc_item.setForeground(Qt.black)  # Explicitly set text color to black
            self.templates_table.setItem(row, 1, desc_item)
            
            # Type
            type_text = "Multi-page" if template["template_type"] == "multi" else "Single-page"
            type_item = QTableWidgetItem(type_text)
            type_item.setForeground(Qt.black)  # Explicitly set text color to black
            self.templates_table.setItem(row, 2, type_item)
            
            # Created date - Format for better readability
            try:
                # Try to parse and format the date
                date_str = template["creation_date"]
                if "T" in date_str:  # ISO format
                    date_parts = date_str.split("T")[0].split("-")
                    if len(date_parts) == 3:
                        formatted_date = f"{date_parts[2]}/{date_parts[1]}/{date_parts[0]}"
                    else:
                        formatted_date = date_str
                else:
                    formatted_date = date_str
            except:
                formatted_date = template["creation_date"]
                
            date_item = QTableWidgetItem(formatted_date)
            date_item.setTextAlignment(Qt.AlignCenter)
            date_item.setForeground(Qt.black)  # Explicitly set text color to black
            self.templates_table.setItem(row, 3, date_item)
            
            # Action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 0, 4, 0)
            actions_layout.setSpacing(8)
            actions_layout.setAlignment(Qt.AlignCenter)
            
            # Apply button with icon
            apply_btn = QPushButton("Apply")
            apply_btn.setProperty("template_id", template["id"])
            apply_btn.setProperty("action", "apply")
            apply_btn.setToolTip(f"Apply template: {template['name']}")
            apply_btn.clicked.connect(lambda checked=False, tid=template["id"]: self.apply_template(tid))
            apply_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4169E1;
                    color: white;
                    padding: 5px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 70px;
                }
                QPushButton:hover {
                    background-color: #3158D3;
                }
            """)
            
            # Edit button with icon
            edit_btn = QPushButton("Edit")
            edit_btn.setProperty("template_id", template["id"])
            edit_btn.setProperty("action", "edit")
            edit_btn.setToolTip(f"Edit template: {template['name']}")
            edit_btn.clicked.connect(lambda checked=False, tid=template["id"]: self.edit_template(tid))
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    padding: 5px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 70px;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
            """)
            
            # Delete button with icon
            delete_btn = QPushButton("Delete")
            delete_btn.setProperty("template_id", template["id"])
            delete_btn.setProperty("action", "delete")
            delete_btn.setToolTip(f"Delete template: {template['name']}")
            delete_btn.clicked.connect(lambda checked=False, tid=template["id"]: self.delete_template(tid))
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #D32F2F;
                    color: white;
                    padding: 5px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 70px;
                }
                QPushButton:hover {
                    background-color: #B71C1C;
                }
            """)
            
            actions_layout.addWidget(apply_btn)
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            
            self.templates_table.setCellWidget(row, 4, actions_widget)
            
        # If no templates, show a message
        if len(templates) == 0:
            self.templates_table.setRowCount(1)
            no_templates_item = QTableWidgetItem("No templates found. Create your first template!")
            no_templates_item.setTextAlignment(Qt.AlignCenter)
            no_templates_item.setForeground(Qt.black)  # Explicitly set text color to black
            self.templates_table.setItem(0, 0, no_templates_item)
            self.templates_table.setSpan(0, 0, 1, 5)
            
        # Adjust row heights for better spacing
        for row in range(self.templates_table.rowCount()):
            self.templates_table.setRowHeight(row, 40)
    
    def save_current_template(self):
        """Save the current PDF processor settings as a template"""
        try:
            if not self.pdf_processor:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("No PDF Processor")
                msg_box.setText("Please define regions in the PDF processor before saving a template.")
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setStyleSheet("QLabel { color: black; }")
                msg_box.exec()
                return
            
            # Check if regions are defined
            if not hasattr(self.pdf_processor, 'regions') or not self.pdf_processor.regions:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("No Regions Defined")
                msg_box.setText("Please define at least one region in the PDF processor before saving a template.")
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setStyleSheet("QLabel { color: black; }")
                msg_box.exec()
                return
            
            # Show dialog to get template name and description
            dialog = SaveTemplateDialog(self)
            if dialog.exec() != QDialog.Accepted:
                return
            
            template_data = dialog.get_template_data()
            name = template_data["name"]
            description = template_data["description"]
            
            if not name:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Invalid Name")
                msg_box.setText("Please provide a valid template name.")
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setStyleSheet("QLabel { color: black; }")
                msg_box.exec()
                return
            
            # Get region and column data
            regions = self.pdf_processor.regions
            column_lines = self.pdf_processor.column_lines
            
            # Convert QRect objects to dictionaries for JSON serialization
            serializable_regions = {}
            for section, rects in regions.items():
                serializable_regions[section] = []
                for rect in rects:
                    # Convert QRect to a dictionary
                    serializable_regions[section].append({
                        'x': rect.x(),
                        'y': rect.y(),
                        'width': rect.width(),
                        'height': rect.height()
                    })
            
            # Convert column lines to serializable format
            serializable_column_lines = {}
            for section, lines in column_lines.items():
                serializable_column_lines[section] = []
                for line in lines:
                    # Format depends on the structure of line
                    if len(line) == 2:  # Simple start-end point format
                        # Convert QPoint objects to dictionaries
                        serializable_line = [
                            {'x': line[0].x(), 'y': line[0].y()},
                            {'x': line[1].x(), 'y': line[1].y()}
                        ]
                        serializable_column_lines[section].append(serializable_line)
                    elif len(line) == 3:  # Format with rect_index
                        # Convert QPoint objects to dictionaries
                        serializable_line = [
                            {'x': line[0].x(), 'y': line[0].y()},
                            {'x': line[1].x(), 'y': line[1].y()},
                            line[2]  # rect_index is already an integer
                        ]
                        serializable_column_lines[section].append(serializable_line)
            
            # Get additional configuration parameters
            config = {
                "multi_table_mode": self.pdf_processor.multi_table_mode
            }
            
            # Save template to the database
            template_id = self.db.save_template(
                name=name,
                description=description,
                regions=serializable_regions,
                column_lines=serializable_column_lines,
                config=config
            )
            
            # Retrieve the full template info to show a preview
            saved_template = self.db.get_template(template_id=template_id)
            
            # Create preview text
            template_preview = f"""
<h3>Template: {saved_template['name']}</h3>

<p><b>Description:</b> {saved_template['description'] or 'No description'}</p>

<p><b>Saved Data:</b></p>
<ul>
"""
            
            # Add information about regions
            region_count = 0
            if 'regions' in saved_template and saved_template['regions']:
                for section, rects in saved_template['regions'].items():
                    if rects:
                        region_count += len(rects)
                        template_preview += f"<li>{section.title()}: {len(rects)} table(s)</li>"
            
            # Add column line information
            column_lines_count = 0
            if 'column_lines' in saved_template and saved_template['column_lines']:
                for section, lines in saved_template['column_lines'].items():
                    if lines:
                        column_lines_count += len(lines)
            
            template_preview += f"""
</ul>

<p><b>Total Regions:</b> {region_count}</p>
<p><b>Total Column Lines:</b> {column_lines_count}</p>
<p><b>Multi-Table Mode:</b> {'Enabled' if config.get('multi_table_mode', False) else 'Disabled'}</p>
"""
            
            # Show the template saved message with preview
            success_msg = QMessageBox(self)
            success_msg.setWindowTitle("Template Saved")
            success_msg.setText("Template Saved Successfully")
            success_msg.setInformativeText(template_preview)
            success_msg.setIcon(QMessageBox.Information)
            success_msg.setStyleSheet("QLabel { color: black; }")
            success_msg.exec()
            
            # Reload the templates list
            self.load_templates()
            
        except Exception as e:
            QMessageBox.critical(self, "Error Saving Template", f"An error occurred: {str(e)}")
            # Print detailed error information to help with debugging
            import traceback
            traceback.print_exc()
    
    def apply_template(self, template_id):
        """Apply the selected template to the current PDF processor"""
        try:
            from PySide6.QtCore import QRect, QPoint
            
            template = self.db.get_template(template_id=template_id)
            if not template:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Template Not Found")
                msg_box.setText("The selected template could not be found.")
                msg_box.setIcon(QMessageBox.Warning) 
                msg_box.setStyleSheet("QLabel { color: black; }")
                msg_box.exec()
                return
            
            # Show a preview of the template settings
            template_preview = f"""
<h3>Template: {template['name']}</h3>

<p><b>Description:</b> {template['description'] or 'No description'}</p>

<p><b>Tables:</b></p>
<ul>
"""
            
            # Add information about regions
            region_count = 0
            if 'regions' in template and template['regions']:
                for section, rects in template['regions'].items():
                    if rects:
                        region_count += len(rects)
                        template_preview += f"<li>{section.title()}: {len(rects)} table(s)</li>"
            
            template_preview += f"""
</ul>

<p><b>Column Lines:</b> {'Yes' if 'column_lines' in template and any(template['column_lines'].values()) else 'No'}</p>
<p><b>Total Regions:</b> {region_count}</p>
<p><b>Configuration:</b> {template.get('config', {})}</p>
"""
            
            # Show the preview dialog
            preview = QMessageBox(self)
            preview.setWindowTitle("Template Preview")
            preview.setText("Template Preview")
            preview.setInformativeText(template_preview)
            preview.setStandardButtons(QMessageBox.Apply | QMessageBox.Cancel)
            preview.setDefaultButton(QMessageBox.Apply)
            preview.setStyleSheet("QLabel { color: black; }")
            
            # If the user confirms, apply the template
            if preview.exec() == QMessageBox.Apply:
                # Convert serialized regions back to QRect objects if needed
                if 'regions' in template and template['regions']:
                    converted_regions = {}
                    for section, rects in template['regions'].items():
                        converted_regions[section] = []
                        for rect_data in rects:
                            # Check if the rect is already a QRect object or a dictionary
                            if isinstance(rect_data, dict) and 'x' in rect_data:
                                # Convert dictionary to QRect
                                rect = QRect(
                                    rect_data['x'], 
                                    rect_data['y'], 
                                    rect_data['width'], 
                                    rect_data['height']
                                )
                                converted_regions[section].append(rect)
                            else:
                                # Already a QRect or some other format, keep as is
                                converted_regions[section].append(rect_data)
                    
                    template['regions'] = converted_regions
                
                # Convert serialized column lines back to QPoint objects if needed
                if 'column_lines' in template and template['column_lines']:
                    converted_column_lines = {}
                    for section, lines in template['column_lines'].items():
                        converted_column_lines[section] = []
                        for line_data in lines:
                            # Handle different formats
                            if len(line_data) == 2:
                                # Simple start-end point format
                                start_point = line_data[0]
                                end_point = line_data[1]
                                
                                # Convert dictionary to QPoint if needed
                                if isinstance(start_point, dict) and 'x' in start_point:
                                    start_point = QPoint(start_point['x'], start_point['y'])
                                if isinstance(end_point, dict) and 'x' in end_point:
                                    end_point = QPoint(end_point['x'], end_point['y'])
                                    
                                converted_column_lines[section].append([start_point, end_point])
                            elif len(line_data) == 3:
                                # Format with rect_index
                                start_point = line_data[0]
                                end_point = line_data[1]
                                rect_index = line_data[2]
                                
                                # Convert dictionary to QPoint if needed
                                if isinstance(start_point, dict) and 'x' in start_point:
                                    start_point = QPoint(start_point['x'], start_point['y'])
                                if isinstance(end_point, dict) and 'x' in end_point:
                                    end_point = QPoint(end_point['x'], end_point['y'])
                                    
                                converted_column_lines[section].append([start_point, end_point, rect_index])
                    
                    template['column_lines'] = converted_column_lines
                
                # Add debugging information
                print("\n[DEBUG] Template data that will be applied:")
                for section, rects in template['regions'].items():
                    print(f"Section: {section} - {len(rects)} regions")
                    for i, rect in enumerate(rects):
                        print(f"  Region {i}: x={rect.x()}, y={rect.y()}, width={rect.width()}, height={rect.height()}")
                
                for section, lines in template['column_lines'].items():
                    print(f"Column lines for section: {section} - {len(lines)} lines")
                    for i, line in enumerate(lines):
                        if len(line) == 2:
                            print(f"  Line {i}: start=({line[0].x()}, {line[0].y()}), end=({line[1].x()}, {line[1].y()})")
                        elif len(line) == 3:
                            print(f"  Line {i}: start=({line[0].x()}, {line[0].y()}), end=({line[1].x()}, {line[1].y()}), rect_index={line[2]}")
                
                # Emit the template selection signal with the template data
                self.template_selected.emit(template)
                
                # Show success message
                success_msg = QMessageBox(self)
                success_msg.setWindowTitle("Template Applied")
                success_msg.setText("Template Applied Successfully")
                success_msg.setInformativeText(f"The template '{template['name']}' has been applied. You can now use it for PDF processing.")
                success_msg.setIcon(QMessageBox.Information)
                success_msg.setStyleSheet("QLabel { color: black; }")
                success_msg.exec()
                
        except Exception as e:
            error_dialog = QMessageBox(self)
            error_dialog.setWindowTitle("Error")
            error_dialog.setText("Error Applying Template")
            error_dialog.setInformativeText(f"An error occurred: {str(e)}")
            error_dialog.setIcon(QMessageBox.Critical)
            error_dialog.setStyleSheet("QLabel { color: black; }")
            error_dialog.exec()
            # Print detailed error information to help with debugging
            import traceback
            traceback.print_exc()
    
    def closeEvent(self, event):
        """Close database connection when widget is closed"""
        self.db.close()
        super().closeEvent(event)

    def refresh(self):
        """Refresh the template list and update the UI"""
        # Reload templates from the database
        self.load_templates()
        
        # Update any UI components that need refreshing
        # Make sure we're showing the latest state of the system
        if self.pdf_processor:
            # Check if we have regions to save
            has_regions = (hasattr(self.pdf_processor, 'regions') and 
                          self.pdf_processor.regions and 
                          any(len(rects) > 0 for rects in self.pdf_processor.regions.values()))
            
            # Update the save button state based on whether we have regions
            save_buttons = [btn for btn in self.findChildren(QPushButton) 
                           if btn.text() == "Save Current Template"]
            for btn in save_buttons:
                btn.setEnabled(has_regions)
                
        print("Template manager refreshed")

    def reset_database(self):
        """Delete and recreate the SQLite database, removing all templates"""
        # Confirm with the user before proceeding
        response = QMessageBox.warning(
            self,
            "Reset Database",
            "This will delete ALL templates from the database.\n\n"
            "This action CANNOT be undone. Are you sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # Default is No to prevent accidental deletion
        )
        
        if response == QMessageBox.No:
            return
            
        try:
            # Close the database connection
            self.db.close()
            
            # Delete the database file
            if os.path.exists('invoice_templates.db'):
                os.remove('invoice_templates.db')
                
                # Create a new database
                self.db = InvoiceDatabase()  # This will recreate the database
                
                # Refresh the templates table
                self.templates_table.setRowCount(0)
                
                QMessageBox.information(
                    self,
                    "Database Reset",
                    "The database has been successfully reset. All templates have been removed."
                )
                
                print("\n" + "="*80)
                print("DATABASE RESET SUCCESSFUL")
                print("All templates have been removed and the database has been recreated.")
                print("="*80)
            else:
                # If the file doesn't exist, just create a new one
                self.db = InvoiceDatabase()  # This will create the database
                
                QMessageBox.information(
                    self,
                    "Database Created",
                    "A new empty database has been created."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to reset database: {str(e)}"
            )
            print(f"✗ Error resetting database: {str(e)}")
            import traceback
            traceback.print_exc() 