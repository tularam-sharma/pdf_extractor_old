from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit,
    QGroupBox, QSplitter, QFrame, QScrollArea, QCheckBox,
    QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
import pandas as pd
import json
import os

class ValidationScreen(QWidget):
    # Define signals
    back_requested = Signal()  # Signal for navigating back to main dashboard
    
    def __init__(self, parent=None, is_rules_manager=False):
        super().__init__(parent)
        self.parent = parent
        self.data = None
        self.validation_rules = {}
        self.modified_data = None
        self.is_rules_manager = is_rules_manager  # Flag to indicate if used as rules manager
        self.rules_file_path = os.path.join(os.path.dirname(__file__), "validation_rules.json")
        
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
            self.load_rules()
            self.set_sample_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Add title if this is rules manager
        if self.is_rules_manager:
            title_label = QLabel("Rules Management")
            title_label.setFont(QFont("Arial", 18, QFont.Bold))
            title_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(title_label)
            
            description_label = QLabel("Create and manage validation rules for data extraction")
            description_label.setAlignment(Qt.AlignCenter)
            description_label.setStyleSheet(f"color: {self.theme['text']}; margin-bottom: 16px;")
            layout.addWidget(description_label)

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
            }}
        """)
        rules_layout = QVBoxLayout(rules_group)
        
        # Field Selection
        field_layout = QHBoxLayout()
        field_label = QLabel("Field:")
        self.field_combo = QComboBox()
        field_layout.addWidget(field_label)
        field_layout.addWidget(self.field_combo)
        rules_layout.addLayout(field_layout)
        
        # Rule Type Selection
        rule_type_layout = QHBoxLayout()
        rule_type_label = QLabel("Rule Type:")
        self.rule_type_combo = QComboBox()
        self.rule_type_combo.addItems([
            "Required",
            "Numeric",
            "Date",
            "Email",
            "Custom Regex"
        ])
        rule_type_layout.addWidget(rule_type_label)
        rule_type_layout.addWidget(self.rule_type_combo)
        rules_layout.addLayout(rule_type_layout)
        
        # Rule Parameters
        self.rule_params = QLineEdit()
        self.rule_params.setPlaceholderText("Enter rule parameters (e.g., regex pattern)")
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
        rules_layout.addWidget(add_rule_btn)
        
        # Rules List
        self.rules_list = QTableWidget()
        self.rules_list.setColumnCount(3)
        self.rules_list.setHorizontalHeaderLabels(["Field", "Rule Type", "Parameters"])
        self.rules_list.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                background-color: white;
            }}
        """)
        rules_layout.addWidget(self.rules_list)
        
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
        
        # Add Save/Load Rules buttons if this is rules manager
        if self.is_rules_manager:
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
        
        # Data Table
        self.data_table = QTableWidget()
        self.data_table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                background-color: white;
            }}
        """)
        right_layout.addWidget(self.data_table)
        
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
        main_splitter.setSizes([300, 700])
        
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
        self.update_data_table()
        self.update_field_combo()
    
    def update_data_table(self):
        """Update the data table with current data"""
        if self.modified_data is None:
            return
            
        self.data_table.setRowCount(len(self.modified_data))
        self.data_table.setColumnCount(len(self.modified_data.columns))
        self.data_table.setHorizontalHeaderLabels(self.modified_data.columns)
        
        for i in range(len(self.modified_data)):
            for j in range(len(self.modified_data.columns)):
                value = str(self.modified_data.iloc[i, j])
                item = QTableWidgetItem(value)
                self.data_table.setItem(i, j, item)
    
    def update_field_combo(self):
        """Update the field combo box with available columns"""
        if self.modified_data is None:
            return
            
        self.field_combo.clear()
        self.field_combo.addItems(self.modified_data.columns)
    
    def add_validation_rule(self):
        """Add a new validation rule"""
        field = self.field_combo.currentText()
        rule_type = self.rule_type_combo.currentText()
        params = self.rule_params.text()
        
        if not field or not rule_type:
            QMessageBox.warning(self, "Warning", "Please select a field and rule type")
            return
            
        # Add rule to the rules list
        row = self.rules_list.rowCount()
        self.rules_list.insertRow(row)
        self.rules_list.setItem(row, 0, QTableWidgetItem(field))
        self.rules_list.setItem(row, 1, QTableWidgetItem(rule_type))
        self.rules_list.setItem(row, 2, QTableWidgetItem(params))
        
        # Store rule in validation_rules
        if field not in self.validation_rules:
            self.validation_rules[field] = []
            
        self.validation_rules[field].append({
            "type": rule_type,
            "params": params
        })
        
        # Clear input fields
        self.rule_params.clear()
    
    def clear_rules(self):
        """Clear all validation rules"""
        self.rules_list.setRowCount(0)
        self.validation_rules = {}
    
    def validate_data(self):
        """Validate the data according to the rules"""
        if self.modified_data is None:
            QMessageBox.warning(self, "Warning", "No data to validate")
            return
            
        # Reset cell colors
        for i in range(self.data_table.rowCount()):
            for j in range(self.data_table.columnCount()):
                self.data_table.item(i, j).setBackground(QColor("white"))
        
        # Apply validation rules
        for field, rules in self.validation_rules.items():
            if field not in self.modified_data.columns:
                continue
                
            col_index = self.modified_data.columns.get_loc(field)
            
            for rule in rules:
                rule_type = rule["type"]
                params = rule["params"]
                
                for i in range(len(self.modified_data)):
                    value = str(self.modified_data.iloc[i, col_index])
                    is_valid = self.validate_value(value, rule_type, params)
                    
                    if not is_valid:
                        self.data_table.item(i, col_index).setBackground(QColor(self.theme["danger"]))
    
    def validate_value(self, value, rule_type, params):
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
            # Add date validation logic
            return True
        elif rule_type == "Email":
            # Add email validation logic
            return True
        elif rule_type == "Custom Regex":
            try:
                import re
                return bool(re.match(params, value))
            except:
                return False
        return True
    
    def save_changes(self):
        """Save the modified data"""
        if self.modified_data is None:
            return
            
        # Update modified_data from table
        for i in range(self.data_table.rowCount()):
            for j in range(self.data_table.columnCount()):
                value = self.data_table.item(i, j).text()
                self.modified_data.iloc[i, j] = value
        
        QMessageBox.information(self, "Success", "Changes saved successfully")
    
    def export_data(self):
        """Export the validated data"""
        if self.modified_data is None:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            "",
            "CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        
        if file_path:
            if file_path.endswith('.csv'):
                self.modified_data.to_csv(file_path, index=False)
            else:
                self.modified_data.to_excel(file_path, index=False)
            
            QMessageBox.information(self, "Success", "Data exported successfully")
    
    def navigate_back(self):
        """Return to the previous screen"""
        self.back_requested.emit()
        
    def save_rules(self):
        """Save validation rules to JSON file"""
        if not self.validation_rules:
            QMessageBox.warning(self, "Warning", "No rules to save")
            return
            
        try:
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
            with open(self.rules_file_path, 'w') as f:
                json.dump(serialized_rules, f, indent=4)
                
            QMessageBox.information(self, "Success", "Rules saved successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving rules: {str(e)}")
    
    def load_rules(self):
        """Load validation rules from JSON file"""
        try:
            if not os.path.exists(self.rules_file_path):
                # No rules file exists yet
                return
                
            with open(self.rules_file_path, 'r') as f:
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
                    self.rules_list.setItem(row, 0, QTableWidgetItem(field))
                    self.rules_list.setItem(row, 1, QTableWidgetItem(rule["type"]))
                    self.rules_list.setItem(row, 2, QTableWidgetItem(rule["params"]))
                    
            if self.validation_rules:
                QMessageBox.information(self, "Success", "Rules loaded successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading rules: {str(e)}")
            
    def set_sample_data(self):
        """Set sample data for rules testing in rules manager mode"""
        if not self.is_rules_manager:
            return
            
        # Create sample data with common fields
        sample_data = {
            "header_invoice_number": "INV-001",
            "header_invoice_date": "2023-01-15",
            "header_due_date": "2023-02-15",
            "header_vendor_name": "ABC Company",
            "header_vendor_address": "123 Main St, City, Country",
            "header_customer_name": "XYZ Corporation",
            "header_customer_address": "456 Business Ave, Town, Country",
            "items_description": "Product A",
            "items_quantity": "5",
            "items_unit_price": "100.00",
            "items_amount": "500.00",
            "summary_subtotal": "500.00",
            "summary_tax": "50.00",
            "summary_total": "550.00",
            "pdf_file": "sample_invoice.pdf",
            "template_type": "invoice",
            "pdf_page_count": "1"
        }
        
        # Convert to DataFrame
        df = pd.DataFrame([sample_data])
        
        # Set as current data
        self.set_data(df) 