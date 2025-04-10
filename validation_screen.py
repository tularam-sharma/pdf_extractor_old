from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit,
    QGroupBox, QSplitter, QFrame, QScrollArea, QCheckBox,
    QMessageBox, QFileDialog, QTextEdit, QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon
import pandas as pd
import json
import os
import re

class ValidationScreen(QWidget):
    # Define signals
    back_requested = Signal()  # Signal for navigating back to main dashboard
    
    def __init__(self, parent=None, is_rules_manager=False):
        super().__init__(parent)
        self.parent = parent
        self.data = None
        self.json_data = None  # Store original JSON data
        self.validation_rules = {}
        self.modified_data = None
        self.is_rules_manager = is_rules_manager  # Flag to indicate if used as rules manager
        self.rules_file_path = os.path.join(os.path.dirname(__file__), "validation_rules.json")
        self.initializing = True  # Flag to indicate initialization phase
        
        # Define AI theme colors
        self.theme = {
            "primary": "#6366F1",       # Indigo
            "primary_dark": "#4F46E5",  # Darker indigo
            "secondary": "#10B981",     # Emerald
            "tertiary": "#8B5CF6",      # Violet
            "danger": "#EF4444",        # Red
            "warning": "#F59E0B",       # Amber
            "light": "#F9FAFB",         # Light gray
            "dark": "#111827",          # Dark gray
            "bg": "#F3F4F6",            # Background light gray
            "text": "#1F2937",          # Text dark
            "border": "#E5E7EB",        # Border light gray
        }
        
        self.init_ui()
        
        # Load saved rules if this is the rules manager
        if self.is_rules_manager:
            self.load_rules(silent=True)
            self.set_sample_data()
            
        self.initializing = False  # Initialization complete
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)  # Reduced spacing
        layout.setContentsMargins(24, 12, 24, 24)  # Reduced top margin
        
        # Apply global stylesheet
        self.setStyleSheet(f"""
            QWidget {{
                background-color: #F3F4F6;
            }}
            QLabel {{
                color: {self.theme['dark']};
                background-color: transparent;
            }}
            QTableWidget {{
                color: {self.theme['dark']};
                background-color: white;
                gridline-color: {self.theme['border']};
            }}
            QTableWidget::item {{
                color: {self.theme['dark']};
                background-color: white;
                border-bottom: 1px solid {self.theme['border']};
                padding: 4px;
            }}
            QHeaderView::section {{
                color: {self.theme['dark']};
                background-color: {self.theme['light']};
                border: 1px solid {self.theme['border']};
                padding: 6px;
                font-weight: bold;
                text-align: center;
            }}
            QComboBox {{
                color: {self.theme['dark']};
                background-color: white;
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QComboBox::drop-down {{
                border: 0px;
            }}
            QComboBox::down-arrow {{
                image: url(dropdown.png);
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                color: {self.theme['dark']};
                background-color: white;
                selection-background-color: {self.theme['primary']};
                selection-color: white;
            }}
            QTextEdit {{
                color: {self.theme['dark']};
                background-color: white;
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
            }}
            QLineEdit {{
                color: {self.theme['dark']};
                background-color: white;
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QGroupBox {{
                color: {self.theme['dark']};
                background-color: white;
                border-radius: 8px;
                margin-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 5px;
                color: {self.theme['dark']};
                background-color: white;
            }}
            QTreeWidget {{
                color: {self.theme['dark']};
                background-color: white;
                alternate-background-color: {self.theme['light']};
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
            }}
            QTreeWidget::item {{
                color: {self.theme['dark']};
                border-bottom: 1px solid {self.theme['border']};
                padding: 4px;
            }}
            QTreeWidget::item:selected {{
                background-color: {self.theme['primary']};
                color: white;
            }}
            QPushButton {{
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
        """)
        
        # Add title if this is rules manager
        if self.is_rules_manager:
            # Create a compact header
            header_layout = QHBoxLayout()
            header_layout.setSpacing(8)
            
            title_label = QLabel("Rules Management")
            title_label.setFont(QFont("Arial", 14, QFont.Bold))  # Reduced font size
            title_label.setStyleSheet(f"color: {self.theme['primary']}; font-weight: bold; background-color: transparent;")
            
            header_layout.addWidget(title_label)
            header_layout.addStretch(1)  # Push title to the left
            
            # Add header to layout with fixed height
            header_widget = QWidget()
            header_widget.setLayout(header_layout)
            header_widget.setFixedHeight(40)  # Fixed compact height
            header_widget.setStyleSheet("background-color: transparent;")
            layout.addWidget(header_widget)
            
            # Add a separator line
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            separator.setStyleSheet(f"background-color: {self.theme['border']};")
            separator.setMaximumHeight(1)
            layout.addWidget(separator)

        # Create a horizontal splitter to divide the screen left/right
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setHandleWidth(1)
        main_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {self.theme['border']};
            }}
        """)
        
        # LEFT SECTION - Validation Rules
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(16)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Rules Group
        rules_group = QGroupBox("Validation Rules")
        rules_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: white;
                border-radius: 8px;
                border: 1px solid {self.theme['border']};
                padding: 16px;
                font-weight: bold;
                color: {self.theme['dark']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 5px 0 5px;
                color: {self.theme['dark']};
                background-color: white;
            }}
        """)
        rules_layout = QVBoxLayout(rules_group)
        
        # Field Selection
        field_layout = QHBoxLayout()
        field_label = QLabel("JSON Path:")
        field_label.setStyleSheet(f"color: {self.theme['text']};")
        self.field_combo = QComboBox()
        self.field_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 5px;
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
                background-color: white;
                color: {self.theme['text']};
            }}
        """)
        self.field_combo.setEditable(True)  # Allow manual editing for template paths
        field_layout.addWidget(field_label)
        field_layout.addWidget(self.field_combo)
        
        # Add help button for path templates
        path_help_btn = QPushButton("?")
        path_help_btn.setFixedSize(24, 24)
        path_help_btn.setToolTip("Learn about path templates and wildcards")
        path_help_btn.clicked.connect(self.show_path_help)
        path_help_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['tertiary']};
                color: white;
                border-radius: 12px;
                font-weight: bold;
            }}
        """)
        field_layout.addWidget(path_help_btn)
        
        rules_layout.addLayout(field_layout)
        
        # Rule Type Selection
        rule_type_layout = QHBoxLayout()
        rule_type_label = QLabel("Rule Type:")
        rule_type_label.setStyleSheet(f"color: {self.theme['text']};")
        self.rule_type_combo = QComboBox()
        self.rule_type_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 5px;
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
                background-color: white;
                color: {self.theme['text']};
            }}
        """)
        self.rule_type_combo.addItems([
            "Required",
            "Numeric",
            "Date",
            "Email",
            "Custom Regex",
            "Row Total",
            "Column Total",
            "Merge Row",
            "Invoice Item Type",
            "Table Start Pattern",
            "Table End Pattern",
            "Skip Line Pattern"
        ])
        rule_type_layout.addWidget(rule_type_label)
        rule_type_layout.addWidget(self.rule_type_combo)
        rules_layout.addLayout(rule_type_layout)
        
        # Rule Parameters
        params_label = QLabel("Parameters:")
        params_label.setStyleSheet(f"color: {self.theme['text']};")
        rules_layout.addWidget(params_label)
        
        self.rule_params = QTextEdit()
        self.rule_params.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
                background-color: white;
                color: {self.theme['text']};
                padding: 5px;
            }}
        """)
        self.rule_params.setPlaceholderText("Enter rule parameters (e.g., regex pattern, column names for totals)")
        self.rule_params.setMaximumHeight(100)
        rules_layout.addWidget(self.rule_params)
        
        # Add Rule Button
        add_rule_btn = QPushButton("Add Rule")
        add_rule_btn.clicked.connect(self.add_validation_rule)
        add_rule_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['primary']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme['primary_dark']};
            }}
        """)
        
        # Add a delete rule button
        delete_rule_btn = QPushButton("Delete Selected Rule")
        delete_rule_btn.clicked.connect(self.delete_selected_rule)
        delete_rule_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['danger']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #DC2626;
            }}
        """)
        
        # Create a horizontal layout for the buttons
        rule_buttons_layout = QHBoxLayout()
        rule_buttons_layout.addWidget(add_rule_btn)
        rule_buttons_layout.addWidget(delete_rule_btn)
        rules_layout.addLayout(rule_buttons_layout)
        
        # Rules List
        self.rules_list = QTableWidget()
        self.rules_list.setColumnCount(3)
        self.rules_list.setHorizontalHeaderLabels(["Field", "Rule Type", "Parameters"])
        self.rules_list.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                background-color: white;
                color: {self.theme['dark']};
                gridline-color: {self.theme['border']};
            }}
            QTableWidget::item {{
                color: {self.theme['dark']};
                padding: 4px;
                border-bottom: 1px solid {self.theme['border']};
            }}
            QHeaderView::section {{
                background-color: {self.theme['light']};
                color: {self.theme['dark']};
                border: 1px solid {self.theme['border']};
                padding: 6px;
                font-weight: bold;
                text-align: center;
            }}
        """)
        # Set columns to stretch
        self.rules_list.horizontalHeader().setStretchLastSection(True)
        self.rules_list.verticalHeader().setDefaultSectionSize(30)  # Set row height
        self.rules_list.setShowGrid(True)
        self.rules_list.setAlternatingRowColors(True)
        self.rules_list.setSelectionBehavior(QTableWidget.SelectRows)  # Select entire rows
        self.rules_list.setSelectionMode(QTableWidget.SingleSelection)  # Allow single selection
        rules_layout.addWidget(self.rules_list)
        
        # Add the template selection section after validation actions
        # Create a separate widget for template selection
        self.template_selection_widget = QWidget()
        template_layout = QVBoxLayout(self.template_selection_widget)
        template_layout.setContentsMargins(0, 8, 0, 8)
        
        # Template group title
        template_title = QLabel("Template Selection")
        template_title.setFont(QFont("Arial", 12, QFont.Bold))
        template_title.setStyleSheet(f"color: {self.theme['dark']}; margin-bottom: 6px;")
        template_layout.addWidget(template_title)
        
        # Template selector
        template_selector_layout = QHBoxLayout()
        template_label = QLabel("Select Template:")
        template_label.setStyleSheet(f"color: {self.theme['text']};")
        
        self.template_combo = QComboBox()
        self.template_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 5px;
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
                background-color: white;
                color: {self.theme['text']};
            }}
        """)
        
        # Refresh templates button
        refresh_btn = QPushButton("⟳")
        refresh_btn.setFixedSize(60, 30)
        refresh_btn.setToolTip("Refresh template list")
        refresh_btn.clicked.connect(self.load_templates)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['secondary']};
                color: white;
                border-radius: 4px;
                font-weight: bold;
                left: 10px;
            }}
        """)
        
        template_selector_layout.addWidget(template_label)
        template_selector_layout.addWidget(self.template_combo, 1)  # Give combo box more space
        template_selector_layout.addWidget(refresh_btn)
        template_layout.addLayout(template_selector_layout)
        
        # # Save to template button
        # save_to_template_btn = QPushButton("Save Rules to Selected Template")
        # save_to_template_btn.clicked.connect(self.save_rules_to_template)
        # save_to_template_btn.setStyleSheet(f"""
        #     QPushButton {{
        #         background-color: {self.theme['primary']};
        #         color: white;
        #         padding: 8px 16px;
        #         border-radius: 6px;
        #         font-weight: bold;
        #         margin-top: 8px;
        #     }}
        #     QPushButton:hover {{
        #         background-color: {self.theme['primary_dark']};
        #     }}
        # """)
        # template_layout.addWidget(save_to_template_btn)
        
        # # Load from template button
        # load_from_template_btn = QPushButton("Load Rules from Selected Template")
        # load_from_template_btn.clicked.connect(self.load_rules_from_template)
        # load_from_template_btn.setStyleSheet(f"""
        #     QPushButton {{
        #         background-color: {self.theme['tertiary']};
        #         color: white;
        #         padding: 8px 16px;
        #         border-radius: 6px;
        #         font-weight: bold;
        #         margin-top: 8px;
        #     }}
        #     QPushButton:hover {{
        #         background-color: #7C3AED;
        #     }}
        # """)
        # template_layout.addWidget(load_from_template_btn)
        
        # Add a divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet(f"background-color: {self.theme['border']}; margin-top: 12px; margin-bottom: 12px;")
        template_layout.addWidget(divider)
        
        # Always show template selection section regardless of parent
        left_layout.addWidget(self.template_selection_widget)
        self.load_templates()  # Load available templates
        
        left_layout.addWidget(rules_group)
        
        # Validation Actions
        actions_layout = QHBoxLayout()
        
        validate_btn = QPushButton("Validate Data")
        validate_btn.clicked.connect(self.validate_data)
        validate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['secondary']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #0D9B6C;
            }}
        """)
        
        clear_rules_btn = QPushButton("Clear Rules")
        clear_rules_btn.clicked.connect(self.clear_rules)
        clear_rules_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['danger']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #DC2626;
            }}
        """)
        
        actions_layout.addWidget(validate_btn)
        actions_layout.addWidget(clear_rules_btn)
        left_layout.addLayout(actions_layout)
        
        # Add Save/Load Rules buttons
        rules_actions_layout = QHBoxLayout()
        
        save_rules_btn = QPushButton("Save Rules")
        save_rules_btn.clicked.connect(self.save_rules)
        save_rules_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['tertiary']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #7C3AED;
            }}
        """)
        
        load_rules_btn = QPushButton("Load Rules")
        load_rules_btn.clicked.connect(self.load_rules)
        load_rules_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['dark']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #0F172A;
            }}
        """)
        
        rules_actions_layout.addWidget(save_rules_btn)
        rules_actions_layout.addWidget(load_rules_btn)
        left_layout.addLayout(rules_actions_layout)
        
        # Add left widget to splitter
        main_splitter.addWidget(left_widget)
        
        # RIGHT SECTION - Data Review
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(16)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Test Data Import Section
        test_data_group = QGroupBox("Test Data")
        test_data_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: white;
                border-radius: 8px;
                border: 1px solid {self.theme['border']};
                padding: 16px;
                font-weight: bold;
                color: {self.theme['dark']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 5px 0 5px;
                color: {self.theme['dark']};
                background-color: white;
            }}
        """)
        test_data_layout = QVBoxLayout(test_data_group)
        
        # Description label
        test_data_desc = QLabel("Import test data to validate your rules. You can use sample data or load a JSON file.")
        test_data_desc.setWordWrap(True)
        test_data_desc.setStyleSheet(f"color: {self.theme['text']};")
        test_data_layout.addWidget(test_data_desc)
        
        # Test Data Buttons
        test_data_buttons = QHBoxLayout()
        
        # Sample data button
        sample_data_btn = QPushButton("Load Sample Data")
        sample_data_btn.clicked.connect(self.set_sample_data)
        sample_data_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['secondary']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #0D9B6C;
            }}
        """)
        
        # JSON upload button
        upload_json_btn = QPushButton("Upload JSON File")
        upload_json_btn.clicked.connect(self.upload_json)
        upload_json_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['primary']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme['primary_dark']};
            }}
        """)
        
        test_data_buttons.addWidget(sample_data_btn)
        test_data_buttons.addWidget(upload_json_btn)
        test_data_layout.addLayout(test_data_buttons)
        
        right_layout.addWidget(test_data_group)
        
        # Data Tree Section
        data_tree_group = QGroupBox("JSON Viewer")
        data_tree_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: white;
                border-radius: 8px;
                border: 1px solid {self.theme['border']};
                padding: 16px;
                font-weight: bold;
                color: {self.theme['dark']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 5px 0 5px;
                color: {self.theme['dark']};
                background-color: white;
            }}
        """)
        data_tree_layout = QVBoxLayout(data_tree_group)
        
        # JSON Tree Widget
        self.json_tree = QTreeWidget()
        self.json_tree.setHeaderLabels(["Field", "Value", "Type", "Path"])
        self.json_tree.setAlternatingRowColors(True)
        self.json_tree.setColumnWidth(0, 200)
        self.json_tree.setColumnWidth(1, 300)
        self.json_tree.setColumnWidth(2, 100)
        self.json_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.json_tree.setStyleSheet(f"""
            QTreeWidget {{
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                background-color: white;
                color: {self.theme['dark']};
            }}
            QTreeWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {self.theme['border']};
            }}
            QHeaderView::section {{
                background-color: {self.theme['light']};
                color: {self.theme['dark']};
                border: 1px solid {self.theme['border']};
                padding: 4px;
                font-weight: bold;
            }}
        """)
        data_tree_layout.addWidget(self.json_tree)
        
        # Tree Control Buttons
        tree_controls = QHBoxLayout()
        
        # Expand/Collapse buttons
        expand_all_btn = QPushButton("Expand All")
        expand_all_btn.clicked.connect(self.expand_all_tree_items)
        expand_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['tertiary']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #7C3AED;
            }}
        """)
        
        collapse_all_btn = QPushButton("Collapse All")
        collapse_all_btn.clicked.connect(self.collapse_all_tree_items)
        collapse_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['dark']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #0F172A;
            }}
        """)
        
        tree_controls.addWidget(expand_all_btn)
        tree_controls.addWidget(collapse_all_btn)
        data_tree_layout.addLayout(tree_controls)
        
        right_layout.addWidget(data_tree_group)
        
        # Data Actions
        data_actions_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self.save_changes)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['primary']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme['primary_dark']};
            }}
        """)
        
        export_btn = QPushButton("Export Data")
        export_btn.clicked.connect(self.export_data)
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['secondary']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #0D9B6C;
            }}
        """)
        
        data_actions_layout.addWidget(save_btn)
        data_actions_layout.addWidget(export_btn)
        right_layout.addLayout(data_actions_layout)
        
        # Add right widget to splitter
        main_splitter.addWidget(right_widget)
        
        # Set the splitter proportions
        main_splitter.setSizes([400, 600])
        
        # Add splitter to main layout
        layout.addWidget(main_splitter)
        
        # Navigation buttons at bottom
        nav_layout = QHBoxLayout()
        
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.navigate_back)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['dark']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}
        """)
        
        nav_layout.addWidget(back_btn)
        nav_layout.addStretch()
        layout.addLayout(nav_layout)
        
        self.setLayout(layout)
    
    def set_data(self, data):
        """Set the data to be validated"""
        self.data = data
        self.modified_data = data.copy()
        self.update_data_view()
        self.update_field_combo()
    
    def update_data_table(self):
        """Update the data table with current data - deprecated, use update_data_view instead"""
        self.update_data_view()

    def update_data_view(self):
        """Update the JSON tree view"""
        self.json_tree.clear()
        
        if self.json_data:
            # Use the original JSON data if available
            self.populate_tree(self.json_data)
        elif self.modified_data is not None:
            # Try to convert from dataframe if no original JSON
            # Not ideal, but allows backwards compatibility
            try:
                json_dict = {}
                # Convert each row to a nested structure
                for idx, row in self.modified_data.iterrows():
                    row_dict = {}
                    for col in self.modified_data.columns:
                        parts = col.split('_')
                        current = row_dict
                        for i, part in enumerate(parts[:-1]):
                            if part not in current:
                                current[part] = {}
                            current = current[part]
                        current[parts[-1]] = row[col]
                    
                    # Use index as top-level key
                    json_dict[f"row_{idx}"] = row_dict
                
                self.json_data = json_dict
                self.populate_tree(json_dict)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error converting data to tree: {str(e)}")
    
    def populate_tree(self, data, parent=None, key='root', path=''):
        """
        Recursively populate tree with JSON data
        
        Args:
            data: The data to add to the tree
            parent: The parent item (or None for root)
            key: The key for this data
            path: The JSON path to this element
        """
        if parent is None:
            # Root level - add data with proper type
            if isinstance(data, dict):
                # Add dictionary items
                for k, v in data.items():
                    current_path = k
                    item = QTreeWidgetItem(self.json_tree, [k, '', 'object', current_path])
                    item.setExpanded(False)  # Initially collapsed
                    self.populate_tree(v, item, k, current_path)
            elif isinstance(data, list):
                # Add list items
                for i, v in enumerate(data):
                    current_path = f'[{i}]'
                    item = QTreeWidgetItem(self.json_tree, [f'Item {i}', '', 'array', current_path])
                    item.setExpanded(False)  # Initially collapsed
                    self.populate_tree(v, item, str(i), current_path)
            else:
                # Add primitive value
                item = QTreeWidgetItem(self.json_tree, ['Value', str(data), type(data).__name__, ''])
        else:
            # Child items
            if isinstance(data, dict):
                # Add dictionary items
                for k, v in data.items():
                    current_path = f"{path}.{k}" if path else k
                    item = QTreeWidgetItem(parent, [k, '', 'object', current_path])
                    self.populate_tree(v, item, k, current_path)
            elif isinstance(data, list):
                # Add list items
                for i, v in enumerate(data):
                    current_path = f"{path}[{i}]"
                    item = QTreeWidgetItem(parent, [f'Item {i}', '', 'array', current_path])
                    self.populate_tree(v, item, str(i), current_path)
            else:
                # Add primitive value
                value_str = str(data)
                data_type = type(data).__name__
                item = QTreeWidgetItem(parent, [key, value_str, data_type, path])
                
                # Color-code by data type
                if data_type == 'int' or data_type == 'float':
                    item.setForeground(1, QColor('#0284c7'))  # Blue for numbers
                elif data_type == 'bool':
                    item.setForeground(1, QColor('#9333ea'))  # Purple for booleans
                elif data_type == 'str':
                    item.setForeground(1, QColor('#047857'))  # Green for strings
                elif data is None:
                    item.setForeground(1, QColor('#6b7280'))  # Gray for None/null
                    
                # Add the path to the item's data
                item.setData(0, Qt.UserRole, path)
    
    def on_tree_item_clicked(self, item, column):
        """Handle tree item click"""
        # Get the JSON path from the item
        path = item.text(3)
        if path:
            # Set the field combo to this path
            index = self.field_combo.findText(path)
            if index >= 0:
                self.field_combo.setCurrentIndex(index)
            else:
                # Add it if it doesn't exist
                self.field_combo.addItem(path)
                self.field_combo.setCurrentIndex(self.field_combo.count() - 1)
    
    def expand_all_tree_items(self):
        """Expand all items in the tree"""
        self.json_tree.expandAll()
        
    def collapse_all_tree_items(self):
        """Collapse all items in the tree"""
        self.json_tree.collapseAll()
    
    def update_field_combo(self):
        """Update the field combo box with available JSON paths"""
        if not hasattr(self, 'field_combo'):
            return
            
        self.field_combo.clear()
        
        # Start with paths from the DataFrame columns for backward compatibility
        if self.modified_data is not None:
            self.field_combo.addItems(self.modified_data.columns)
        
        # Add paths from the JSON tree if available
        if hasattr(self, 'json_tree'):
            paths = self.collect_json_paths()
            # Add unique paths that aren't already in the list
            for path in paths:
                if self.field_combo.findText(path) == -1:
                    self.field_combo.addItem(path)
    
    def collect_json_paths(self):
        """Collect all JSON paths from the tree"""
        paths = []
        
        def traverse_tree(item):
            # Get path from the Path column (column 3)
            path = item.text(3)
            if path and path not in paths:
                paths.append(path)
                
            # Traverse children
            for i in range(item.childCount()):
                traverse_tree(item.child(i))
        
        # Start traversal from root items
        for i in range(self.json_tree.topLevelItemCount()):
            traverse_tree(self.json_tree.topLevelItem(i))
            
        return paths
    
    def determine_section_type(self, path):
        """Determine which section a path belongs to based on path components"""
        path_lower = path.lower()
        
        # Check explicit section markers in the path
        if '.header.' in path_lower or path_lower.endswith('.header'):
            return "header"
        elif '.items.' in path_lower or path_lower.endswith('.items') or '[items]' in path_lower:
            return "items"
        elif '.summary.' in path_lower or path_lower.endswith('.summary'):
            return "summary"
        elif '.metadata.' in path_lower or path_lower.endswith('.metadata'):
            return "metadata"
            
        # If using underscore notation (for DataFrame columns)
        if '_header_' in path_lower or path_lower.startswith('header_'):
            return "header"
        elif '_items_' in path_lower or path_lower.startswith('items_'):
            return "items"
        elif '_summary_' in path_lower or path_lower.startswith('summary_'):
            return "summary"
        elif '_metadata_' in path_lower or path_lower.startswith('metadata_'):
            return "metadata"
            
        # Try to infer from context
        if 'invoice' in path_lower or 'date' in path_lower or 'number' in path_lower:
            return "header"
        elif 'total' in path_lower or 'sum' in path_lower or 'tax' in path_lower:
            return "summary"
        elif 'quantity' in path_lower or 'price' in path_lower or 'item' in path_lower or 'product' in path_lower:
            return "items"
            
        # Default to unknown
        return "unknown"
    
    def add_validation_rule(self):
        """Add a new validation rule"""
        field = self.field_combo.currentText()
        rule_type = self.rule_type_combo.currentText()
        params = self.rule_params.toPlainText()
        
        if not field or not rule_type:
            QMessageBox.warning(self, "Warning", "Please select a field and rule type")
            return
            
        # Check if this is a template path (contains *)
        is_template = '*' in field
        
        # Determine section type based on path
        section_type = self.determine_section_type(field)
        
        # Add rule to the rules list
        row = self.rules_list.rowCount()
        self.rules_list.insertRow(row)
        
        field_item = QTableWidgetItem(field)
        field_item.setForeground(QColor(self.theme['dark']))
        
        # Set different background colors based on section type
        if section_type == "header":
            field_item.setBackground(QColor("#E6F4FF"))  # Light blue
            field_item.setToolTip(f"Section: Header")
        elif section_type == "items":
            field_item.setBackground(QColor("#E6FFEA"))  # Light green
            field_item.setToolTip(f"Section: Items")
        elif section_type == "summary":
            field_item.setBackground(QColor("#FFF0E6"))  # Light orange
            field_item.setToolTip(f"Section: Summary")
        elif section_type == "metadata":
            field_item.setBackground(QColor("#F5F5F5"))  # Light gray
            field_item.setToolTip(f"Section: Metadata")
        
        # If template path, add additional highlight
        if is_template:
            field_item.setFont(QFont("Arial", 9, QFont.Bold))
            if field_item.toolTip():
                field_item.setToolTip(f"{field_item.toolTip()} - Template path with wildcards")
            else:
                field_item.setToolTip("Template path with wildcards")
        
        rule_type_item = QTableWidgetItem(rule_type)
        rule_type_item.setForeground(QColor(self.theme['dark']))
        
        params_item = QTableWidgetItem(params)
        params_item.setForeground(QColor(self.theme['dark']))
        
        self.rules_list.setItem(row, 0, field_item)
        self.rules_list.setItem(row, 1, rule_type_item)
        self.rules_list.setItem(row, 2, params_item)
        
        # Store rule in validation_rules with section information
        if field not in self.validation_rules:
            self.validation_rules[field] = []
            
        self.validation_rules[field].append({
            "type": rule_type,
            "params": params,
            "section": section_type
        })
        
        # Clear input fields
        self.rule_params.clear()
        
        # Show success message with section information
        QMessageBox.information(
            self, 
            "Rule Added", 
            f"Validation rule added successfully to the {section_type.upper()} section."
        )
    
    def clear_rules(self):
        """Clear all validation rules"""
        self.rules_list.setRowCount(0)
        self.validation_rules = {}
    
    def validate_data(self):
        """Validate the data according to the rules"""
        if self.modified_data is None:
            QMessageBox.warning(self, "Warning", "No data to validate")
            return
            
        # Reset all item colors
        self.reset_all_tree_item_colors(self.json_tree.invisibleRootItem())
        
        # Structure to track validation issues by section
        validation_issues = {
            "header": [],
            "items": [],
            "summary": [],
            "metadata": [],
            "unknown": []
        }
        
        # Track validation counts by section
        validation_counts = {
            "header": 0,
            "items": 0,
            "summary": 0,
            "metadata": 0,
            "unknown": 0
        }
        
        # Track issue counts by section
        issue_counts = {
            "header": 0,
            "items": 0,
            "summary": 0,
            "metadata": 0,
            "unknown": 0
        }
        
        total_validations = 0
        total_issues = 0
        
        # Apply validation rules
        for json_path, rules in self.validation_rules.items():
            # Handle template paths (with wildcards)
            if '*' in json_path:
                matching_paths = self.find_paths_matching_template(json_path)
                if not matching_paths:
                    # Determine which section this path belongs to
                    section = self.determine_section_type(json_path)
                    validation_issues[section].append(f"No paths match template: {json_path}")
                    issue_counts[section] += 1
                    total_issues += 1
                    continue
                
                # Apply rules to all matching paths
                for actual_path in matching_paths:
                    column_name = self.find_closest_column_name(actual_path)
                    if not column_name or column_name not in self.modified_data.columns:
                        continue
                    
                    col_index = self.modified_data.columns.get_loc(column_name)
                    
                    for rule in rules:
                        rule_type = rule["type"]
                        params = rule["params"]
                        
                        # Get section from rule or determine from path
                        section = rule.get("section", self.determine_section_type(actual_path))
                        
                        for i in range(len(self.modified_data)):
                            total_validations += 1
                            validation_counts[section] += 1
                            
                            value = str(self.modified_data.iloc[i, col_index])
                            is_valid = self.validate_value(value, rule_type, params, i)
                            
                            if not is_valid:
                                self.highlight_tree_item(actual_path, value, self.theme["danger"])
                                validation_issues[section].append(f"Row {i+1}, Path '{actual_path}': Failed {rule_type} validation")
                                issue_counts[section] += 1
                                total_issues += 1
            else:
                # Regular path (no wildcards)
                column_name = self.find_closest_column_name(json_path)
                
                if not column_name or column_name not in self.modified_data.columns:
                    # Determine which section this path belongs to
                    section = self.determine_section_type(json_path)
                    validation_issues[section].append(f"Path not found: {json_path}")
                    issue_counts[section] += 1
                    total_issues += 1
                    continue
                    
                col_index = self.modified_data.columns.get_loc(column_name)
                
                for rule in rules:
                    rule_type = rule["type"]
                    params = rule["params"]
                    
                    # Get section from rule or determine from path
                    section = rule.get("section", self.determine_section_type(json_path))
                    
                    for i in range(len(self.modified_data)):
                        total_validations += 1
                        validation_counts[section] += 1
                        
                        value = str(self.modified_data.iloc[i, col_index])
                        is_valid = self.validate_value(value, rule_type, params, i)
                        
                        if not is_valid:
                            self.highlight_tree_item(json_path, value, self.theme["danger"])
                            validation_issues[section].append(f"Row {i+1}, Path '{json_path}': Failed {rule_type} validation")
                            issue_counts[section] += 1
                            total_issues += 1
        
        # Format the detailed validation results message
        if total_issues > 0:
            # Create a detailed message with sections
            sections_with_issues = []
            
            for section, issues in validation_issues.items():
                if issues:
                    section_title = section.upper()
                    issues_text = "\n".join([f"• {issue}" for issue in issues[:5]])
                    
                    if len(issues) > 5:
                        issues_text += f"\n  ... and {len(issues) - 5} more {section} issues"
                    
                    section_summary = f"{section_title} SECTION: {len(issues)} issues out of {validation_counts[section]} validations\n{issues_text}"
                    sections_with_issues.append(section_summary)
            
            detailed_message = "\n\n".join(sections_with_issues)
            
            # Create custom dialog for validation results
            result_dialog = QMessageBox(self)
            result_dialog.setWindowTitle("Validation Results")
            result_dialog.setIcon(QMessageBox.Warning)
            
            # Set dialog text
            result_dialog.setText(f"<h3>Validation Issues Found</h3>")
            result_dialog.setInformativeText(
                f"<p>Found <b>{total_issues}</b> issues out of <b>{total_validations}</b> validations.</p>"
                f"<p>Issues by section:</p>"
                f"<ul>"
                f"<li><b>Header:</b> {issue_counts['header']} issues / {validation_counts['header']} validations</li>"
                f"<li><b>Items:</b> {issue_counts['items']} issues / {validation_counts['items']} validations</li>"
                f"<li><b>Summary:</b> {issue_counts['summary']} issues / {validation_counts['summary']} validations</li>"
                f"<li><b>Metadata:</b> {issue_counts['metadata']} issues / {validation_counts['metadata']} validations</li>"
                f"</ul>"
            )
            
            # Add detailed text
            result_dialog.setDetailedText(detailed_message)
            
            # Show the dialog
            result_dialog.exec()
        else:
            # Create section summary for successful validation
            section_summary = ""
            for section, count in validation_counts.items():
                if count > 0:
                    section_summary += f"• {section.title()}: {count} validations\n"
            
            QMessageBox.information(
                self, 
                "Validation Successful", 
                f"All {total_validations} validations passed successfully!\n\n"
                f"Validations by section:\n{section_summary}"
            )
    
    def find_closest_column_name(self, json_path):
        """Find the closest column name for a given JSON path"""
        # Direct match
        if json_path in self.modified_data.columns:
            return json_path
        
        # Try normalized path
        normalized_path = json_path.replace('.', '_').replace('[', '_').replace(']', '')
        if normalized_path in self.modified_data.columns:
            return normalized_path
        
        # Fix for paths that include indexed items like [0]
        # This is especially for paths like: TXA2449341-GU01A.pdf.header.table_0.page_1[0].invoice_number
        if "[" in json_path and "]" in json_path:
            # Create variations of the path with different index handling
            variations = []
            
            # Variation 1: Remove brackets completely
            variations.append(json_path.replace("[", "").replace("]", ""))
            
            # Variation 2: Replace [n] with _n
            index_pattern = r'\[(\d+)\]'
            variations.append(re.sub(index_pattern, r'_\1', json_path))
            
            # Variation 3: Replace entire [n] with nothing
            variations.append(re.sub(index_pattern, '', json_path))
            
            # Try all variations with underscore normalization
            for var in variations:
                var_normalized = var.replace('.', '_')
                if var_normalized in self.modified_data.columns:
                    return var_normalized
                
                # Try with trimming the last part (for paths ending with index)
                if var.endswith(']'):
                    last_bracket = var.rindex('[')
                    var_trimmed = var[:last_bracket]
                    var_trimmed_normalized = var_trimmed.replace('.', '_')
                    if var_trimmed_normalized in self.modified_data.columns:
                        return var_trimmed_normalized
        
        # Check if it's a wildcard path with filename
        if '.' in json_path:
            # Extract the structure after the filename (which may be variable)
            parts = json_path.split('.')
            if len(parts) > 1:
                # Try to match the path structure (*.metadata.filename)
                wildcard_path = f"*.{'.'.join(parts[1:])}"
                wildcard_path_normalized = wildcard_path.replace('.', '_').replace('*_', '')
                
                # Look for columns that match this pattern
                for col in self.modified_data.columns:
                    # Check if the column ends with our normalized path structure
                    if col.endswith(wildcard_path_normalized):
                        return col
                    
                    # Check if column has the same structure with any filename
                    col_parts = col.split('_')
                    if len(col_parts) >= len(parts):
                        # Skip the first part (filename) and match the rest
                        if '_'.join(col_parts[1:]) == '_'.join(parts[1:]).replace('.', '_').replace('[', '_').replace(']', ''):
                            return col
        
        # Debug info - print columns to help diagnose issues
        print(f"Path not found: {json_path}")
        print(f"Normalized path: {normalized_path}")
        print(f"Available columns: {', '.join(self.modified_data.columns[:10])}...")
                            
        # Fallback: Check if it's a subpath
        for col in self.modified_data.columns:
            if json_path in col or col.endswith(json_path.replace('.', '_').replace('[', '_').replace(']', '')):
                return col
                
        return None
    
    def reset_all_tree_item_colors(self, item):
        """Reset all tree item colors recursively"""
        # Process current item
        for i in range(item.columnCount()):
            item.setBackground(i, QColor("transparent"))
            item.setForeground(i, QColor(self.theme['dark']))
            
        # Process child items
        for i in range(item.childCount()):
            self.reset_all_tree_item_colors(item.child(i))
    
    def highlight_tree_item(self, path, value=None, color=None):
        """Highlight a tree item by its path"""
        # Split path into components
        components = []
        in_bracket = False
        current = ""
        
        for c in path:
            if c == '.' and not in_bracket:
                if current:
                    components.append(current)
                    current = ""
            elif c == '[':
                if current:
                    components.append(current)
                    current = ""
                in_bracket = True
                current += c
            elif c == ']':
                current += c
                if current:
                    components.append(current)
                    current = ""
                in_bracket = False
            else:
                current += c
                
        if current:
            components.append(current)
        
        # Print debug info
        print(f"Path components: {components}")
        
        # Find items in different ways to handle variable filenames
        found_items = []
        
        # 1. Direct path match
        exact_matches = self.json_tree.findItems(path, Qt.MatchExactly, 3)
        found_items.extend(exact_matches)
        
        # 2. If path contains dots (likely nested structure)
        if not found_items:
            # Try matching individual components recursively
            self._find_matching_items(self.json_tree.invisibleRootItem(), components, 0, found_items)
        
        # 3. Try by searching for the file and then the rest of the path
        if not found_items and len(components) > 1 and components[0].endswith('.pdf'):
            # Find the file node first
            file_items = []
            self._find_file_items(self.json_tree.invisibleRootItem(), components[0], file_items)
            
            # If file found, look for the path under it
            for file_item in file_items:
                rest_components = components[1:]
                self._find_matching_items(file_item, rest_components, 0, found_items)
        
        # If still no matches, try looser matching
        if not found_items:
            self._find_loose_matching_items(self.json_tree.invisibleRootItem(), path, found_items)
        
        # If found items, highlight them
        if found_items:
            for item in found_items:
                # Highlight all columns
                for i in range(item.columnCount()):
                    item.setBackground(i, QColor(color))
                    if color == self.theme["danger"]:
                        item.setForeground(i, QColor("white"))
                
                # Ensure the item is visible
                self.json_tree.scrollToItem(item)
                
                # Expand parents
                parent = item.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
        else:
            print(f"No tree items found for path: {path}")
    
    def _find_file_items(self, node, filename, found_items):
        """Find items matching a filename"""
        for i in range(node.childCount()):
            child = node.child(i)
            # Check if this node is the file
            if child.text(0) == filename or child.text(1) == filename:
                found_items.append(child)
            # Check children recursively
            self._find_file_items(child, filename, found_items)
    
    def _find_loose_matching_items(self, node, path, found_items):
        """Try to find items matching parts of the path"""
        path_parts = path.replace('[', '.').replace(']', '').split('.')
        last_part = path_parts[-1]
        
        for i in range(node.childCount()):
            child = node.child(i)
            
            # Check if this node matches the last part of the path
            if child.text(0) == last_part:
                found_items.append(child)
                
            # If this is a leaf with a value, check the value too
            if child.childCount() == 0 and child.text(1) and child.text(1) == last_part:
                found_items.append(child)
                
            # Check children recursively
            self._find_loose_matching_items(child, path, found_items)
            
    def _find_matching_items(self, node, path_components, current_index, found_items):
        """Recursively find items matching path components"""
        if current_index >= len(path_components):
            return
            
        current_component = path_components[current_index]
        
        # Debug info
        print(f"Looking for component: {current_component} at index {current_index}")
        
        # Handle array indices specially
        is_array_index = current_component.startswith('[') and current_component.endswith(']')
        array_index = -1
        if is_array_index:
            try:
                array_index = int(current_component[1:-1])
                print(f"Array index: {array_index}")
            except ValueError:
                pass
        
        # Special handling for the first component which might be a variable filename
        if current_index == 0 and current_component.endswith('.pdf'):
            # Look for any item that might be a PDF filename
            for i in range(node.childCount()):
                child = node.child(i)
                # If it's a PDF file or contains "metadata" as child
                if child.text(0).endswith('.pdf') or self._has_child_with_text(child, path_components[1] if len(path_components) > 1 else ""):
                    if current_index == len(path_components) - 1:
                        found_items.append(child)
                    else:
                        self._find_matching_items(child, path_components, current_index + 1, found_items)
        elif is_array_index and array_index >= 0:
            # Handle array indices - find the Nth child that's relevant
            matched_items = []
            for i in range(node.childCount()):
                child = node.child(i)
                # In arrays, items are often named like "Item 0", "Item 1"
                if child.text(0).startswith("Item ") or child.text(3).endswith(f"[{array_index}]"):
                    matched_items.append(child)
            
            # If we found enough items, use the one at the specified index
            if array_index < len(matched_items):
                child = matched_items[array_index]
                if current_index == len(path_components) - 1:
                    found_items.append(child)
                else:
                    self._find_matching_items(child, path_components, current_index + 1, found_items)
        else:
            # Regular matching for non-first components
            for i in range(node.childCount()):
                child = node.child(i)
                if (child.text(0) == current_component or 
                    child.text(3).endswith(current_component) or
                    (current_component.isdigit() and child.text(0) == f"Item {current_component}")):
                    
                    if current_index == len(path_components) - 1:
                        found_items.append(child)
                    else:
                        self._find_matching_items(child, path_components, current_index + 1, found_items)
    
    def _has_child_with_text(self, node, text):
        """Check if node has a child with the given text"""
        for i in range(node.childCount()):
            if node.child(i).text(0) == text:
                return True
        return False
    
    def validate_value(self, value, rule_type, params, row_index=0):
        """Validate a single value against a rule"""
        if rule_type == "Required":
            return bool(value.strip())
        elif rule_type == "Numeric":
            try:
                float(value)
                return True
            except ValueError:
                return False
        elif rule_type == "Date":
            try:
                pd.to_datetime(value)
                return True
            except:
                return False
        elif rule_type == "Email":
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(email_pattern, value))
        elif rule_type == "Custom Regex":
            try:
                return bool(re.match(params, value))
            except:
                return False
        elif rule_type == "Row Total":
            try:
                columns = params.split(',')
                # Sum values for this row across specified columns
                row_sum = sum(float(self.modified_data.iloc[row_index, self.modified_data.columns.get_loc(col.strip())])
                           for col in columns)
                # Compare with expected value
                return abs(row_sum - float(value)) < 0.01
            except Exception as e:
                print(f"Row Total validation error: {e}")
                return False
        elif rule_type == "Column Total":
            try:
                column = params.strip()
                total = float(value)
                col_sum = self.modified_data[column].astype(float).sum()
                return abs(col_sum - total) < 0.01
            except Exception as e:
                print(f"Column Total validation error: {e}")
                return False
        elif rule_type == "Merge Row":
            try:
                columns = params.split(',')
                return all(self.modified_data.iloc[row_index, self.modified_data.columns.get_loc(col.strip())] == value 
                         for col in columns)
            except Exception as e:
                print(f"Merge Row validation error: {e}")
                return False
        elif rule_type == "Invoice Item Type":
            try:
                item_types = [t.strip() for t in params.split(',')]
                return value.strip() in item_types
            except Exception as e:
                print(f"Invoice Item Type validation error: {e}")
                return False
        elif rule_type == "Table Start Pattern":
            try:
                return bool(re.match(params, value))
            except Exception as e:
                print(f"Table Start Pattern validation error: {e}")
                return False
        elif rule_type == "Table End Pattern":
            try:
                return bool(re.match(params, value))
            except Exception as e:
                print(f"Table End Pattern validation error: {e}")
                return False
        elif rule_type == "Skip Line Pattern":
            try:
                return not bool(re.match(params, value))
            except Exception as e:
                print(f"Skip Line Pattern validation error: {e}")
                return False
        return True
    
    def save_changes(self):
        """Save the modified data"""
        if self.json_data is None and self.modified_data is None:
            return
            
        # Currently we don't support modifying the JSON data directly in the tree
        # This is a placeholder for future implementation of editable tree
        QMessageBox.information(self, "Success", "Changes saved successfully")
    
    def export_data(self):
        """Export the JSON data"""
        if self.json_data is None and self.modified_data is None:
            return
            
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            "",
            "JSON Files (*.json);;CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
            
        try:
            if file_path.endswith('.json'):
                # Export as JSON
                with open(file_path, 'w') as f:
                    json.dump(self.json_data, f, indent=4)
            elif file_path.endswith('.csv'):
                # Export as CSV (using DataFrame)
                self.modified_data.to_csv(file_path, index=False)
            elif file_path.endswith('.xlsx'):
                # Export as Excel (using DataFrame)
                self.modified_data.to_excel(file_path, index=False)
            
            QMessageBox.information(self, "Success", f"Data exported successfully to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error exporting data: {str(e)}")
    
    def navigate_back(self):
        """Return to the previous screen"""
        self.back_requested.emit()
        
    def save_rules(self):
        """Save validation rules to JSON file or selected template"""
        if not self.validation_rules:
            QMessageBox.warning(self, "Warning", "No rules to save")
            return
            
        # Ask user if they want to save to file or template
        if hasattr(self, 'template_combo') and self.template_combo.count() > 0 and self.template_combo.isEnabled():
            choice = QMessageBox.question(
                self, 
                "Save Rules", 
                "Do you want to save rules to a template or to a file?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            
            if choice == QMessageBox.StandardButton.Yes:
                # Save to template
                self.save_rules_to_template()
                return
            elif choice == QMessageBox.StandardButton.Cancel:
                return
        
        # Save to file
        try:
            # Ask for file path
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Rules",
                "",
                "JSON Files (*.json)"
            )
            
            if not file_path:
                return
                
            # Convert rules to serializable format
            serialized_rules = {}
            for field, rules in self.validation_rules.items():
                serialized_rules[field] = []
                for rule in rules:
                    serialized_rules[field].append({
                        "type": rule["type"],
                        "params": rule["params"]
                    })
            
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(serialized_rules, f, indent=4)
                
            QMessageBox.information(self, "Success", f"Rules saved successfully to file: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving rules: {str(e)}")
    
    def load_rules(self, silent=False):
        """Load validation rules from a template or file"""
        # Ask user if they want to load from file or template
        if hasattr(self, 'template_combo') and self.template_combo.count() > 0 and self.template_combo.isEnabled() and not silent:
            choice = QMessageBox.question(
                self, 
                "Load Rules", 
                "Do you want to load rules from a template or from a file?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            
            if choice == QMessageBox.StandardButton.Yes:
                # Load from template
                self.load_rules_from_template()
                return
            elif choice == QMessageBox.StandardButton.Cancel:
                return
        
        # Load from file
        try:
            if silent:
                # Use default file path during initialization
                file_path = self.rules_file_path
                if not os.path.exists(file_path):
                    return
            else:
                # Ask for file path
                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Load Rules",
                    "",
                    "JSON Files (*.json)"
                )
                
                if not file_path:
                    return
                
            with open(file_path, 'r') as f:
                loaded_rules = json.load(f)
            
            # Clear existing rules
            self.clear_rules()
            
            # Add loaded rules
            for field, rules in loaded_rules.items():
                for rule in rules:
                    if field not in self.validation_rules:
                        self.validation_rules[field] = []
                    
                    self.validation_rules[field].append({
                        "type": rule["type"],
                        "params": rule["params"]
                    })
                    
                    # Add to UI list
                    row = self.rules_list.rowCount()
                    self.rules_list.insertRow(row)
                    
                    field_item = QTableWidgetItem(field)
                    field_item.setForeground(QColor(self.theme['dark']))
                    if '*' in field:
                        field_item.setBackground(QColor(self.theme['light']))
                        field_item.setToolTip("This is a template path with wildcards")
                    
                    rule_type_item = QTableWidgetItem(rule["type"])
                    rule_type_item.setForeground(QColor(self.theme['dark']))
                    
                    params_item = QTableWidgetItem(rule["params"])
                    params_item.setForeground(QColor(self.theme['dark']))
                    
                    self.rules_list.setItem(row, 0, field_item)
                    self.rules_list.setItem(row, 1, rule_type_item)
                    self.rules_list.setItem(row, 2, params_item)
                    
            if not silent and self.validation_rules:
                QMessageBox.information(self, "Success", f"Rules loaded successfully from file: {file_path}")
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, "Error", f"Error loading rules: {str(e)}")
            
    def load_rules_from_template(self):
        """Load validation rules from the selected template"""
        if not hasattr(self, 'template_combo') or self.template_combo.count() == 0:
            QMessageBox.warning(self, "Warning", "No templates available")
            return
            
        # Get the selected template ID from the combo box
        template_id = self.template_combo.currentData()
        template_name = self.template_combo.currentText()
        
        if not template_id:
            QMessageBox.warning(self, "Warning", "No template selected")
            return
            
        try:
            # Connect to database
            import sqlite3
            conn = sqlite3.connect("invoice_templates.db")
            cursor = conn.cursor()
            
            # Verify template exists
            cursor.execute("SELECT id FROM templates WHERE id = ?", (template_id,))
            if not cursor.fetchone():
                QMessageBox.warning(self, "Warning", f"Template with ID {template_id} not found")
                conn.close()
                return
            
            # Check if validation_rules column exists
            cursor.execute("PRAGMA table_info(templates)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if "validation_rules" not in column_names:
                QMessageBox.warning(self, "Warning", "No validation rules found in the database schema")
                conn.close()
                return
                
            # Get the validation rules for the template
            cursor.execute("SELECT validation_rules FROM templates WHERE id = ?", (template_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result or not result[0]:
                QMessageBox.warning(self, "Warning", f"No validation rules found for template: {template_name}")
                return
            
            # Try to parse the rules
            try:
                loaded_rules = json.loads(result[0])
            except json.JSONDecodeError:
                QMessageBox.critical(self, "Error", f"Invalid JSON format in validation rules for template: {template_name}")
                return
                
            if not loaded_rules:
                QMessageBox.warning(self, "Warning", f"Template '{template_name}' has empty rules")
                return
                
            # Clear existing rules
            self.clear_rules()
            
            # Add loaded rules
            rules_count = 0
            section_counts = {
                "header": 0,
                "items": 0,
                "summary": 0,
                "metadata": 0,
                "unknown": 0
            }
            
            for field, rules in loaded_rules.items():
                for rule in rules:
                    if "type" not in rule or "params" not in rule:
                        continue  # Skip invalid rules
                        
                    if field not in self.validation_rules:
                        self.validation_rules[field] = []
                    
                    # Get section from rule or determine from path
                    if "section" in rule:
                        section_type = rule["section"]
                    else:
                        section_type = self.determine_section_type(field)
                    
                    # Store the rule with section info
                    self.validation_rules[field].append({
                        "type": rule["type"],
                        "params": rule["params"],
                        "section": section_type
                    })
                    
                    # Update section counts
                    section_counts[section_type] += 1
                    
                    # Add to UI list
                    row = self.rules_list.rowCount()
                    self.rules_list.insertRow(row)
                    
                    field_item = QTableWidgetItem(field)
                    field_item.setForeground(QColor(self.theme['dark']))
                    
                    # Set different background colors based on section type
                    if section_type == "header":
                        field_item.setBackground(QColor("#E6F4FF"))  # Light blue
                        field_item.setToolTip(f"Section: Header")
                    elif section_type == "items":
                        field_item.setBackground(QColor("#E6FFEA"))  # Light green
                        field_item.setToolTip(f"Section: Items")
                    elif section_type == "summary":
                        field_item.setBackground(QColor("#FFF0E6"))  # Light orange
                        field_item.setToolTip(f"Section: Summary")
                    elif section_type == "metadata":
                        field_item.setBackground(QColor("#F5F5F5"))  # Light gray
                        field_item.setToolTip(f"Section: Metadata")
                    
                    # If template path, add additional highlight
                    if '*' in field:
                        field_item.setFont(QFont("Arial", 9, QFont.Bold))
                        if field_item.toolTip():
                            field_item.setToolTip(f"{field_item.toolTip()} - Template path with wildcards")
                        else:
                            field_item.setToolTip("Template path with wildcards")
                    
                    rule_type_item = QTableWidgetItem(rule["type"])
                    rule_type_item.setForeground(QColor(self.theme['dark']))
                    
                    params_item = QTableWidgetItem(rule["params"])
                    params_item.setForeground(QColor(self.theme['dark']))
                    
                    self.rules_list.setItem(row, 0, field_item)
                    self.rules_list.setItem(row, 1, rule_type_item)
                    self.rules_list.setItem(row, 2, params_item)
                    
                    rules_count += 1
            
            # Create section summary for loaded rules
            section_summary = ""
            for section, count in section_counts.items():
                if count > 0:
                    section_summary += f"• {section.title()}: {count} rules\n"
            
            if rules_count > 0:
                QMessageBox.information(
                    self, 
                    "Rules Loaded", 
                    f"Successfully loaded {rules_count} validation rules from template:\n{template_name}\n\n"
                    f"Rules by section:\n{section_summary}"
                )
            else:
                QMessageBox.warning(self, "Warning", f"No valid rules found in template: {template_name}")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Database Error", f"Error loading rules from template: {str(e)}")
            import traceback
            traceback.print_exc()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading rules from template: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def set_sample_data(self):
        """Set sample data for rules testing in rules manager mode"""
        if not self.is_rules_manager and not hasattr(self, 'json_tree'):
            return
            
        # Create sample data with complex nested structure
        sample_data = {
            "invoices": [
                {
                    "metadata": {
                        "filename": "TXA2449341-GU01A.pdf",
                        "page_count": 3,
                        "template_type": "multi",
                        "export_date": "2023-04-04T12:13:18.517184",
                        "template_name": "service-3 (Multi, 3 pages)"
                    },
                    "header": {
                        "table_0": {
                            "page_1": [
                                {
                                    "invoice_number": "TXA24-49341(Cash)",
                                    "invoice_date": "2023-01-15"
                                }
                            ]
                        },
                        "table_1": {
                            "page_1": [
                                {
                                    "reg_no": "DL7CW6200",
                                    "gstin": ""
                                }
                            ]
                        }
                    },
                    "items": [
                        {
                            "description": "Service A",
                            "quantity": 1,
                            "unit_price": 100.00,
                            "amount": 100.00,
                            "item_type": "service"
                        },
                        {
                            "description": "Service B",
                            "quantity": 2,
                            "unit_price": 150.00,
                            "amount": 300.00,
                            "item_type": "service"
                        }
                    ],
                    "summary": {
                        "subtotal": 400.00,
                        "tax": 40.00,
                        "total": 440.00
                    }
                },
                {
                    "metadata": {
                        "filename": "TXA2449342-GU01A.pdf",
                        "page_count": 2,
                        "template_type": "multi",
                        "export_date": "2023-04-04T12:13:18.548881",
                        "template_name": "service-3 (Multi, 3 pages)"
                    },
                    "header": {
                        "table_0": {
                            "page_1": [
                                {
                                    "invoice_number": "TXA24-49342(Cash)",
                                    "invoice_date": "2023-02-20"
                                }
                            ]
                        },
                        "table_1": {
                            "page_1": [
                                {
                                    "reg_no": "HR55AR6587",
                                    "gstin": "06AAUPK9184B1ZC"
                                }
                            ]
                        }
                    },
                    "items": [
                        {
                            "description": "Product A",
                            "quantity": 3,
                            "unit_price": 200.00,
                            "amount": 600.00,
                            "item_type": "product"
                        }
                    ],
                    "summary": {
                        "subtotal": 600.00,
                        "tax": 60.00,
                        "total": 660.00
                    }
                }
            ]
        }
        
        # Store original JSON
        self.json_data = sample_data
        
        # Convert to DataFrame for backward compatibility
        df = self.json_to_dataframe(sample_data)
        
        # Set as current data
        self.set_data(df)
    
    def load_templates(self):
        """Load available templates into the combo box"""
        if not hasattr(self, 'template_combo'):
            return
            
        try:
            # Connect to database
            import sqlite3
            conn = sqlite3.connect("invoice_templates.db")
            cursor = conn.cursor()
            
            # Get all templates
            cursor.execute("SELECT id, name FROM templates ORDER BY name")
            templates = cursor.fetchall()
            
            # Clear the combo box
            self.template_combo.clear()
            
            # Add templates to the combo box
            for template_id, template_name in templates:
                # Store the ID as user data
                self.template_combo.addItem(template_name, template_id)
                
            conn.close()
            
            # Check if any templates were loaded
            if self.template_combo.count() == 0:
                self.template_combo.addItem("No templates available")
                self.template_combo.setEnabled(False)
                QMessageBox.warning(self, "Warning", "No templates available in database. Please create templates first.")
            else:
                self.template_combo.setEnabled(True)
                print(f"Loaded {self.template_combo.count()} templates successfully")
                
        except Exception as e:
            print(f"Error loading templates: {str(e)}")
            self.template_combo.addItem("Error loading templates")
            self.template_combo.setEnabled(False)
            QMessageBox.critical(self, "Database Error", f"Error loading templates: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def save_rules_to_template(self):
        """Save validation rules to the selected template"""
        if not self.validation_rules:
            QMessageBox.warning(self, "Warning", "No rules to save to template")
            return
            
        if not hasattr(self, 'template_combo') or self.template_combo.count() == 0:
            QMessageBox.warning(self, "Warning", "No templates available")
            return
            
        # Get the selected template ID from the combo box
        template_id = self.template_combo.currentData()
        template_name = self.template_combo.currentText()
        
        if not template_id:
            QMessageBox.warning(self, "Warning", "No template selected")
            return
                
        try:
            # Connect to database
            import sqlite3
            conn = sqlite3.connect("invoice_templates.db")
            cursor = conn.cursor()
            
            # Verify template exists
            cursor.execute("SELECT id FROM templates WHERE id = ?", (template_id,))
            if not cursor.fetchone():
                QMessageBox.warning(self, "Warning", f"Template with ID {template_id} not found")
                conn.close()
                return
            
            # Check if validation_rules column exists
            cursor.execute("PRAGMA table_info(templates)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if "validation_rules" not in column_names:
                # Add the column if it doesn't exist
                cursor.execute("ALTER TABLE templates ADD COLUMN validation_rules TEXT")
                conn.commit()
                print("Added validation_rules column to templates table")
            
            # Convert rules to serializable format with section info
            serialized_rules = {}
            section_counts = {
                "header": 0,
                "items": 0, 
                "summary": 0,
                "metadata": 0,
                "unknown": 0
            }
            
            for field, rules in self.validation_rules.items():
                serialized_rules[field] = []
                for rule in rules:
                    # Get section from rule or determine from path
                    if "section" in rule:
                        section_type = rule["section"]
                    else:
                        section_type = self.determine_section_type(field)
                        
                    serialized_rules[field].append({
                        "type": rule["type"],
                        "params": rule["params"],
                        "section": section_type
                    })
                    
                    # Update section counts
                    section_counts[section_type] += 1
            
            # Save to database
            json_rules = json.dumps(serialized_rules)
            cursor.execute(
                "UPDATE templates SET validation_rules = ? WHERE id = ?",
                (json_rules, template_id)
            )
            
            if cursor.rowcount == 0:
                QMessageBox.warning(self, "Warning", f"No changes made to template '{template_name}'")
                conn.close()
                return
                
            conn.commit()
            
            # Verify update was successful
            cursor.execute("SELECT validation_rules FROM templates WHERE id = ?", (template_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            if not result or not result[0]:
                QMessageBox.warning(self, "Warning", f"Failed to save rules to template '{template_name}'")
                return
            
            # Create section summary text
            section_summary = ""
            for section, count in section_counts.items():
                if count > 0:
                    section_summary += f"• {section.title()}: {count} rules\n"
                
            QMessageBox.information(
                self, 
                "Rules Saved", 
                f"Successfully saved {sum(len(rules) for rules in self.validation_rules.values())} validation rules to template:\n{template_name}\n\n"
                f"Rules by section:\n{section_summary}\n"
                f"These rules will be applied when validating data extracted with this template."
            )
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Database Error", f"Error saving rules to template: {str(e)}")
            import traceback
            traceback.print_exc()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving rules to template: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def upload_json(self):
        """Upload JSON file for testing rules"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select JSON File",
            "",
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    json_data = json.load(f)
                
                # Store original JSON data
                self.json_data = json_data
                
                # Convert JSON to DataFrame for backward compatibility
                df = self.json_to_dataframe(json_data)
                
                # Set data
                self.set_data(df)
                QMessageBox.information(self, "Success", f"JSON data loaded successfully with {len(df)} rows")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading JSON: {str(e)}")

    def json_to_dataframe(self, data):
        """Convert complex JSON to a DataFrame with flattened structure"""
        flattened_data = []
        
        # Handle different types of JSON structures
        if isinstance(data, dict):
            # Case 1: Multiple files/documents in a single JSON
            for filename, file_data in data.items():
                # Process each file's data
                file_row = self.flatten_json(file_data, prefix=filename)
                flattened_data.append(file_row)
        elif isinstance(data, list):
            # Case 2: List of objects
            for item in data:
                flattened_item = self.flatten_json(item)
                flattened_data.append(flattened_item)
        else:
            # Case 3: Simple object
            flattened_data.append(self.flatten_json(data))
        
        # Convert to DataFrame
        df = pd.DataFrame(flattened_data)
        return df

    def flatten_json(self, json_obj, prefix=''):
        """Flatten nested JSON into key-value pairs with path as keys"""
        flattened = {}
        
        def _flatten(obj, name=''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{name}_{key}" if name else key
                    _flatten(value, new_key)
            elif isinstance(obj, list):
                # For lists, add index to key
                for i, item in enumerate(obj):
                    if isinstance(item, (dict, list)):
                        _flatten(item, f"{name}_{i}")
                    else:
                        flattened[f"{name}_{i}"] = item
            else:
                flattened[name] = obj
        
        # Start the recursive flattening
        _flatten(json_obj)
        
        # Add prefix if specified (useful for multiple files)
        if prefix and not prefix.endswith('_'):
            prefixed_flattened = {f"{prefix}_{k}": v for k, v in flattened.items()}
            return prefixed_flattened
        
        return flattened 

    def find_paths_matching_template(self, template_path):
        """Find all JSON paths that match a template path with wildcards"""
        matching_paths = []
        
        # For column-based matching
        if self.modified_data is not None:
            # Convert template to regex pattern
            pattern = template_path.replace('.', '\\.').replace('*', '.*').replace('[', '\\[').replace(']', '\\]')
            pattern = f"^{pattern}$"
            
            # Find columns matching the pattern
            for col in self.collect_json_paths():
                if re.match(pattern, col):
                    matching_paths.append(col)
                    
        return matching_paths

    def show_path_help(self):
        """Show help about path templates and wildcards"""
        help_text = """
<h3>Path Templates & Wildcards</h3>

<p>When validating files with variable names, you can use template paths with wildcards.</p>

<h4>Examples:</h4>
<ul>
<li><b>*.metadata.filename</b> - Match any file's metadata filename</li>
<li><b>*.header.table_0.page_1[0].invoice_number</b> - Match any file's invoice number</li>
<li><b>invoices[*].items[*].amount</b> - Match all item amounts in all invoices</li>
</ul>

<h4>Syntax:</h4>
<ul>
<li>Use <b>*</b> to replace variable parts like filenames</li>
<li>Use <b>[*]</b> to match any array index</li>
<li>Use dot notation for nested objects</li>
</ul>

<p>The system will find the appropriate paths in your data that match the template pattern.</p>
"""
        
        QMessageBox.information(self, "Path Templates Help", help_text)

    def delete_selected_rule(self):
        """Delete the selected rule from the list"""
        selected_row = self.rules_list.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a rule to delete")
            return
            
        # Get the field and index to remove from validation_rules
        field = self.rules_list.item(selected_row, 0).text()
        rule_type = self.rules_list.item(selected_row, 1).text()
        params = self.rules_list.item(selected_row, 2).text()
        
        # Remove the rule from validation_rules
        if field in self.validation_rules:
            # Find matching rule and remove it
            for i, rule in enumerate(self.validation_rules[field]):
                if rule["type"] == rule_type and rule["params"] == params:
                    self.validation_rules[field].pop(i)
                    break
                    
            # If no more rules for this field, remove the field entry
            if not self.validation_rules[field]:
                del self.validation_rules[field]
        
        # Remove from UI
        self.rules_list.removeRow(selected_row)
        
        # Show success message
        QMessageBox.information(self, "Success", f"Rule deleted successfully") 