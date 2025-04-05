from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QRadioButton, QButtonGroup, QFileDialog,
                             QScrollArea, QFrame, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

class InvoiceConfigScreen(QWidget):
    # Define signals for navigation
    config_completed = Signal(dict)  # Emits configuration when done
    go_back = Signal()  # Signal to go back to previous screen

    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                color: #333333;
            }
            QLabel {
                color: #333333;
            }
            QRadioButton {
                color: #333333;
                font-size: 14px;
                padding: 5px;
            }
            QRadioButton:checked {
                color: #4169E1;
            }
            QPushButton {
                background-color: #4169E1;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #3158D3;
            }
        """)
        self.initUI()
        self.current_config = {
            'header_location': 'first_page',
            'has_multiple_pages': False,
            'has_middle_pages': False,
            'summary_location': 'last_page',
            'sample_multi_page_invoice': None
        }

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Title
        title = QLabel("Invoice Configuration")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #333333; margin: 20px 0;")
        layout.addWidget(title)

        # Description
        description = QLabel("Please configure how your invoice should be processed by answering the following questions:")
        description.setWordWrap(True)
        description.setStyleSheet("color: #666666; font-size: 16px; margin: 10px 0;")
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)

        # Create a scroll area for the content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(30)

        # 1. Header Location
        header_group = self.create_section(
            "1. Invoice Header Location",
            "Where is the invoice header information located in your document?",
            [
                ("First page only - Header appears only on the first page", "first_page"),
                ("All pages - Header information repeats on every page", "all_pages")
            ],
            'header_location'
        )
        content_layout.addWidget(header_group)

        # 2. Multiple Pages
        multiple_pages_group = self.create_section(
            "2. Multiple Pages Support",
            "How are the pages structured in this invoice type?",
            [
                ("Single page only - Invoice is always one page", "single"),
                ("Multiple pages with repeating middle section - Has identical structured middle pages", "multiple_with_middle"),
                ("Multiple pages without repeating section - Each page is unique", "multiple_no_middle")
            ],
            'has_multiple_pages'
        )
        content_layout.addWidget(multiple_pages_group)

        # 3. Summary Location
        summary_group = self.create_section(
            "3. Summary Location",
            "Where can the invoice summary (totals, tax, etc.) be found?",
            [
                ("Last page only - Summary appears only on the final page", "last_page"),
                ("Every page - Summary information appears on all pages", "every_page")
            ],
            'summary_location'
        )
        content_layout.addWidget(summary_group)

        # 4. Sample Multi-page Invoice Upload
        self.multi_page_section = QFrame()
        self.multi_page_section.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                margin-top: 10px;
            }
        """)
        multi_page_layout = QVBoxLayout(self.multi_page_section)
        
        multi_page_title = QLabel("4. Sample Multi-page Invoice")
        multi_page_title.setFont(QFont("Arial", 14, QFont.Bold))
        multi_page_title.setStyleSheet("color: #333333;")
        
        multi_page_desc = QLabel(
            "To properly configure the extraction process, please upload a sample multi-page invoice. "
            "This will help us understand:\n\n"
            "• How to identify and process item details across middle pages\n"
            "• Where to locate the final summary section\n"
            "• How to handle page transitions"
        )
        multi_page_desc.setWordWrap(True)
        multi_page_desc.setStyleSheet("color: #666666; font-size: 14px; margin: 10px 0;")
        
        upload_btn = QPushButton("Upload Multi-page Invoice")
        upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                padding: 12px 24px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3158D3;
            }
        """)
        upload_btn.clicked.connect(self.upload_multi_page_invoice)
        
        self.upload_status = QLabel("")
        self.upload_status.setStyleSheet("color: #666666; font-size: 14px; margin-top: 10px;")
        
        multi_page_layout.addWidget(multi_page_title)
        multi_page_layout.addWidget(multi_page_desc)
        multi_page_layout.addWidget(upload_btn)
        multi_page_layout.addWidget(self.upload_status)
        
        self.multi_page_section.setVisible(False)
        content_layout.addWidget(self.multi_page_section)

        # Add spacer
        content_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Navigation buttons
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
        
        next_btn = QPushButton("Next →")
        next_btn.clicked.connect(self.complete_configuration)
        next_btn.setStyleSheet("""
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
        nav_layout.addWidget(next_btn)
        
        content_layout.addLayout(nav_layout)

        # Set up scroll area
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        self.setLayout(layout)

    def create_section(self, title, question, options, config_key):
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        layout = QVBoxLayout(section)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet("color: #333333;")
        layout.addWidget(title_label)
        
        # Question
        question_label = QLabel(question)
        question_label.setWordWrap(True)
        question_label.setStyleSheet("color: #666666; font-size: 14px; margin: 10px 0;")
        layout.addWidget(question_label)
        
        # Radio buttons
        button_group = QButtonGroup(section)
        
        for i, (text, value) in enumerate(options):
            radio = QRadioButton(text)
            radio.setStyleSheet("""
                QRadioButton {
                    font-size: 14px;
                    padding: 5px;
                    color: #333333;
                }
                QRadioButton:checked {
                    color: #4169E1;
                }
            """)
            if i == 0:  # Select first option by default
                radio.setChecked(True)
            button_group.addButton(radio, i)
            layout.addWidget(radio)
            
            # Connect the button to update configuration
            radio.toggled.connect(
                lambda checked, v=value, k=config_key: 
                self.update_config(k, v if checked else None)
            )
            
            # Special handling for multiple pages option
            if config_key == 'has_multiple_pages':
                radio.toggled.connect(
                    lambda checked, v=value:
                    self.multi_page_section.setVisible(checked and v in ['multiple_with_middle', 'multiple_no_middle'])
                )
        
        return section

    def update_config(self, key, value):
        if value is not None:
            if key == 'has_multiple_pages':
                self.current_config[key] = (value in ['multiple_with_middle', 'multiple_no_middle'])
                self.current_config['has_middle_pages'] = (value == 'multiple_with_middle')
                # Show/hide multi-page upload section based on any multiple page type
                if hasattr(self, 'multi_page_section'):
                    self.multi_page_section.setVisible(self.current_config[key])
            else:
                self.current_config[key] = value

    def upload_multi_page_invoice(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Multi-page PDF Invoice", "", "PDF Files (*.pdf)"
        )
        if file_path:
            self.current_config['sample_multi_page_invoice'] = file_path
            self.upload_status.setText(f"Uploaded: {file_path.split('/')[-1]}")
            self.upload_status.setStyleSheet("color: green;")

    def complete_configuration(self):
        # Validate if multi-page invoice is uploaded when needed
        if (self.current_config['has_multiple_pages'] and 
            not self.current_config['sample_multi_page_invoice']):
            self.upload_status.setText("Please upload a multi-page invoice sample!")
            self.upload_status.setStyleSheet("color: red;")
            return
            
        self.config_completed.emit(self.current_config) 