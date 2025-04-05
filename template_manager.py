from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QScrollArea, QFrame, QLineEdit, QTextEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
                             QFormLayout, QMessageBox, QInputDialog, QDialogButtonBox,
                             QApplication, QTabWidget, QCheckBox, QComboBox, QGroupBox, QGridLayout, QSpinBox, QListWidget, QListWidgetItem,
                             QMainWindow, QStackedWidget, QFileDialog, QScrollArea, QFrame, QSplitter, QGridLayout, QLineEdit, QComboBox,
                             QListWidget, QProgressBar, QTabWidget, QTextEdit, QCheckBox, QProgressDialog)
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QFont, QIcon
from database import InvoiceDatabase
import os
import datetime
import json
import sqlite3

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
        
        # Initialize page count
        self.page_count = template_data.get('page_count', 1) if template_data else 1
        self.current_page = 0
        
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
        self.type_combo.currentTextChanged.connect(self.on_template_type_changed)
        type_layout.addRow("Template Type:", self.type_combo)
        
        # Page count (only for multi-page)
        # Create a container widget for the page count layout
        self.page_count_container = QWidget()
        self.page_count_layout = QFormLayout(self.page_count_container)
        self.page_count_spin = QSpinBox()
        self.page_count_spin.setMinimum(1)
        self.page_count_spin.setMaximum(10)  # Reasonable limit
        self.page_count_spin.setValue(self.page_count)
        self.page_count_spin.valueChanged.connect(self.on_page_count_changed)
        self.page_count_layout.addRow("Number of Pages:", self.page_count_spin)
        
        # Show/hide page count based on template type
        self.update_page_count_visibility()
        
        layout.addLayout(name_layout)
        layout.addLayout(desc_layout)
        layout.addLayout(type_layout)
        layout.addWidget(self.page_count_container)
        layout.addStretch()
        
        return tab
    
    def create_regions_tab(self):
        """Create the table regions tab with page support"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # Page navigation for multi-page templates
        if self.template_data.get("template_type") == "multi":
            page_nav_layout = QHBoxLayout()
            self.prev_page_btn = QPushButton("← Previous Page")
            self.next_page_btn = QPushButton("Next Page →")
            self.page_label = QLabel(f"Page {self.current_page + 1} of {self.page_count}")
            
            self.prev_page_btn.clicked.connect(self.prev_page)
            self.next_page_btn.clicked.connect(self.next_page)
            
            page_nav_layout.addWidget(self.prev_page_btn)
            page_nav_layout.addWidget(self.page_label)
            page_nav_layout.addWidget(self.next_page_btn)
            
            # Add clone page button for multi-page templates
            clone_btn = QPushButton("Clone Regions to Another Page")
            clone_btn.setToolTip("Copy regions from this page to another page")
            clone_btn.clicked.connect(self.clone_regions_to_another_page)
            clone_btn.setStyleSheet("""
                QPushButton {
                    background-color: #5bc0de;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #46b8da;
                }
            """)
            page_nav_layout.addWidget(clone_btn)
            
            layout.addLayout(page_nav_layout)
        
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
        self.load_regions_for_current_page()
        
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
        """Create the column lines tab with page support"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # Page navigation for multi-page templates
        if self.template_data.get("template_type") == "multi":
            page_nav_layout = QHBoxLayout()
            self.prev_page_btn_cols = QPushButton("← Previous Page")
            self.next_page_btn_cols = QPushButton("Next Page →")
            self.page_label_cols = QLabel(f"Page {self.current_page + 1} of {self.page_count}")
            
            self.prev_page_btn_cols.clicked.connect(self.prev_page)
            self.next_page_btn_cols.clicked.connect(self.next_page)
            
            page_nav_layout.addWidget(self.prev_page_btn_cols)
            page_nav_layout.addWidget(self.page_label_cols)
            page_nav_layout.addWidget(self.next_page_btn_cols)
            
            # Add clone page button for multi-page templates
            clone_btn = QPushButton("Clone Column Lines to Another Page")
            clone_btn.setToolTip("Copy column lines from this page to another page")
            clone_btn.clicked.connect(self.clone_column_lines_to_another_page)
            clone_btn.setStyleSheet("""
                QPushButton {
                    background-color: #5bc0de;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #46b8da;
                }
            """)
            page_nav_layout.addWidget(clone_btn)
            
            layout.addLayout(page_nav_layout)
        
        # Create table for column lines
        self.columns_table = QTableWidget()
        self.columns_table.setColumnCount(4)
        self.columns_table.setHorizontalHeaderLabels(["Section", "Table #", "X Position", "Description"])
        self.columns_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.columns_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.columns_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.columns_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        
        # Add column lines from template data
        self.load_column_lines_for_current_page()
        
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
        """Create the configuration tab with extraction parameters and regex patterns"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setSpacing(16)
        
        # Page navigation for multi-page templates with page-specific config
        if self.template_data.get("template_type") == "multi":
            page_nav_layout = QHBoxLayout()
            self.prev_page_btn_config = QPushButton("← Previous Page")
            self.next_page_btn_config = QPushButton("Next Page →")
            self.page_label_config = QLabel(f"Page {self.current_page + 1} of {self.page_count}")
            
            self.prev_page_btn_config.clicked.connect(self.prev_page)
            self.next_page_btn_config.clicked.connect(self.next_page)
            
            page_nav_layout.addWidget(self.prev_page_btn_config)
            page_nav_layout.addWidget(self.page_label_config)
            page_nav_layout.addWidget(self.next_page_btn_config)
            
            # Add page-specific config checkbox
            self.page_specific_config = QCheckBox("Enable Page-Specific Configuration")
            self.page_specific_config.setToolTip("Configure extraction parameters separately for each page")
            
            # Check if page-specific configs already exist
            if 'page_configs' in self.template_data:
                self.page_specific_config.setChecked(True)
                
            page_nav_layout.addWidget(self.page_specific_config)
            main_layout.addLayout(page_nav_layout)
        
        # Create sections using group boxes
        # 1. Extraction Parameters Section
        extraction_group = QGroupBox("Extraction Parameters")
        extraction_layout = QVBoxLayout()
        
        # Row tolerance parameters
        tol_form = QFormLayout()
        
        # Get default values from template data if available
        config = self.template_data.get('config', {})
        
        # Handle both old and new format - check for extraction_params first
        extraction_params = {}
        if 'extraction_params' in config:
            extraction_params = config.get('extraction_params', {})
            print("Found extraction_params in config - using nested structure")
        else:
            # Fallback to old format where parameters might be directly in config
            print("No extraction_params found - using direct config values")
        
        # Header row tolerance
        header_params = {}
        if 'header' in extraction_params:
            header_params = extraction_params.get('header', {})
        elif 'header' in config:
            header_params = config.get('header', {})
        
        self.header_row_tol = QSpinBox()
        self.header_row_tol.setRange(0, 20)
        row_tol_value = header_params.get('row_tol', None)
        if row_tol_value is None:
            row_tol_value = config.get('row_tol', 3)  # Global fallback
        self.header_row_tol.setValue(row_tol_value)
        self.header_row_tol.setToolTip("Tolerance for header row extraction (higher = more flexible)")
        tol_form.addRow("Header Row Tolerance:", self.header_row_tol)
        
        # Items row tolerance
        items_params = {}
        if 'items' in extraction_params:
            items_params = extraction_params.get('items', {})
        elif 'items' in config:
            items_params = config.get('items', {})
        
        self.items_row_tol = QSpinBox()
        self.items_row_tol.setRange(0, 20)
        row_tol_value = items_params.get('row_tol', None)
        if row_tol_value is None:
            row_tol_value = config.get('row_tol', 3)  # Global fallback
        self.items_row_tol.setValue(row_tol_value)
        self.items_row_tol.setToolTip("Tolerance for items row extraction (higher = more flexible)")
        tol_form.addRow("Items Row Tolerance:", self.items_row_tol)
        
        # Summary row tolerance
        summary_params = {}
        if 'summary' in extraction_params:
            summary_params = extraction_params.get('summary', {})
        elif 'summary' in config:
            summary_params = config.get('summary', {})
        
        self.summary_row_tol = QSpinBox()
        self.summary_row_tol.setRange(0, 20)
        row_tol_value = summary_params.get('row_tol', None)
        if row_tol_value is None:
            row_tol_value = config.get('row_tol', 3)  # Global fallback
        self.summary_row_tol.setValue(row_tol_value)
        self.summary_row_tol.setToolTip("Tolerance for summary row extraction (higher = more flexible)")
        tol_form.addRow("Summary Row Tolerance:", self.summary_row_tol)
        
        extraction_layout.addLayout(tol_form)
        
        # Text processing options
        text_form = QFormLayout()
        
        # Split text option
        self.split_text = QCheckBox("Enable")
        split_text_value = extraction_params.get('split_text', None)
        if split_text_value is None:
            split_text_value = config.get('split_text', True)
        self.split_text.setChecked(split_text_value)
        self.split_text.setToolTip("Split text that may contain multiple values")
        text_form.addRow("Split Text:", self.split_text)
        
        # Strip text option
        self.strip_text = QLineEdit()
        strip_text_value = extraction_params.get('strip_text', None)
        if strip_text_value is None:
            strip_text_value = config.get('strip_text', '\n')
        if strip_text_value == '\n':
            self.strip_text.setText("\\n")
        else:
            self.strip_text.setText(strip_text_value)
        self.strip_text.setToolTip("Characters to strip from text (use \\n for newlines)")
        text_form.addRow("Strip Text:", self.strip_text)
        
        extraction_layout.addLayout(text_form)
        
        # Multi-table mode option
        self.multi_table_mode = QCheckBox("Enable Multi-Table Mode")
        self.multi_table_mode.setChecked(config.get('multi_table_mode', False))
        self.multi_table_mode.setToolTip("Process multiple tables in the header section")
        extraction_layout.addWidget(self.multi_table_mode)
        
        extraction_group.setLayout(extraction_layout)
        main_layout.addWidget(extraction_group)
        
        # 2. Regex Patterns Section
        regex_group = QGroupBox("Regex Patterns")
        regex_layout = QVBoxLayout()
        
        # Get existing patterns if available
        regex_patterns = {}
        
        # First check for regex_patterns in extraction_params
        if 'regex_patterns' in extraction_params:
            regex_patterns = extraction_params.get('regex_patterns', {})
            print("Found regex_patterns in extraction_params")
        # Then check for regex_patterns directly in config
        elif 'regex_patterns' in config:
            regex_patterns = config.get('regex_patterns', {})
            print("Found regex_patterns directly in config")
        
        # Create tabs for different sections
        regex_tabs = QTabWidget()
        
        # Header patterns
        header_tab = QWidget()
        header_layout = QFormLayout(header_tab)
        
        header_patterns = regex_patterns.get('header', {})
        self.header_start_pattern = QLineEdit()
        self.header_start_pattern.setText(header_patterns.get('start', ''))
        self.header_start_pattern.setToolTip("Pattern to identify the start of the header section")
        header_layout.addRow("Start Pattern:", self.header_start_pattern)
        
        self.header_end_pattern = QLineEdit()
        self.header_end_pattern.setText(header_patterns.get('end', ''))
        self.header_end_pattern.setToolTip("Pattern to identify the end of the header section")
        header_layout.addRow("End Pattern:", self.header_end_pattern)
        
        self.header_skip_pattern = QLineEdit()
        self.header_skip_pattern.setText(header_patterns.get('skip', ''))
        self.header_skip_pattern.setToolTip("Pattern to identify rows to skip in the header section")
        header_layout.addRow("Skip Pattern:", self.header_skip_pattern)
        
        regex_tabs.addTab(header_tab, "Header")
        
        # Items patterns
        items_tab = QWidget()
        items_layout = QFormLayout(items_tab)
        
        items_patterns = regex_patterns.get('items', {})
        self.items_start_pattern = QLineEdit()
        self.items_start_pattern.setText(items_patterns.get('start', ''))
        self.items_start_pattern.setToolTip("Pattern to identify the start of the items section")
        items_layout.addRow("Start Pattern:", self.items_start_pattern)
        
        self.items_end_pattern = QLineEdit()
        self.items_end_pattern.setText(items_patterns.get('end', ''))
        self.items_end_pattern.setToolTip("Pattern to identify the end of the items section")
        items_layout.addRow("End Pattern:", self.items_end_pattern)
        
        self.items_skip_pattern = QLineEdit()
        self.items_skip_pattern.setText(items_patterns.get('skip', ''))
        self.items_skip_pattern.setToolTip("Pattern to identify rows to skip in the items section")
        items_layout.addRow("Skip Pattern:", self.items_skip_pattern)
        
        regex_tabs.addTab(items_tab, "Items")
        
        # Summary patterns
        summary_tab = QWidget()
        summary_layout = QFormLayout(summary_tab)
        
        summary_patterns = regex_patterns.get('summary', {})
        self.summary_start_pattern = QLineEdit()
        self.summary_start_pattern.setText(summary_patterns.get('start', ''))
        self.summary_start_pattern.setToolTip("Pattern to identify the start of the summary section")
        summary_layout.addRow("Start Pattern:", self.summary_start_pattern)
        
        self.summary_end_pattern = QLineEdit()
        self.summary_end_pattern.setText(summary_patterns.get('end', ''))
        self.summary_end_pattern.setToolTip("Pattern to identify the end of the summary section")
        summary_layout.addRow("End Pattern:", self.summary_end_pattern)
        
        self.summary_skip_pattern = QLineEdit()
        self.summary_skip_pattern.setText(summary_patterns.get('skip', ''))
        self.summary_skip_pattern.setToolTip("Pattern to identify rows to skip in the summary section")
        summary_layout.addRow("Skip Pattern:", self.summary_skip_pattern)
        
        regex_tabs.addTab(summary_tab, "Summary")
        
        regex_layout.addWidget(regex_tabs)
        regex_group.setLayout(regex_layout)
        main_layout.addWidget(regex_group)
        
        # Add help text
        help_label = QLabel("Regex patterns allow fine-tuning the extraction process. Leave empty if not needed.")
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #666; font-style: italic;")
        main_layout.addWidget(help_label)
        
        # Add a debug section to show the actual config structure
        debug_btn = QPushButton("Show Raw Config")
        debug_btn.setToolTip("Show the raw configuration structure for debugging")
        debug_btn.clicked.connect(lambda: self.show_raw_config(config))
        main_layout.addWidget(debug_btn)
        
        main_layout.addStretch()
        
        return tab

    def clone_column_lines_to_another_page(self):
        """Clone column lines from the current page to another page"""
        if self.template_data.get("template_type") != "multi" or self.page_count <= 1:
            return
            
        # Get current page column lines
        current_column_lines = self.get_column_lines_for_current_page()
        if not current_column_lines or not any(current_column_lines.values()):
            QMessageBox.warning(
                self,
                "No Column Lines to Clone",
                "There are no column lines defined on the current page to clone.",
                QMessageBox.Ok
            )
            return
            
        # Create a dialog to select the target page
        target_pages = []
        for i in range(self.page_count):
            if i != self.current_page:  # Exclude current page
                target_pages.append(f"Page {i + 1}")
                
        if not target_pages:
            QMessageBox.warning(
                self,
                "No Target Pages",
                "There are no other pages to clone column lines to.",
                QMessageBox.Ok
            )
            return
            
        # Create dialog for selecting target page and options
        dialog = QDialog(self)
        dialog.setWindowTitle("Clone Column Lines to Another Page")
        dialog.setMinimumWidth(400)
        
        dialog_layout = QVBoxLayout()
        
        # Explanation
        explanation = QLabel("Select the page(s) to clone the current column lines to:")
        explanation.setWordWrap(True)
        dialog_layout.addWidget(explanation)
        
        # Target page selection
        page_list = QListWidget()
        for page in target_pages:
            item = QListWidgetItem(page)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            page_list.addItem(item)
        dialog_layout.addWidget(page_list)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        replace_option = QCheckBox("Replace existing column lines on target page(s)")
        replace_option.setChecked(True)
        options_layout.addWidget(replace_option)
        
        options_group.setLayout(options_layout)
        dialog_layout.addWidget(options_group)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dialog_layout.addWidget(buttons)
        
        dialog.setLayout(dialog_layout)
        
        # Show dialog and process result
        if dialog.exec() == QDialog.Accepted:
            # Get selected pages
            selected_pages = []
            for i in range(page_list.count()):
                item = page_list.item(i)
                if item.checkState() == Qt.Checked:
                    # Convert from display name "Page X" to 0-based index
                    page_idx = int(item.text().split(" ")[1]) - 1
                    selected_pages.append(page_idx)
            
            if not selected_pages:
                QMessageBox.warning(
                    self,
                    "No Pages Selected",
                    "No target pages were selected. The operation was cancelled.",
                    QMessageBox.Ok
                )
                return
            
            # Apply cloning to each selected page
            replace_existing = replace_option.isChecked()
            cloned_to = []
            
            # Make sure page_column_lines is initialized
            if 'page_column_lines' not in self.template_data:
                self.template_data['page_column_lines'] = [{}] * self.page_count
            
            # Extend page_column_lines if needed
            while len(self.template_data['page_column_lines']) < self.page_count:
                self.template_data['page_column_lines'].append({})
            
            for page_idx in selected_pages:
                # If replace is checked, or if the target page has no column lines
                if replace_existing or not self.template_data['page_column_lines'][page_idx]:
                    # Create a deep copy of the current column lines
                    import copy
                    self.template_data['page_column_lines'][page_idx] = copy.deepcopy(current_column_lines)
                    cloned_to.append(page_idx + 1)  # Convert to 1-based for display
                else:
                    # Merge column lines (add to existing)
                    target_column_lines = self.template_data['page_column_lines'][page_idx]
                    for section, lines in current_column_lines.items():
                        if section not in target_column_lines:
                            target_column_lines[section] = []
                        target_column_lines[section].extend(copy.deepcopy(lines))
                    cloned_to.append(page_idx + 1)  # Convert to 1-based for display
            
            # Show success message
            success_message = f"Column lines cloned successfully to page(s): {', '.join(map(str, cloned_to))}"
            QMessageBox.information(
                self,
                "Column Lines Cloned",
                success_message,
                QMessageBox.Ok
            )
            
            # If current page is one of the target pages, refresh the view
            if self.current_page in selected_pages:
                self.load_column_lines_for_current_page()

    def on_template_type_changed(self, template_type):
        """Handle template type change"""
        is_multi_page = template_type == "Multi-page"
        self.update_page_count_visibility()
        if is_multi_page:
            self.page_count = max(1, self.page_count)
            self.page_count_spin.setValue(self.page_count)
        else:
            self.page_count = 1
            self.page_count_spin.setValue(1)

    def update_page_count_visibility(self):
        """Show/hide page count based on template type"""
        is_multi_page = self.type_combo.currentText() == "Multi-page"
        self.page_count_container.setVisible(is_multi_page)

    def on_page_count_changed(self, value):
        """Handle page count change"""
        self.page_count = value
        if self.current_page >= value:
            self.current_page = value - 1
        self.update_page_navigation()

    def prev_page(self):
        """Navigate to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page_navigation()
            self.load_regions_for_current_page()
            self.load_column_lines_for_current_page()

    def next_page(self):
        """Navigate to next page"""
        if self.current_page < self.page_count - 1:
            self.current_page += 1
            self.update_page_navigation()
            self.load_regions_for_current_page()
            self.load_column_lines_for_current_page()

    def update_page_navigation(self):
        """Update page navigation UI"""
        if hasattr(self, 'page_label'):
            self.page_label.setText(f"Page {self.current_page + 1} of {self.page_count}")
        if hasattr(self, 'page_label_cols'):
            self.page_label_cols.setText(f"Page {self.current_page + 1} of {self.page_count}")
        if hasattr(self, 'page_label_config'):
            self.page_label_config.setText(f"Page {self.current_page + 1} of {self.page_count}")
        
        # Update button states
        if hasattr(self, 'prev_page_btn'):
            self.prev_page_btn.setEnabled(self.current_page > 0)
        if hasattr(self, 'next_page_btn'):
            self.next_page_btn.setEnabled(self.current_page < self.page_count - 1)
        if hasattr(self, 'prev_page_btn_cols'):
            self.prev_page_btn_cols.setEnabled(self.current_page > 0)
        if hasattr(self, 'next_page_btn_cols'):
            self.next_page_btn_cols.setEnabled(self.current_page < self.page_count - 1)
        if hasattr(self, 'prev_page_btn_config'):
            self.prev_page_btn_config.setEnabled(self.current_page > 0)
        if hasattr(self, 'next_page_btn_config'):
            self.next_page_btn_config.setEnabled(self.current_page < self.page_count - 1)
            
        # Update config fields if page-specific config is enabled
        if (hasattr(self, 'page_specific_config') and 
            self.page_specific_config.isChecked() and 
            'page_configs' in self.template_data):
            
            page_configs = self.template_data['page_configs']
            if self.current_page < len(page_configs) and page_configs[self.current_page]:
                # Load page-specific config
                if hasattr(self, 'load_page_specific_config'):
                    self.load_page_specific_config(page_configs[self.current_page])

    def load_regions_for_current_page(self):
        """Load regions for the current page"""
        self.regions_table.setRowCount(0)
        
        # Get regions for current page
        regions = self.get_regions_for_current_page()
        
        row = 0
        for section, rects in regions.items():
            for i, rect in enumerate(rects):
                self.regions_table.insertRow(row)
                self.regions_table.setItem(row, 0, QTableWidgetItem(section.title()))
                self.regions_table.setItem(row, 1, QTableWidgetItem(str(i + 1)))
                
                # Handle different region formats
                if isinstance(rect, QRect):
                    # QRect format (x,y,width,height)
                    x = rect.x()
                    y = rect.y()
                    width = rect.width()
                    height = rect.height()
                elif isinstance(rect, dict):
                    if 'x' in rect and 'y' in rect and 'width' in rect and 'height' in rect:
                        # Dictionary format (x,y,width,height)
                        x = rect['x']
                        y = rect['y']
                        width = rect['width'] 
                        height = rect['height']
                    elif 'x1' in rect and 'y1' in rect and 'x2' in rect and 'y2' in rect:
                        # Dictionary format (x1,y1,x2,y2)
                        x = rect['x1']
                        y = rect['y1']
                        width = rect['x2'] - rect['x1']
                        height = rect['y2'] - rect['y1']
                    else:
                        print(f"Warning: Unknown region format in {section}: {rect}")
                        continue
                else:
                    print(f"Warning: Unknown region type in {section}: {type(rect)}")
                    continue
                
                # Store drawn format (x,y,width,height)
                self.regions_table.setItem(row, 2, QTableWidgetItem(str(x)))
                self.regions_table.setItem(row, 3, QTableWidgetItem(str(y)))
                self.regions_table.setItem(row, 4, QTableWidgetItem(str(width)))
                self.regions_table.setItem(row, 5, QTableWidgetItem(str(height)))
                
                # Store scaled format (x1,y1,x2,y2)
                x1 = x
                y1 = y
                x2 = x + width
                y2 = y + height
                scaled_text = f"({x1}, {y1}, {x2}, {y2})"
                scaled_item = QTableWidgetItem(scaled_text)
                scaled_item.setToolTip("Format: x1, y1, x2, y2")
                self.regions_table.setItem(row, 6, scaled_item)
                
                row += 1

    def load_column_lines_for_current_page(self):
        """Load column lines for the current page"""
        try:
                # Clear existing items
            self.columns_table.setRowCount(0)
            
                        # Get current page's column lines
            column_lines = self.get_column_lines_for_current_page()
            
            if not column_lines:
                return
            
            # Add column lines to the table
            for section, lines in column_lines.items():
                if not lines:
                    continue
                    
                for line in lines:
                    try:
                        # Debug output to see the line data structure
                        print(f"\nProcessing line in {section}:")
                        print(f"Line type: {type(line)}")
                        print(f"Line data: {line}")
                        
                        # Handle both old and new formats
                        if isinstance(line, (list, tuple)):
                            if len(line) >= 2:
                                # Old format: [QPoint, QPoint, region_index] or [dict, dict, region_index]
                                start_point = line[0]
                                end_point = line[1]
                                region_index = line[2] if len(line) > 2 else 0
                                
                                # Convert dictionary to QPoint if needed
                                if isinstance(start_point, dict) and 'x' in start_point:
                                    start_point = QPoint(start_point['x'], start_point['y'])
                                if isinstance(end_point, dict) and 'x' in end_point:
                                    end_point = QPoint(end_point['x'], end_point['y'])
                                else:
                                    print(f"Warning: Invalid line format in {section}, skipping")
                                    continue
                        elif isinstance(line, dict):
                            # New format: {'x1': float, 'y1': float, 'x2': float, 'y2': float, 'region_index': int}
                            if 'x1' in line and 'y1' in line and 'x2' in line and 'y2' in line:
                                start_point = QPoint(int(line['x1']), int(line['y1']))
                                end_point = QPoint(int(line['x2']), int(line['y2']))
                                region_index = line.get('region_index', 0)
                            else:
                                print(f"Warning: Invalid dictionary format in {section}, missing coordinates")
                                print(f"Available keys: {line.keys()}")
                                continue
                        else:
                            print(f"Warning: Unknown line format in {section}, skipping")
                            continue
                        
                        # Add row to table
                        row = self.columns_table.rowCount()
                        self.columns_table.insertRow(row)
                        
                        # Add section
                        section_item = QTableWidgetItem(section)
                        section_item.setFlags(section_item.flags() & ~Qt.ItemIsEditable)
                        self.columns_table.setItem(row, 0, section_item)
                        
                        # Add table number (region index + 1)
                        table_item = QTableWidgetItem(str(region_index + 1))
                        table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                        self.columns_table.setItem(row, 1, table_item)
                        
                        # Add X position (using start point X)
                        x_pos_item = QTableWidgetItem(f"{start_point.x():.1f}")
                        x_pos_item.setFlags(x_pos_item.flags() & ~Qt.ItemIsEditable)
                        self.columns_table.setItem(row, 2, x_pos_item)
                        
                        # Add description with coordinates
                        desc = f"Start: ({start_point.x()}, {start_point.y()}) End: ({end_point.x()}, {end_point.y()})"
                        desc_item = QTableWidgetItem(desc)
                        desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
                        self.columns_table.setItem(row, 3, desc_item)
                        
                    except Exception as e:
                        print(f"Error processing line in {section}: {str(e)}")
                        continue
            
            # Adjust column widths
            self.columns_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"Error loading column lines: {str(e)}")
            import traceback
            traceback.print_exc()

    def get_regions_for_current_page(self):
        """Get regions for the current page"""
        if self.template_data.get("template_type") == "multi":
            # For multi-page templates, get page-specific regions
            page_regions = self.template_data.get("page_regions", [])
            if self.current_page < len(page_regions):
                return page_regions[self.current_page]
            return {}
        else:
            # For single-page templates, return all regions
            return self.template_data.get("regions", {})

    def get_column_lines_for_current_page(self):
        """Get column lines for the current page"""
        if self.template_data.get("template_type") == "multi":
            # For multi-page templates, get page-specific column lines
            page_column_lines = self.template_data.get("page_column_lines", [])
            if self.current_page < len(page_column_lines):
                return page_column_lines[self.current_page]
            return {}
        else:
            # For single-page templates, return all column lines
            return self.template_data.get("column_lines", {})

    def get_template_data(self):
        """Get all template data from the dialog"""
        template_data = {}
        
        # Get general information
        template_data['name'] = self.name_input.text().strip()
        template_data['description'] = self.desc_input.toPlainText().strip()
        template_data['template_type'] = "multi" if self.type_combo.currentText() == "Multi-page" else "single"
        template_data['page_count'] = self.page_count
        
        print(f"\nCollecting template data for {template_data['name']} (type: {template_data['template_type']})")
        
        # Get regions data
        if template_data['template_type'] == "multi":
            # For multi-page templates, collect regions for each page
            print(f"Collecting multi-page regions for {self.page_count} pages")
            page_regions = []
            for page in range(self.page_count):
                self.current_page = page
                page_region = self.get_regions_data()
                # Log the regions collected for each page
                region_counts = {section: len(rects) for section, rects in page_region.items()}
                print(f"- Page {page+1}: collected regions = {region_counts}")
                page_regions.append(page_region)
            template_data['page_regions'] = page_regions
            
            # Also include an empty 'regions' field to satisfy older code that might expect it
            template_data['regions'] = {}
            print(f"Multi-page template: collected {len(page_regions)} page_regions")
        else:
            # For single-page templates
            regions = self.get_regions_data()
            template_data['regions'] = regions
            # Log the regions collected
            region_counts = {section: len(rects) for section, rects in regions.items()}
            print(f"Single-page template: collected regions = {region_counts}")
            
            # Initialize page_regions as an empty list to satisfy code that might look for it
            template_data['page_regions'] = []
        
        # Get column lines data
        if template_data['template_type'] == "multi":
            # For multi-page templates, collect column lines for each page
            print(f"Collecting multi-page column lines for {self.page_count} pages")
            page_column_lines = []
            for page in range(self.page_count):
                self.current_page = page
                page_column_line = self.get_column_lines_data()
                # Log the column lines collected for each page
                column_counts = {section: len(lines) for section, lines in page_column_line.items()}
                print(f"- Page {page+1}: collected column lines = {column_counts}")
                page_column_lines.append(page_column_line)
            template_data['page_column_lines'] = page_column_lines
            
            # Also include an empty 'column_lines' field to satisfy older code
            template_data['column_lines'] = {}
            print(f"Multi-page template: collected {len(page_column_lines)} page_column_lines")
        else:
            # For single-page templates
            column_lines = self.get_column_lines_data()
            template_data['column_lines'] = column_lines
            # Log the column lines collected
            column_counts = {section: len(lines) for section, lines in column_lines.items()}
            print(f"Single-page template: collected column lines = {column_counts}")
            
            # Initialize page_column_lines as an empty list to satisfy code that might look for it
            template_data['page_column_lines'] = []
        
        # Get configuration data
        template_data['config'] = self.get_config_data()
        
        # Ensure we have valid data before returning
        try:
            self.validate_template_data(template_data)
            print("Template data validation successful")
        except Exception as e:
            print(f"Template data validation failed: {str(e)}")
        
        return template_data
        
    def get_regions_data(self):
        """Extract regions data from the regions table"""
        regions = {
            'header': [],
            'items': [],
            'summary': []
        }
        
        # Iterate through all rows in the regions table
        for row in range(self.regions_table.rowCount()):
            # Get section, which should be in the first column
            section_item = self.regions_table.item(row, 0)
            if not section_item:
                continue
                
            section = section_item.text().lower()
            
            # Make sure section is valid
            if section not in regions:
                continue
                
            # Get coordinates
            try:
                x_item = self.regions_table.item(row, 2)
                y_item = self.regions_table.item(row, 3)
                width_item = self.regions_table.item(row, 4)
                height_item = self.regions_table.item(row, 5)
                
                if x_item and y_item and width_item and height_item:
                    x = int(x_item.text())
                    y = int(y_item.text())
                    width = int(width_item.text())
                    height = int(height_item.text())
                    
                    # Add to the appropriate section
                    regions[section].append({
                        'x': x,
                        'y': y,
                        'width': width,
                        'height': height
                    })
            except (ValueError, AttributeError) as e:
                print(f"Error parsing region data: {str(e)}")
                continue
        
        # If no regions were found, preserve the original regions based on template type
        if not any(regions.values()) and hasattr(self, 'template_data'):
            print("No regions found in table, preserving original regions data")
            
            # Check if this is a multi-page template
            if self.template_data.get("template_type") == "multi":
                # For multi-page templates, get page-specific regions
                page_regions = self.template_data.get("page_regions", [])
                if hasattr(self, 'current_page') and self.current_page < len(page_regions):
                    print(f"Preserving multi-page regions for page {self.current_page}")
                    return page_regions[self.current_page]
            
            # Otherwise fallback to standard regions (for single-page templates)
            if 'regions' in self.template_data:
                print("Preserving single-page regions")
            return self.template_data['regions']
            
        return regions
        
    def get_column_lines_data(self):
        """Extract column lines data from the columns table"""
        column_lines = {
            'header': [],
            'items': [],
            'summary': []
        }
        
        # Iterate through all rows in the columns table
        for row in range(self.columns_table.rowCount()):
            # Get section, which should be in the first column
            section_item = self.columns_table.item(row, 0)
            if not section_item:
                continue
                
            section = section_item.text().lower()
            
            # Make sure section is valid
            if section not in column_lines:
                continue
                
            # Get coordinates
            try:
                table_idx_item = self.columns_table.item(row, 1)
                x_pos_item = self.columns_table.item(row, 2)
                desc_item = self.columns_table.item(row, 3)
                
                if table_idx_item and x_pos_item and desc_item:
                    table_idx = int(table_idx_item.text()) - 1  # Convert to 0-based index
                    x_pos = float(x_pos_item.text())
                    
                    # Parse coordinates from description
                    desc = desc_item.text()
                    start_coords = desc.split("End:")[0].strip("Start: ()").split(",")
                    end_coords = desc.split("End:")[1].strip(" ()").split(",")
                    
                    if len(start_coords) == 2 and len(end_coords) == 2:
                        start_x = float(start_coords[0].strip())
                        start_y = float(start_coords[1].strip())
                        end_x = float(end_coords[0].strip())
                        end_y = float(end_coords[1].strip())
                        
                        # Create start and end points as dictionaries
                        start_point = {'x': start_x, 'y': start_y}
                        end_point = {'x': end_x, 'y': end_y}
                        
                        # Add to column lines with table index
                        column_lines[section].append([start_point, end_point, table_idx])
                    else:
                        print(f"Warning: Invalid coordinate format in description: {desc}")
                continue
        
            except Exception as e:
                print(f"Error processing row {row}: {str(e)}")
                continue
        
        # If no column lines were found, preserve the original ones based on template type
        if not any(column_lines.values()) and hasattr(self, 'template_data'):
            print("No column lines found in table, preserving original column lines data")
            
            # Check if this is a multi-page template
            if self.template_data.get("template_type") == "multi":
                # For multi-page templates, get page-specific column lines
                page_column_lines = self.template_data.get("page_column_lines", [])
                if hasattr(self, 'current_page') and self.current_page < len(page_column_lines):
                    print(f"Preserving multi-page column lines for page {self.current_page}")
                    return page_column_lines[self.current_page]
            
            # Otherwise fallback to standard column lines (for single-page templates)
            if 'column_lines' in self.template_data:
                print("Preserving single-page column lines")
            return self.template_data['column_lines']
            
        return column_lines

    def get_config_data(self):
        """Extract configuration data from the dialog"""
        config = {}
        
        # If we have a template_data, preserve any existing config data not overwritten
        if hasattr(self, 'template_data') and 'config' in self.template_data:
            # Start with a copy of the existing config to preserve any custom fields
            config = self.template_data['config'].copy()
        
        # Add extraction parameters to config
        extraction_params = {
            'header': {
                'row_tol': self.header_row_tol.value()
            },
            'items': {
                'row_tol': self.items_row_tol.value()
            },
            'summary': {
                'row_tol': self.summary_row_tol.value()
            },
            'split_text': self.split_text.isChecked(),
            'strip_text': self.strip_text.text().replace('\\n', '\n'),
            'flavor': 'stream'  # This is fixed
        }
        
        # Add multi-table mode
        config['multi_table_mode'] = self.multi_table_mode.isChecked()
        
        # Add extraction parameters
        config['extraction_params'] = extraction_params
        
        # Add regex patterns to config - always create the structure even if empty
        regex_patterns = {
            'header': {},
            'items': {},
            'summary': {}
        }
        
        # Add patterns for header section - even if empty
        regex_patterns['header']['start'] = self.header_start_pattern.text().strip()
        regex_patterns['header']['end'] = self.header_end_pattern.text().strip()
        regex_patterns['header']['skip'] = self.header_skip_pattern.text().strip()
        # Add patterns for items section - even if empty
        regex_patterns['items']['start'] = self.items_start_pattern.text().strip()
        regex_patterns['items']['end'] = self.items_end_pattern.text().strip()
        regex_patterns['items']['skip'] = self.items_skip_pattern.text().strip()
        # Add patterns for summary section - even if empty
        regex_patterns['summary']['start'] = self.summary_start_pattern.text().strip()
        regex_patterns['summary']['end'] = self.summary_end_pattern.text().strip()
        regex_patterns['summary']['skip'] = self.summary_skip_pattern.text().strip()
        # Always include regex_patterns in config to ensure empty patterns can be saved
        config['regex_patterns'] = regex_patterns
            # Log what patterns we're saving
        print("\nSaving regex patterns to template:")
        for section, patterns in regex_patterns.items():
            print(f"  {section}: {patterns}")
        # For multi-page templates with page-specific config
        if (self.template_data.get("template_type") == "multi" and 
            hasattr(self, 'page_specific_config') and 
            self.page_specific_config.isChecked()):
            # Create or update page_configs
            page_configs = self.template_data.get('page_configs', [None] * self.page_count)
            
            # Ensure page_configs list is long enough
            while len(page_configs) < self.page_count:
                page_configs.append(None)
            
            # Create page-specific configs for each page
            for page_idx in range(self.page_count):
                # If this is the current page, use the current values
                if page_idx == self.current_page:
                    page_config = {
                        'extraction_params': extraction_params.copy(),
                        'regex_patterns': regex_patterns.copy()
                    }
                    page_configs[page_idx] = page_config
                # Otherwise, keep existing config or initialize
                elif page_idx >= len(page_configs) or page_configs[page_idx] is None:
                    # Initialize with global config
                    page_configs[page_idx] = {
                        'extraction_params': config['extraction_params'].copy(),
                        'regex_patterns': config.get('regex_patterns', {}).copy()
                    }
            
            # Save page_configs to template_data
            config['page_configs'] = page_configs
        
        return config

    def validate_template_data(self, template_data):
        """Validate that the template data contains all required fields"""
        # Basic validation - check that all required fields exist
        required_fields = ['name', 'description', 'template_type', 'config']
        for field in required_fields:
            if field not in template_data:
                print(f"Missing required field: {field}")
                return False
        
        # Check template type and required fields based on type
        if template_data['template_type'] == 'multi':
            # For multi-page templates
            if 'page_count' not in template_data:
                print("Missing page_count field for multi-page template")
                return False
            
            if 'page_regions' not in template_data:
                print("Missing page_regions field for multi-page template")
                return False
                
            if 'page_column_lines' not in template_data:
                print("Missing page_column_lines field for multi-page template")
                return False
                
            # Validate that page_regions has entries
            if not template_data['page_regions'] or not any(template_data['page_regions']):
                print("page_regions is empty for multi-page template")
                return False
        else:
            # For single-page templates
            if 'regions' not in template_data:
                print("Missing regions field for single-page template")
                return False
                
            if 'column_lines' not in template_data:
                print("Missing column_lines field for single-page template")
                return False
                
            # Validate that regions has entries
            if not template_data['regions'] or not any(template_data['regions'].values()):
                print("regions is empty for single-page template")
                return False
                
        # Check that config contains required fields
        if not isinstance(template_data['config'], dict):
            print("Config must be a dictionary")
            return False
            
        if 'extraction_params' not in template_data['config']:
            print("Missing extraction_params in config")
            return False
            
        # Basic validation passed
        return True

    def clone_regions_to_another_page(self):
        """Clone regions from the current page to another page"""
        if self.template_data.get("template_type") != "multi" or self.page_count <= 1:
            return
            
        # Get current page regions
        current_regions = self.get_regions_for_current_page()
        if not current_regions or not any(current_regions.values()):
            QMessageBox.warning(
                self,
                "No Regions to Clone",
                "There are no regions defined on the current page to clone.",
                QMessageBox.Ok
            )
            return
            
        # Create a dialog to select the target page
        target_pages = []
        for i in range(self.page_count):
            if i != self.current_page:  # Exclude current page
                target_pages.append(f"Page {i + 1}")
                
        if not target_pages:
            QMessageBox.warning(
                self,
                "No Target Pages",
                "There are no other pages to clone regions to.",
                QMessageBox.Ok
            )
            return
            
        # Create dialog for selecting target page and options
        dialog = QDialog(self)
        dialog.setWindowTitle("Clone Regions to Another Page")
        dialog.setMinimumWidth(400)
        
        dialog_layout = QVBoxLayout()
        
        # Explanation
        explanation = QLabel("Select the page(s) to clone the current regions to:")
        explanation.setWordWrap(True)
        dialog_layout.addWidget(explanation)
        
        # Target page selection
        page_list = QListWidget()
        for page in target_pages:
            item = QListWidgetItem(page)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            page_list.addItem(item)
        dialog_layout.addWidget(page_list)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        replace_option = QCheckBox("Replace existing regions on target page(s)")
        replace_option.setChecked(True)
        options_layout.addWidget(replace_option)
        
        options_group.setLayout(options_layout)
        dialog_layout.addWidget(options_group)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dialog_layout.addWidget(buttons)
        
        dialog.setLayout(dialog_layout)
        
        # Show dialog and process result
        if dialog.exec() == QDialog.Accepted:
            # Get selected pages
            selected_pages = []
            for i in range(page_list.count()):
                item = page_list.item(i)
                if item.checkState() == Qt.Checked:
                    # Convert from display name "Page X" to 0-based index
                    page_idx = int(item.text().split(" ")[1]) - 1
                    selected_pages.append(page_idx)
            
            if not selected_pages:
                QMessageBox.warning(
                    self,
                    "No Pages Selected",
                    "No target pages were selected. The operation was cancelled.",
                    QMessageBox.Ok
                )
                return
            
            # Apply cloning to each selected page
            replace_existing = replace_option.isChecked()
            cloned_to = []
            
            # Make sure page_regions is initialized
            if 'page_regions' not in self.template_data:
                self.template_data['page_regions'] = [{}] * self.page_count
            
            # Extend page_regions if needed
            while len(self.template_data['page_regions']) < self.page_count:
                self.template_data['page_regions'].append({})
            
            for page_idx in selected_pages:
                # If replace is checked, or if the target page has no regions
                if replace_existing or not self.template_data['page_regions'][page_idx]:
                    # Create a deep copy of the current regions
                    import copy
                    self.template_data['page_regions'][page_idx] = copy.deepcopy(current_regions)
                    cloned_to.append(page_idx + 1)  # Convert to 1-based for display
                else:
                    # Merge regions (add to existing)
                    target_regions = self.template_data['page_regions'][page_idx]
                    for section, rects in current_regions.items():
                        if section not in target_regions:
                            target_regions[section] = []
                        target_regions[section].extend(copy.deepcopy(rects))
                    cloned_to.append(page_idx + 1)  # Convert to 1-based for display
            
            # Show success message
            success_message = f"Regions cloned successfully to page(s): {', '.join(map(str, cloned_to))}"
            QMessageBox.information(
                self,
                "Regions Cloned",
                success_message,
                QMessageBox.Ok
            )
            
            # If current page is one of the target pages, refresh the view
            if self.current_page in selected_pages:
                self.load_regions_for_current_page()

    def show_raw_config(self, config):
        """Show the raw configuration in a dialog for debugging"""
        try:
            import json
            config_text = json.dumps(config, indent=2)
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Raw Configuration")
            dialog.setMinimumWidth(600)
            dialog.setMinimumHeight(400)
            
            layout = QVBoxLayout(dialog)
            
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setFont(QFont("Courier New", 10))
            text_edit.setText(config_text)
            
            layout.addWidget(text_edit)
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.exec()
        except Exception as e:
            print(f"Error showing raw config: {e}")
            import traceback
            traceback.print_exc()

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
                try:
                    # Get updated data with proper error handling
                    updated_data = dialog.get_template_data()
                    
                    # Validate that we have all required data
                    if not self.validate_template_data(updated_data):
                        print("Template data validation failed, aborting update")
                        return
                        
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
                    
                    # Create a progress dialog instead of a message box
                    progress = QProgressDialog("Updating template...", None, 0, 100, self)
                    progress.setWindowTitle("Updating Template")
                    progress.setWindowModality(Qt.WindowModal)
                    progress.setMinimumDuration(0)  # Show immediately
                    progress.setValue(0)
                    progress.setAutoClose(True)
                    progress.setAutoReset(True)
                    progress.setCancelButton(None)  # No cancel button
                    progress.setFixedSize(300, 100)
                    progress.setStyleSheet("QLabel { color: black; }")
                    progress.show()
                    
                    # Process events to ensure the dialog is displayed
                    QApplication.processEvents()
                    
                    try:
                        # Update progress to show we've started
                        progress.setValue(10)
                        QApplication.processEvents()
                        
                        # Debug output
                        print(f"\nAttempting to save template: {new_name}")
                        print(f"Template regions: {len(updated_data['regions'].get('header', []))} header, {len(updated_data['regions'].get('items', []))} items, {len(updated_data['regions'].get('summary', []))} summary")
                        print(f"Config has regex_patterns: {'regex_patterns' in updated_data['config']}")
                        
                        # Update progress
                        progress.setValue(30)
                        QApplication.processEvents()
                        
                        # Check if new name exists (if changed)
                        if new_name != template["name"]:
                            # Need to delete old template and create new one with new name
                            print(f"Name changed from '{template['name']}' to '{new_name}', deleting old template")
                            self.db.delete_template(template_id=template_id)
                            
                            # Update progress
                            progress.setValue(50)
                            QApplication.processEvents()
                            
                            # Save the new template with appropriate data based on template type
                            if updated_data["template_type"] == "multi":
                                # For multi-page templates, include page-specific data
                                print("\nCreating new multi-page template with the following data:")
                                print(f"- Page count: {updated_data['page_count']}")
                                
                                # Log regions data
                                page_regions = updated_data.get("page_regions", [])
                                print(f"- Page regions: {len(page_regions)} pages")
                                for i, page_region in enumerate(page_regions):
                                    region_counts = {section: len(rects) for section, rects in page_region.items()}
                                    print(f"  - Page {i+1}: {region_counts}")
                                
                                # Log column lines data
                                page_column_lines = updated_data.get("page_column_lines", [])
                                print(f"- Page column lines: {len(page_column_lines)} pages")
                                for i, page_column_line in enumerate(page_column_lines):
                                    column_counts = {section: len(lines) for section, lines in page_column_line.items()}
                                    print(f"  - Page {i+1}: {column_counts}")
                                
                                # Create template with page-specific data
                                new_id = self.db.save_template(
                                    name=new_name,
                                    description=new_description,
                                    regions=updated_data["regions"],
                                    column_lines=updated_data["column_lines"],
                                    config=updated_data["config"],
                                    template_type=updated_data["template_type"],
                                    page_count=updated_data["page_count"],
                                    page_regions=updated_data.get("page_regions", []),
                                    page_column_lines=updated_data.get("page_column_lines", []),
                                    page_configs=updated_data["config"].get("page_configs", [])
                                )
                            else:
                                # For single-page templates, use the standard fields
                                print("\nCreating new single-page template with the following data:")
                                region_counts = {section: len(rects) for section, rects in updated_data["regions"].items()}
                                print(f"- Regions: {region_counts}")
                                column_counts = {section: len(lines) for section, lines in updated_data["column_lines"].items()}
                                print(f"- Column lines: {column_counts}")
                                
                            new_id = self.db.save_template(
                                name=new_name,
                                description=new_description,
                                regions=updated_data["regions"],
                                column_lines=updated_data["column_lines"],
                                config=updated_data["config"],
                                template_type=updated_data["template_type"]
                            )
                            print(f"Created new template with ID: {new_id}")
                        else:
                            # Just update the template data
                            print(f"Updating existing template with ID: {template_id}")
                            
                            # Update progress
                            progress.setValue(50)
                            QApplication.processEvents()
                            
                            # Update the template with appropriate data based on template type
                            if updated_data["template_type"] == "multi":
                                # For multi-page templates, include page-specific data
                                self.db.save_template(
                                    name=new_name,
                                    description=new_description,
                                    regions=updated_data["regions"],
                                    column_lines=updated_data["column_lines"],
                                    config=updated_data["config"],
                                    template_type=updated_data["template_type"],
                                    page_count=updated_data["page_count"],
                                    page_regions=updated_data.get("page_regions", []),
                                    page_column_lines=updated_data.get("page_column_lines", []),
                                    page_configs=updated_data["config"].get("page_configs", [])
                                )
                            else:
                                # For single-page templates, use the standard fields
                                self.db.save_template(
                                name=new_name,
                                description=new_description,
                                regions=updated_data["regions"],
                                column_lines=updated_data["column_lines"],
                                config=updated_data["config"],
                                template_type=updated_data["template_type"]
                            )
                        
                        # Update progress to completion
                        progress.setValue(100)
                        QApplication.processEvents()
                        
                        # Make sure dialog is closed
                        progress.close()
                        QApplication.processEvents()
                        
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
"""

                        # Add regions information based on template type
                        success_message += "<p><b>Regions:</b></p><ul>"
                        if updated_data["template_type"] == "multi":
                            # For multi-page templates, show page-specific regions
                            page_regions = updated_data.get("page_regions", [])
                            for page_idx, page_region in enumerate(page_regions):
                                success_message += f"<li><b>Page {page_idx + 1}:</b><ul>"
                                for section, rects in page_region.items():
                                    success_message += f"<li>{section.title()}: {len(rects)} table(s)</li>"
                                success_message += "</ul></li>"
                        else:
                            # For single-page templates, use the regular regions
                            for section, rects in updated_data["regions"].items():
                                success_message += f"<li>{section.title()}: {len(rects)} table(s)</li>"
                        success_message += "</ul>"
                        
                        # Add column lines information based on template type
                        success_message += "<p><b>Column Lines:</b></p><ul>"
                        if updated_data["template_type"] == "multi":
                            # For multi-page templates, show page-specific column lines
                            page_column_lines = updated_data.get("page_column_lines", [])
                            for page_idx, page_column_line in enumerate(page_column_lines):
                                success_message += f"<li><b>Page {page_idx + 1}:</b><ul>"
                                for section, lines in page_column_line.items():
                                    success_message += f"<li>{section.title()}: {len(lines)} line(s)</li>"
                                success_message += "</ul></li>"
                        else:
                            # For single-page templates, use the regular column lines
                            for section, lines in updated_data["column_lines"].items():
                                success_message += f"<li>{section.title()}: {len(lines)} line(s)</li>"
                            success_message += "</ul>"
                        
                        # Add regex pattern information if available
                        if 'regex_patterns' in updated_data['config']:
                            success_message += "<p><b>Regex Patterns:</b></p><ul>"
                            for section, patterns in updated_data['config']['regex_patterns'].items():
                                pattern_list = []
                                for pattern_type, pattern in patterns.items():
                                    if pattern:
                                        pattern_list.append(f"{pattern_type}: '{pattern}'")
                                if pattern_list:
                                    success_message += f"<li>{section.title()}: {', '.join(pattern_list)}</li>"
                            success_message += "</ul>"
                        
                        success_msg = QMessageBox(self)
                        success_msg.setWindowTitle("Template Updated")
                        success_msg.setText("Template Updated")
                        success_msg.setInformativeText(success_message)
                        success_msg.setIcon(QMessageBox.Information)
                        success_msg.setStyleSheet("QLabel { color: black; }")
                        success_msg.exec()
                        
                        # Refresh the template list
                        self.load_templates()
                    
                    except sqlite3.Error as db_e:
                        # Handle database-specific errors
                        progress.close()
                        QApplication.processEvents()
                        
                        error_message = f"""
<h3>Database Error</h3>
<p>A database error occurred while trying to save the template:</p>
<p style='color: #D32F2F;'>{str(db_e)}</p>
<p>This might be due to database corruption, permissions issues, or disk space limitations.</p>
"""
                        error_dialog = QMessageBox(self)
                        error_dialog.setWindowTitle("Database Error")
                        error_dialog.setText("Error Saving Template")
                        error_dialog.setInformativeText(error_message)
                        error_dialog.setIcon(QMessageBox.Critical)
                        error_dialog.setStyleSheet("QLabel { color: black; }")
                        error_dialog.exec()
                        
                        print(f"Database error in edit_template: {str(db_e)}")
                        import traceback
                        traceback.print_exc()
                    
                    except Exception as inner_e:
                        # Close the progress dialog for any other error
                        progress.close()
                        QApplication.processEvents()
                        
                        error_message = f"""
<h3>Error Saving Template</h3>
<p>An error occurred while saving the template:</p>
<p style='color: #D32F2F;'>{str(inner_e)}</p>
<p>The template may not have been updated properly.</p>
"""
                        error_dialog = QMessageBox(self)
                        error_dialog.setWindowTitle("Save Error")
                        error_dialog.setText("Error Saving Template")
                        error_dialog.setInformativeText(error_message)
                        error_dialog.setIcon(QMessageBox.Critical)
                        error_dialog.setStyleSheet("QLabel { color: black; }")
                        error_dialog.exec()
                        
                        print(f"Error in edit_template save operation: {str(inner_e)}")
                        import traceback
                        traceback.print_exc()
                    
                    finally:
                        # Make sure progress dialog is closed in all cases
                        try:
                            progress.close()
                            QApplication.processEvents()
                        except Exception as close_e:
                            print(f"Error closing progress dialog: {str(close_e)}")
                
                except AttributeError as attr_e:
                    error_message = f"""
<h3>Template Update Error</h3>
<p>There was a problem accessing template data:</p>
<p style='color: #D32F2F;'>{str(attr_e)}</p>
<p>This could be due to missing or corrupted template information.</p>
"""
                    error_dialog = QMessageBox(self)
                    error_dialog.setWindowTitle("Error")
                    error_dialog.setText("Error Updating Template")
                    error_dialog.setInformativeText(error_message)
                    error_dialog.setIcon(QMessageBox.Critical)
                    error_dialog.setStyleSheet("QLabel { color: black; }")
                    error_dialog.exec()
                    
                    print(f"AttributeError in edit_template: {str(attr_e)}")
                    import traceback
                    traceback.print_exc()
                
                except ValueError as val_e:
                    error_message = f"""
<h3>Template Value Error</h3>
<p>There was a problem with the template data values:</p>
<p style='color: #D32F2F;'>{str(val_e)}</p>
<p>Please check that all fields contain valid information.</p>
"""
                    error_dialog = QMessageBox(self)
                    error_dialog.setWindowTitle("Error")
                    error_dialog.setText("Error Updating Template")
                    error_dialog.setInformativeText(error_message)
                    error_dialog.setIcon(QMessageBox.Critical)
                    error_dialog.setStyleSheet("QLabel { color: black; }")
                    error_dialog.exec()
                    
                    print(f"ValueError in edit_template: {str(val_e)}")
                    import traceback
                    traceback.print_exc()
        
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
            print(f"Error in edit_template: {str(e)}")
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
            
            # Type with page count for multi-page templates
            if template["template_type"] == "multi":
                page_count = template.get("page_count", 1)
                type_text = f"Multi-page ({page_count} pages)"
            else:
                type_text = "Single-page"
            
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
<p><b>Type:</b> {"Multi-page" if template.get('template_type') == 'multi' else "Single-page"}</p>
"""

            if template.get('template_type') == 'multi':
                template_preview += f"<p><b>Number of Pages:</b> {template.get('page_count', 1)}</p>"
                
                # For multi-page templates, show info for each page
                template_preview += "<p><b>Pages:</b></p><ul>"
                
                # Get page-specific data if available
                page_regions = template.get('page_regions', [])
                page_column_lines = template.get('page_column_lines', [])
                
                for page_idx in range(template.get('page_count', 1)):
                    template_preview += f"<li><b>Page {page_idx + 1}:</b><ul>"
                    
                    # Regions for this page
                    if page_idx < len(page_regions):
                        regions = page_regions[page_idx]
                        region_count = sum(len(rects) for rects in regions.values())
                        template_preview += f"<li>Regions: {region_count}</li>"
                        
                        # Add details about regions
                        if regions:
                            template_preview += "<ul>"
                            for section, rects in regions.items():
                                if rects:
                                    template_preview += f"<li>{section.title()}: {len(rects)} table(s)</li>"
                            template_preview += "</ul>"
                    
                    # Column lines for this page
                    if page_idx < len(page_column_lines):
                        column_lines = page_column_lines[page_idx]
                        column_line_count = sum(len(lines) for lines in column_lines.values())
                        template_preview += f"<li>Column Lines: {column_line_count}</li>"
                    
                    template_preview += "</ul></li>"
                
                template_preview += "</ul>"
            else:
                # Show information for single-page template
                region_count = 0
                if 'regions' in template and template['regions']:
                    template_preview += "<p><b>Tables:</b></p><ul>"
                    for section, rects in template['regions'].items():
                        if rects:
                            region_count += len(rects)
                            template_preview += f"<li>{section.title()}: {len(rects)} table(s)</li>"
                    template_preview += f"</ul><p><b>Total Regions:</b> {region_count}</p>"
                
                # Column lines info
                template_preview += f"<p><b>Column Lines:</b> {'Yes' if 'column_lines' in template and any(template['column_lines'].values()) else 'No'}</p>"
            
            # Show configuration info
            template_preview += f"<p><b>Multi-table Mode:</b> {'Yes' if template.get('config', {}).get('multi_table_mode', False) else 'No'}</p>"
            
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
                # Clear the existing PDF in pdf_processor if it exists
                if self.pdf_processor and hasattr(self.pdf_processor, 'clear_all'):
                    print("Clearing existing PDF and regions before applying template")
                    self.pdf_processor.clear_all()
                
                # Helper function to convert coordinates from database format to PDF format
                def convert_coordinates(rect_data, pdf_height=None):
                    """
                    Convert coordinates from database format (x1,y1,x2,y2 bottom-left origin) 
                    to PDF format (x,y,width,height top-left origin)
                    
                    If pdf_height is provided, converts from bottom-left to top-left origin
                    """
                    if isinstance(rect_data, dict):
                        if 'x1' in rect_data and 'y1' in rect_data and 'x2' in rect_data and 'y2' in rect_data:
                            # Get coordinates from database format
                            x1 = float(rect_data['x1'])
                            y1 = float(rect_data['y1'])
                            x2 = float(rect_data['x2'])
                            y2 = float(rect_data['y2'])
                            
                            # Calculate width and height
                            width = x2 - x1
                            height = y2 - y1
                            
                            # If pdf_height is provided, convert from bottom-left to top-left origin
                            if pdf_height is not None:
                                # Flip y-coordinates (subtract from pdf_height)
                                # Note: This depends on the exact coordinate system used in your database
                                # For a standard PDF, (0,0) is usually bottom-left, but for display we need top-left
                                new_y1 = pdf_height - y2  # Convert bottom-left to top-left
                                return QRect(int(x1), int(new_y1), int(width), int(height))
                            else:
                                # For cases where we don't have the PDF height yet
                                return QRect(int(x1), int(y1), int(width), int(height))
                        elif 'x' in rect_data and 'y' in rect_data and 'width' in rect_data and 'height' in rect_data:
                            # Already in the right format
                            x = int(rect_data['x'])
                            y = int(rect_data['y'])
                            width = int(rect_data['width'])
                            height = int(rect_data['height'])
                            
                            if pdf_height is not None and template.get('uses_bottom_left', True):
                                # Flip y-coordinate if needed
                                y = pdf_height - y - height
                            
                            return QRect(x, y, width, height)
                        else:
                            print(f"Warning: Unknown rect format in template: {rect_data}")
                            return QRect()
                    elif isinstance(rect_data, QRect):
                        # Already a QRect, but might still need coordinate conversion
                        if pdf_height is not None and template.get('uses_bottom_left', True):
                            x = rect_data.x()
                            y = pdf_height - rect_data.y() - rect_data.height()
                            return QRect(x, y, rect_data.width(), rect_data.height())
                        return rect_data
                    else:
                        print(f"Warning: Unknown rect type in template: {type(rect_data)}")
                        return QRect()
                
                # Get PDF dimensions if available
                pdf_height = None
                if self.pdf_processor and hasattr(self.pdf_processor, 'pdf_label') and self.pdf_processor.pdf_label.pixmap():
                    pdf_height = self.pdf_processor.pdf_label.pixmap().height()
                    print(f"Using PDF height for coordinate conversion: {pdf_height}")
                else:
                    print("Warning: Could not determine PDF height, using raw coordinates")
                
                # For single-page templates
                if template.get('template_type') == 'single':
                    # Convert serialized regions to QRect objects with coordinate conversion
                    if 'regions' in template and template['regions']:
                        converted_regions = {}
                        for section, rects in template['regions'].items():
                            converted_regions[section] = []
                            for rect_data in rects:
                                converted_rect = convert_coordinates(rect_data, pdf_height)
                                converted_regions[section].append(converted_rect)
                                print(f"Converted region: {rect_data} -> {converted_rect}")
                        
                        template['regions'] = converted_regions
                    
                    # Convert serialized column lines
                    if 'column_lines' in template and template['column_lines']:
                        converted_column_lines = {}
                        for section, lines in template['column_lines'].items():
                            converted_column_lines[section] = []
                            for line_data in lines:
                                if isinstance(line_data, list) or isinstance(line_data, tuple):
                                    if len(line_data) == 2:
                                        start_point = line_data[0]
                                        end_point = line_data[1]
                                        
                                        # Convert dictionary to QPoint if needed
                                        if isinstance(start_point, dict) and 'x' in start_point and 'y' in start_point:
                                            x = int(start_point['x'])
                                            y = int(start_point['y'])
                                            if pdf_height is not None and template.get('uses_bottom_left', True):
                                                y = pdf_height - y  # Convert to top-left origin
                                            start_point = QPoint(x, y)
                                            
                                        if isinstance(end_point, dict) and 'x' in end_point and 'y' in end_point:
                                            x = int(end_point['x'])
                                            y = int(end_point['y'])
                                            if pdf_height is not None and template.get('uses_bottom_left', True):
                                                y = pdf_height - y  # Convert to top-left origin
                                            end_point = QPoint(x, y)
                                            
                                        converted_column_lines[section].append([start_point, end_point])
                                    elif len(line_data) == 3:
                                        start_point = line_data[0]
                                        end_point = line_data[1]
                                        rect_index = line_data[2]
                                        
                                        # Convert dictionary to QPoint if needed
                                        if isinstance(start_point, dict) and 'x' in start_point and 'y' in start_point:
                                            x = int(start_point['x'])
                                            y = int(start_point['y'])
                                            if pdf_height is not None and template.get('uses_bottom_left', True):
                                                y = pdf_height - y  # Convert to top-left origin
                                            start_point = QPoint(x, y)
                                            
                                        if isinstance(end_point, dict) and 'x' in end_point and 'y' in end_point:
                                            x = int(end_point['x'])
                                            y = int(end_point['y'])
                                            if pdf_height is not None and template.get('uses_bottom_left', True):
                                                y = pdf_height - y  # Convert to top-left origin
                                            end_point = QPoint(x, y)
                                            
                                        converted_column_lines[section].append([start_point, end_point, rect_index])
                                else:
                                    # Unknown format, log error and continue
                                    print(f"Warning: Unknown column line format in template: {line_data}")
                    
                        template['column_lines'] = converted_column_lines
                
                # For multi-page templates
                else:
                    # Process page regions with coordinate conversion
                    if 'page_regions' in template and template['page_regions']:
                        converted_page_regions = []
                        for page_regions in template['page_regions']:
                            converted_regions = {}
                            for section, rects in page_regions.items():
                                converted_regions[section] = []
                                for rect_data in rects:
                                    converted_rect = convert_coordinates(rect_data, pdf_height)
                                    converted_regions[section].append(converted_rect)
                                    print(f"Converted multi-page region: {rect_data} -> {converted_rect}")
                            converted_page_regions.append(converted_regions)
                        template['page_regions'] = converted_page_regions
                    
                    # Process page column lines with coordinate conversion
                    if 'page_column_lines' in template and template['page_column_lines']:
                        converted_page_column_lines = []
                        for page_column_lines in template['page_column_lines']:
                            converted_column_lines = {}
                            for section, lines in page_column_lines.items():
                                converted_column_lines[section] = []
                                for line_data in lines:
                                    if isinstance(line_data, list) or isinstance(line_data, tuple):
                                        if len(line_data) == 2:
                                            start_point = line_data[0]
                                            end_point = line_data[1]
                                            
                                            # Convert dictionary to QPoint if needed
                                            if isinstance(start_point, dict) and 'x' in start_point and 'y' in start_point:
                                                x = int(start_point['x'])
                                                y = int(start_point['y'])
                                                if pdf_height is not None and template.get('uses_bottom_left', True):
                                                    y = pdf_height - y  # Convert to top-left origin
                                                start_point = QPoint(x, y)
                                                
                                            if isinstance(end_point, dict) and 'x' in end_point and 'y' in end_point:
                                                x = int(end_point['x'])
                                                y = int(end_point['y'])
                                                if pdf_height is not None and template.get('uses_bottom_left', True):
                                                    y = pdf_height - y  # Convert to top-left origin
                                                end_point = QPoint(x, y)
                                                
                                            converted_column_lines[section].append([start_point, end_point])
                                        elif len(line_data) == 3:
                                            start_point = line_data[0]
                                            end_point = line_data[1]
                                            rect_index = line_data[2]
                                            
                                            # Convert dictionary to QPoint if needed
                                            if isinstance(start_point, dict) and 'x' in start_point and 'y' in start_point:
                                                x = int(start_point['x'])
                                                y = int(start_point['y'])
                                                if pdf_height is not None and template.get('uses_bottom_left', True):
                                                    y = pdf_height - y  # Convert to top-left origin
                                                start_point = QPoint(x, y)
                                                
                                            if isinstance(end_point, dict) and 'x' in end_point and 'y' in end_point:
                                                x = int(end_point['x'])
                                                y = int(end_point['y'])
                                                if pdf_height is not None and template.get('uses_bottom_left', True):
                                                    y = pdf_height - y  # Convert to top-left origin
                                                end_point = QPoint(x, y)
                                            
                                            converted_column_lines[section].append([start_point, end_point, rect_index])
                                    else:
                                        # Unknown format, log error and continue
                                        print(f"Warning: Unknown column line format in multi-page template: {line_data}")
                            converted_page_column_lines.append(converted_column_lines)
                        template['page_column_lines'] = converted_page_column_lines
                
                # Set multi-table mode in PDF processor based on the template configuration
                if self.pdf_processor and hasattr(self.pdf_processor, 'multi_table_mode'):
                    multi_table_mode = template.get('config', {}).get('multi_table_mode', False)
                    self.pdf_processor.multi_table_mode = multi_table_mode
                    print(f"Setting multi-table mode to {multi_table_mode} based on template config")
                
                # Set up table_areas dictionary in the pdf_processor for structured storage
                if self.pdf_processor:
                    template_type = template.get('template_type', 'single')
                    if template_type == 'single' and 'regions' in template:
                        self.pdf_processor.table_areas = {}
                        
                        # Build table_areas for each section
                        for section, rects in template['regions'].items():
                            for i, rect in enumerate(rects):
                                table_label = f"{section}_table_{i+1}"
                                
                                # Get columns for this table
                                columns = []
                                if 'column_lines' in template and section in template['column_lines']:
                                    for line_data in template['column_lines'][section]:
                                        if len(line_data) >= 2:
                                            if len(line_data) == 2 or (len(line_data) == 3 and line_data[2] == i):
                                                # This line belongs to the current table
                                                columns.append(line_data[0].x())
                                
                                # Create the table area entry
                                self.pdf_processor.table_areas[table_label] = {
                                    'type': section,
                                    'index': i,
                                    'rect': rect,
                                    'columns': sorted(columns) if columns else []
                                }
                                print(f"Created table_area: {table_label} with {len(columns)} columns")
                    
                    # For multi-page templates, table_areas will be set up when pages are displayed
                
                # Add debugging information
                print("\n[DEBUG] Template data that will be applied:")
                if template.get('template_type') == 'single':
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
                else:
                    print(f"Multi-page template with {template.get('page_count', 1)} pages")
                    for page_idx, page_regions in enumerate(template.get('page_regions', [])):
                        print(f"Page {page_idx + 1} regions:")
                        for section, rects in page_regions.items():
                            print(f"  Section: {section} - {len(rects)} regions")
                            for i, rect in enumerate(rects):
                                print(f"    Region {i}: x={rect.x()}, y={rect.y()}, width={rect.width()}, height={rect.height()}")
                
                # Emit the template selection signal with the template data
                # The PDFProcessor will receive this data and apply it to the PDF
                # The PDFLabel will handle the scaling when drawing the regions
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

    # Add this method to the TemplateManager class
    def validate_template_data(self, template_data):
        """Validate template data before saving to database"""
        if not template_data:
            raise ValueError("Template data is empty")
        
        # Check basic fields that are always required
        required_fields = ['name', 'template_type']
        for field in required_fields:
            if field not in template_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Check type-specific required fields
        if template_data['template_type'] == 'multi':
            # For multi-page templates
            if 'page_count' not in template_data or not template_data['page_count']:
                raise ValueError("Multi-page templates must have a page count")
            
            if 'page_regions' not in template_data or not template_data['page_regions']:
                raise ValueError("Multi-page templates must have page regions defined")
        else:
            # For single-page templates
            if 'regions' not in template_data:
                raise ValueError("Single-page templates must have regions defined")
            
            # Validate regions data
            if not template_data['regions']:
                raise ValueError("No regions defined in template")
        
        return True