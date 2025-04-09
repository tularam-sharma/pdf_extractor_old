import sys
import os
import re
import json
import sqlite3
from datetime import datetime
import fitz  # PyMuPDF
import pypdf_table_extraction
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QTableWidget,
    QTableWidgetItem,
    QProgressBar,
    QFileDialog,
    QMessageBox,
    QComboBox,
    QStackedWidget,
    QFrame,
    QHeaderView,
    QGroupBox,
    QSplitter,
    QGridLayout,
    QSizePolicy,
    QListView,
    QStyle,
    QProxyStyle,
)
from PySide6.QtCore import Qt, Signal, QObject, QRect, QTimer
from PySide6.QtGui import QColor, QFont, QIcon
import pandas as pd
import time


class NoFrameStyle(QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.SH_ComboBox_Popup:
            return 0
        return super().styleHint(hint, option, widget, returnData)
        

class BulkProcessor(QWidget):
    # Define signals
    back_requested = Signal()  # Signal for navigating back to main dashboard
    go_back = Signal()  # Signal for navigating back to main dashboard
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.pdf_files = []
        self.processed_data = {}
        
        # Initialize stop flag for processing
        self.should_stop = False
        self.start_time = None
        
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
        
        # Set widget background
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.theme['bg']};
                color: {self.theme['text']};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            
            QLabel {{
                font-size: 14px;
            }}
            
            QComboBox {{
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                padding: 8px 12px;
                background-color: white;
                min-height: 22px;
                selection-background-color: {self.theme['primary']};
            }}
            
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 0px;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }}
            
            QListWidget {{
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                background-color: white;
                padding: 8px;
                selection-background-color: {self.theme['primary']};
                selection-color: white;
            }}
            
            QTableWidget {{
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                background-color: white;
                gridline-color: {self.theme['border']};
                selection-background-color: {self.theme['primary']};
                selection-color: white;
            }}
            
            QTableWidget::item {{
                padding: 6px;
            }}
            
            QHeaderView::section {{
                background-color: {self.theme['light']};
                border: none;
                padding: 8px;
                font-weight: bold;
                color: {self.theme['text']};
                border-right: 1px solid {self.theme['border']};
                border-bottom: 1px solid {self.theme['border']};
            }}
            
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: {self.theme['light']};
                height: 12px;
                text-align: center;
            }}
            
            QProgressBar::chunk {{
                background-color: {self.theme['primary']};
                border-radius: 4px;
            }}
        """)
        
        self.init_ui()
        self.load_templates()  # Load templates when initializing
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # # Header section - Title and info
        # header_layout = QHBoxLayout()
        # title_label = QLabel("PDF Table Extractor", self)
        # title_label.setStyleSheet(f"""
        #     font-size: 24px;
        #     font-weight: bold;
        #     color: {self.theme['primary']};
        # """)
        # header_layout.addWidget(title_label)
        # header_layout.addStretch()
        # layout.addLayout(header_layout)
        
        # Create a horizontal splitter to divide the screen left/right
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setHandleWidth(1)
        main_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {self.theme['border']};
            }}
        """)
        
        # LEFT SECTION - Extraction controls
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(16)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Template selection with card style
        template_card = QFrame(self)
        template_card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 8px;
                border: 1px solid {self.theme['border']};
                padding: 16px;
            }}
        """)
        template_layout = QVBoxLayout(template_card)
        template_label = QLabel("Select Template", self)
        template_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        template_layout.addWidget(template_label)
        
        template_input_layout = QHBoxLayout()
        self.template_combo = QComboBox(self)
        self.template_combo.setMinimumHeight(36)
        
        # Apply custom style to remove frame
        self.template_combo.setStyle(NoFrameStyle())
        
        # Create and set a custom list view for the combo box
        list_view = QListView()
        list_view.setFrameShape(QListView.NoFrame)
        self.template_combo.setView(list_view)
        
        # Styled dropdown with proper border
        self.template_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 8px 12px;
                background-color: white;
                min-height: 36px;
                color: #1F2937;
                font-size: 14px;
            }
            
            QComboBox:hover, QComboBox:focus {
                border: 1px solid #6366F1;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: none;
            }
            
            QComboBox QAbstractItemView {
                border: 1px solid #E5E7EB;
                border-radius: 4px;
                padding: 4px;
                background-color: white;
                outline: none;
            }
            
            QComboBox QAbstractItemView::item {
                border-bottom: 1px solid #F3F4F6;
                padding: 8px 12px;
                min-height: 30px;
                color: #1F2937;
            }
            
            QComboBox QAbstractItemView::item:last-child {
                border-bottom: none;
            }
            
            QComboBox QAbstractItemView::item:hover {
                background-color: #F3F4F6;
            }
            
            QComboBox QAbstractItemView::item:selected {
                background-color: #EEF2FF;
                color: #4F46E5;
            }
        """)
        
        # Add refresh button
        refresh_btn = QPushButton("Refresh", self)
        refresh_btn.clicked.connect(self.load_templates)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['primary']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                min-height: 36px;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['primary_dark']};
            }}
            QPushButton:pressed {{
                background-color: {self.theme['primary_dark']};
                padding-top: 9px;
                padding-left: 17px;
            }}
        """)
        
        template_input_layout.addWidget(self.template_combo, 1)
        template_input_layout.addWidget(refresh_btn, 0)
        template_layout.addLayout(template_input_layout)
        
        # Multi-page info label with modern style
        self.multi_page_label = QLabel("Multi-page support: Enabled ✓", self)
        self.multi_page_label.setStyleSheet(f"""
            color: {self.theme['secondary']};
            font-weight: bold;
            padding: 4px 8px;
            background-color: {self.theme['secondary'] + '20'};
                border-radius: 4px;
        """)
        template_layout.addWidget(self.multi_page_label)
        
        # Status and Progress
        status_layout = QHBoxLayout()
        # Status indicator without any background or border
        self.status_label = QLabel("Ready", self)
        self.status_label.setStyleSheet("color: #00B8A9;")
        status_layout.addWidget(self.status_label)
        
        # Processing time label - simple text only
        self.processing_time_label = QLabel("", self)
        self.processing_time_label.setStyleSheet("color: #1F2937;")
        status_layout.addWidget(self.processing_time_label)
        
        # Add stretch to push labels to the left
        status_layout.addStretch()
        template_layout.addLayout(status_layout)
        
        # Progress bar and stop button in a layout
        progress_layout = QHBoxLayout()
        
        # Progress bar with modern style
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumHeight(8)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: {self.theme['light']};
                height: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {self.theme['primary']};
                border-radius: 4px;
            }}
        """)
        progress_layout.addWidget(self.progress_bar, 1)
        
        # Stop button
        self.stop_button = QPushButton("Stop", self)
        self.stop_button.clicked.connect(self.stop_processing)
        self.stop_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['danger']};
                color: white;
                padding: 4px 12px;
                border-radius: 4px;
                font-weight: bold;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['danger'] + 'CC'};
            }}
            QPushButton:pressed {{
                background-color: {self.theme['danger'] + 'AA'};
            }}
        """)
        self.stop_button.setVisible(False)
        progress_layout.addWidget(self.stop_button)
        
        template_layout.addLayout(progress_layout)
        
        left_layout.addWidget(template_card)
        
        # File Operations section
        file_card = QFrame(self)
        file_card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 8px;
                border: 1px solid {self.theme['border']};
                padding: 16px;
            }}
        """)
        file_layout = QVBoxLayout(file_card)
        
        file_title = QLabel("PDF Files", self)
        file_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        file_layout.addWidget(file_title)
        
        # File list with better spacing
        self.file_list = QListWidget(self)
        self.file_list.setMinimumHeight(200)
        self.file_list.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                background-color: white;
                padding: 4px;
            }}
            QListWidget::item {{
                border-bottom: 1px solid {self.theme['border'] + '50'};
                padding: 6px;
            }}
            QListWidget::item:selected {{
                background-color: {self.theme['primary'] + '30'};
                color: {self.theme['text']};
                border-radius: 4px;
            }}
        """)
        file_layout.addWidget(self.file_list)
        
        # Buttons for file operations
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        add_files_btn = QPushButton("Add Files", self)
        add_files_btn.clicked.connect(self.add_files)
        add_files_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['primary']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['primary_dark']};
            }}
            QPushButton:pressed {{
                background-color: {self.theme['primary_dark']};
                padding-top: 9px;
                padding-left: 17px;
            }}
        """)
        
        clear_files_btn = QPushButton("Clear Files", self)
        clear_files_btn.clicked.connect(self.clear_files)
        clear_files_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: {self.theme['text']};
                padding: 8px 16px;
                border-radius: 6px;
                border: 1px solid {self.theme['border']};
                font-weight: bold;
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['light']};
            }}
            QPushButton:pressed {{
                background-color: {self.theme['border']};
                padding-top: 9px;
                padding-left: 17px;
            }}
        """)
        
        process_btn = QPushButton("Process Files", self)
        process_btn.clicked.connect(self.process_files)
        process_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['primary']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['primary_dark']};
            }}
            QPushButton:pressed {{
                background-color: {self.theme['primary_dark']};
                padding-top: 9px;
                padding-left: 17px;
            }}
        """)
        
        button_layout.addWidget(add_files_btn)
        button_layout.addWidget(clear_files_btn)
        button_layout.addWidget(process_btn)
        file_layout.addLayout(button_layout)
        left_layout.addWidget(file_card)
        
        # Navigation section at bottom of left panel
        nav_layout = QHBoxLayout()
        
        # Back button on the left
        back_btn = QPushButton("← Back", self)
        back_btn.clicked.connect(self.navigate_back)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['dark']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                min-height: 36px;
            }}
            QPushButton:pressed {{
                background-color: {self.theme['dark'] + 'C0'};
                padding-top: 9px;
                padding-left: 17px;
            }}
        """)
        
        # Reset screen button on the right
        reset_btn = QPushButton("Reset Screen", self)
        reset_btn.clicked.connect(self.reset_screen)
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['danger']};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['danger'] + 'E0'};
            }}
            QPushButton:pressed {{
                background-color: {self.theme['danger'] + 'C0'};
                padding-top: 9px;
                padding-left: 17px;
            }}
        """)
        
        nav_layout.addWidget(back_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(reset_btn)
        
        left_layout.addLayout(nav_layout)
        
        # Add left widget to splitter
        main_splitter.addWidget(left_widget)
        
        # RIGHT SECTION - Extraction results
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(16)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Results section
        results_card = QFrame(self)
        results_card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 8px;
                border: 1px solid {self.theme['border']};
                padding: 16px;
            }}
        """)
        results_layout = QVBoxLayout(results_card)
        
        results_title = QLabel("Extraction Results", self)
        results_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        results_layout.addWidget(results_title)
        
        # Summary statistics panel
        summary_frame = QFrame()
        summary_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['light']};
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 12px;
            }}
            QLabel {{
                font-size: 13px;
            }}
        """)
        summary_layout = QGridLayout(summary_frame)
        summary_layout.setSpacing(12)
        
        # Add summary statistics labels
        processed_label = QLabel("Processed Files:", self)
        processed_label.setStyleSheet("font-weight: bold;")
        self.processed_count = QLabel("0", self)
        self.processed_count.setStyleSheet(f"color: {self.theme['primary']}; font-weight: bold;")
        
        success_label = QLabel("Successful:", self)
        success_label.setStyleSheet("font-weight: bold;")
        self.success_count = QLabel("0", self)
        self.success_count.setStyleSheet(f"color: {self.theme['secondary']}; font-weight: bold;")
        
        failed_label = QLabel("Failed:", self)
        failed_label.setStyleSheet("font-weight: bold;")
        self.failed_count = QLabel("0", self)
        self.failed_count.setStyleSheet(f"color: {self.theme['danger']}; font-weight: bold;")
        
        total_rows_label = QLabel("Total Rows Extracted:", self)
        total_rows_label.setStyleSheet("font-weight: bold;")
        self.total_rows_count = QLabel("0", self)
        self.total_rows_count.setStyleSheet("font-weight: bold;")
        
        # Add labels to grid layout
        summary_layout.addWidget(processed_label, 0, 0)
        summary_layout.addWidget(self.processed_count, 0, 1)
        summary_layout.addWidget(success_label, 0, 2)
        summary_layout.addWidget(self.success_count, 0, 3)
        summary_layout.addWidget(failed_label, 0, 4)
        summary_layout.addWidget(self.failed_count, 0, 5)
        summary_layout.addWidget(total_rows_label, 1, 0, 1, 2)
        summary_layout.addWidget(self.total_rows_count, 1, 2, 1, 1)
        
        results_layout.addWidget(summary_frame)
        
        # Results table with modern style
        self.results_table = QTableWidget(self)
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels(
            [
                "File Name",
                "Extraction Status",
                "PDF Pages",
                "Header Data Rows",
                "Line Items Rows",
                "Summary Data Rows",
            ]
        )

        # Set up horizontal header with better styling
        header = self.results_table.horizontalHeader()
        
        # Configure header behavior
        header.setVisible(True)
        header.setHighlightSections(False)
        header.setStretchLastSection(False)
        header.setSectionsMovable(False)
        
        # Set column widths and resize modes
        column_widths = [250, 150, 100, 150, 150, 150]
        for i, width in enumerate(column_widths):
            self.results_table.setColumnWidth(i, width)
            header.setSectionResizeMode(i, QHeaderView.Fixed)  # Fixed width to prevent disappearing
        
        # Update table stylesheet with more prominent header styling and proper alignment
        self.results_table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                background-color: white;
                gridline-color: {self.theme['border']};
            }}
            
            QHeaderView::section {{
                background-color: white;
                color: {self.theme['text']};
                font-weight: bold;
                font-size: 13px;
                padding: 8px;
                border: 1px solid {self.theme['border']};
                min-height: 30px;
                max-height: 30px;
            }}
            
            QHeaderView::section:horizontal {{
                border-top: 1px solid {self.theme['border']};
                text-align: left;
                padding-left: 12px;
            }}
            
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {self.theme['border']};
                text-align: left;
                padding-left: 12px;
            }}
            
            QTableWidget::item:selected {{
                background-color: {self.theme['primary'] + '15'};
                color: {self.theme['text']};
            }}
        """)
        
        # Additional header settings
        header.setMinimumHeight(40)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # Enable features for better usability
        self.results_table.setAlternatingRowColors(False)  # Disable alternating row colors
        self.results_table.setShowGrid(True)
        self.results_table.setGridStyle(Qt.SolidLine)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.setMinimumHeight(300)
        
        # Set table size policy to expand properly
        self.results_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Ensure the table is properly contained in a frame
        table_frame = QFrame()
        table_frame.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                background-color: white;
                padding: 1px;
            }}
        """)
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(1, 1, 1, 1)
        table_layout.addWidget(self.results_table)
        
        results_layout.addWidget(table_frame)
        
        # Export section
        export_layout = QVBoxLayout()
        
        export_label = QLabel("Export Options:", self)
        export_label.setStyleSheet("font-weight: bold; font-size: 16px; margin-top: 8px;")
        export_layout.addWidget(export_label)
        
        export_buttons_layout = QHBoxLayout()
        export_buttons_layout.setSpacing(12)
        
        export_header_btn = QPushButton("Header Data", self)
        export_header_btn.clicked.connect(lambda: self.export_data("header"))
        export_header_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #00B8A9;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: #00A396;
            }}
            QPushButton:pressed {{
                background-color: #009688;
                padding-top: 9px;
                padding-left: 17px;
            }}
        """)
        
        export_items_btn = QPushButton("Item Data", self)
        export_items_btn.clicked.connect(lambda: self.export_data("items"))
        export_items_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #00B8A9;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: #00A396;
            }}
            QPushButton:pressed {{
                background-color: #009688;
                padding-top: 9px;
                padding-left: 17px;
            }}
        """)
        
        export_summary_btn = QPushButton("Summary Data", self)
        export_summary_btn.clicked.connect(lambda: self.export_data("summary"))
        export_summary_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #00B8A9;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: #00A396;
            }}
            QPushButton:pressed {{
                background-color: #009688;
                padding-top: 9px;
                padding-left: 17px;
            }}
        """)
        
        export_buttons_layout.addWidget(export_header_btn)
        export_buttons_layout.addWidget(export_items_btn)
        export_buttons_layout.addWidget(export_summary_btn)
        export_layout.addLayout(export_buttons_layout)
        
        results_layout.addLayout(export_layout)
        right_layout.addWidget(results_card)
        
        # Add right widget to splitter
        main_splitter.addWidget(right_widget)
        
        # Set the splitter proportions
        main_splitter.setSizes([500, 500])
        
        # Add splitter to main layout
        layout.addWidget(main_splitter)
        
        self.setLayout(layout)
    
    def load_templates(self):
        """Load templates from the database"""
        try:
            print("\nLoading templates for bulk processing...")
            conn = sqlite3.connect("invoice_templates.db")
            cursor = conn.cursor()
            
            # Check if the templates table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='templates'"
            )
            if not cursor.fetchone():
                print("Templates table does not exist in the database")
                conn.close()
                QMessageBox.warning(
                    self,
                    "No Templates",
                    "No template table found in the database. Please create templates first.",
                )
                return
            
            # Get table columns to handle different database schemas
            cursor.execute("PRAGMA table_info(templates)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            print(f"Available template columns: {column_names}")
            
            # Build query dynamically based on available columns
            select_columns = ["id"]
            if "name" in column_names:
                select_columns.append("name")
            else:
                select_columns.append("'Unnamed'")
            
            if "template_type" in column_names:
                select_columns.append("template_type")
            else:
                select_columns.append("'single'")
            
            if "page_count" in column_names:
                select_columns.append("page_count")
            else:
                select_columns.append("1")
            
            query = f"SELECT {', '.join(select_columns)} FROM templates"
            print(f"Query: {query}")
            
            # Execute the query
            cursor.execute(query)
            templates = cursor.fetchall()
            print(f"Found {len(templates)} templates")
            
            # Print template details for debugging
            for template in templates:
                template_id = template[0]
                template_name = template[1] if len(template) > 1 else "Unnamed"
                template_type = template[2] if len(template) > 2 else "single"
                page_count = template[3] if len(template) > 3 else 1
                print(
                    f"  Template: {template_id}, {template_name}, {template_type}, {page_count} pages"
                )
            
            # Clear and reload the combo box
            self.template_combo.clear()
            
            if not templates:
                print("No templates found in database")
                self.template_combo.addItem("No templates available", None)
                self.multi_page_label.setText("Multi-page support: No templates found")
                self.multi_page_label.setStyleSheet("color: orange;")
            else:
                has_multi_page = False
                for template in templates:
                    template_id = template[0]
                    template_name = template[1] if len(template) > 1 else "Unnamed"
                    template_type = template[2] if len(template) > 2 else "single"
                    page_count = template[3] if len(template) > 3 else 1

                    if template_type == "multi":
                        has_multi_page = True
                        display_text = f"{template_name} ({template_type.title()}, {page_count} pages)"
                    else:
                        display_text = f"{template_name} ({template_type.title()})"

                    self.template_combo.addItem(display_text, template_id)
                    print(
                        f"Added template to dropdown: {display_text}, ID: {template_id}"
                    )

                # Update multi-page indicator
                if has_multi_page:
                    self.multi_page_label.setText("Multi-page support: Enabled ✓")
                    self.multi_page_label.setStyleSheet(
                        "color: green; font-weight: bold;"
                    )
                else:
                    self.multi_page_label.setText(
                        "Multi-page support: No multi-page templates found"
                    )
                    self.multi_page_label.setStyleSheet("color: orange;")
            
            conn.close()
            print("Finished loading templates")
            
        except sqlite3.Error as e:
            error_msg = f"Database error while loading templates: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Database Error", error_msg)
            self.multi_page_label.setText("Multi-page support: Database error")
            self.multi_page_label.setStyleSheet("color: red;")
        except Exception as e:
            error_msg = f"Failed to load templates: {str(e)}"
            print(error_msg)
            import traceback

            traceback.print_exc()
            QMessageBox.critical(self, "Error", error_msg)
            self.multi_page_label.setText("Multi-page support: Error loading templates")
            self.multi_page_label.setStyleSheet("color: red;")
    
    def process_files(self):
        """Process selected PDF files with the selected template"""
        # Validate files and template selection
        if not self.pdf_files:
            QMessageBox.warning(self, "Warning", "Please add PDF files first")
            return

        template_id = self.get_selected_template_id()
        if not template_id:
            QMessageBox.warning(self, "Warning", "Please select a template")
            return

        # Reset counters and displays
        self.status_label.setText("Processing files...")
        self.results_table.setRowCount(0)
        self.processed_count.setText("0")
        self.success_count.setText("0")
        self.failed_count.setText("0")
        self.total_rows_count.setText("0")
        self.progress_bar.setMaximum(len(self.pdf_files))
        self.progress_bar.setValue(0)
        
        # Reset stop flag and show stop button
        self.should_stop = False
        self.stop_button.setVisible(True)
        
        # Start the timer
        self.start_time = time.time()
        self.processing_time_timer = QTimer(self)
        self.processing_time_timer.timeout.connect(self.update_processing_time)
        self.processing_time_timer.start(1000)  # Update every second

        try:
            # Initialize counters for summary statistics
            processed_count = 0
            success_count = 0
            failed_count = 0
            total_rows = 0
            
            # Process each PDF file
            for index, pdf_path in enumerate(self.pdf_files):
                # Check if processing should stop
                if self.should_stop:
                    self.status_label.setText("Processing stopped by user")
                    break
                    
                print(
                    f"\nProcessing file {index + 1}/{len(self.pdf_files)}: {pdf_path}"
                )
                self.status_label.setText(f"Processing: {os.path.basename(pdf_path)}")

                try:
                    # Get actual PDF page count first
                    with fitz.open(pdf_path) as pdf:
                        actual_page_count = len(pdf)

                    # Extract tables from the PDF
                    results = self.extract_invoice_tables(pdf_path, template_id)

                    processed_count += 1
                    self.processed_count.setText(str(processed_count))
                    
                    if results:
                        # Get template_type from the selected template name
                        template_display_text = self.template_combo.currentText()
                        template_type = "single"  # Default
                        if "Multi" in template_display_text:
                            template_type = "multi"
                        
                        # Get the overall extraction status
                        extraction_status = results.get("extraction_status", {})
                        overall_status = extraction_status.get("overall", "failed")
                        
                        # Store the results with correct page count and template type
                        self.processed_data[pdf_path] = {
                            "pdf_page_count": actual_page_count,  # Use actual page count from PDF
                            "template_type": template_type,  # Add template type
                            "header": results.get("header_tables", []),
                            "items": results.get("items_tables", []),
                            "summary": results.get("summary_tables", []),
                            "extraction_status": extraction_status  # Add extraction status
                        }

                        # Add to results table with correct counts
                        row = self.results_table.rowCount()
                        self.results_table.insertRow(row)

                        # File name
                        file_item = QTableWidgetItem(os.path.basename(pdf_path))
                        self.results_table.setItem(row, 0, file_item)

                        # Determine success status based on extraction_status
                        header_count = sum(
                            len(df)
                            for df in results.get("header_tables", [])
                            if df is not None and not df.empty
                        )
                        item_count = sum(
                            len(df)
                            for df in results.get("items_tables", [])
                            if df is not None and not df.empty
                        )
                        summary_count = sum(
                            len(df)
                            for df in results.get("summary_tables", [])
                            if df is not None and not df.empty
                        )
                        
                        # Set status based on overall extraction status
                        if overall_status == "success":
                            status_text = "Success"
                            status_type = "success"
                            # Update success counter
                            success_count += 1
                            self.success_count.setText(str(success_count))
                        elif overall_status == "partial":
                            # Create a more detailed status message
                            partial_sections = []
                            if extraction_status.get("header") in ["success", "partial"]:
                                partial_sections.append("Header")
                            if extraction_status.get("items") in ["success", "partial"]:
                                partial_sections.append("Items")
                            if extraction_status.get("summary") in ["success", "partial"]:
                                partial_sections.append("Summary")
                            
                            status_text = f"Partial: {', '.join(partial_sections)}"
                            status_type = "partial"
                            # Update success counter but also track as partial
                            success_count += 1
                            self.success_count.setText(str(success_count))
                        else:
                            # Try to determine why it failed
                            if actual_page_count == 0:
                                status_text = "Failed: Could not read PDF"
                            elif not any([header_count, item_count, summary_count]):
                                status_text = "Failed: No data extracted"
                            else:
                                status_text = "Failed: Extraction errors"
                            
                            status_type = "failed"
                            # Update failed counter
                            failed_count += 1
                            self.failed_count.setText(str(failed_count))

                        status_item = QTableWidgetItem(status_text)
                        status_item.setData(Qt.UserRole, status_type)
                        self.results_table.setItem(row, 1, status_item)
                        
                        # PDF Pages - Use actual page count
                        self.results_table.setItem(
                            row, 2, QTableWidgetItem(str(actual_page_count))
                        )

                        # Header Rows - sum of rows in all header tables
                        self.results_table.setItem(
                            row, 3, QTableWidgetItem(str(header_count))
                        )

                        # Item Rows - sum of rows in all item tables
                        self.results_table.setItem(
                            row, 4, QTableWidgetItem(str(item_count))
                        )

                        # Summary Rows - sum of rows in all summary tables
                        self.results_table.setItem(
                            row, 5, QTableWidgetItem(str(summary_count))
                        )
                        
                        # Update total rows counter
                        file_total_rows = header_count + item_count + summary_count
                        total_rows += file_total_rows
                        self.total_rows_count.setText(str(total_rows))
                    else:
                        # Add error to results table
                        row = self.results_table.rowCount()
                        self.results_table.insertRow(row)
                        self.results_table.setItem(
                            row, 0, QTableWidgetItem(os.path.basename(pdf_path))
                        )
                        
                        status_item = QTableWidgetItem("Failed")
                        status_item.setData(Qt.UserRole, "failed")
                        self.results_table.setItem(row, 1, status_item)
                        
                        # Update failed counter
                        failed_count += 1
                        self.failed_count.setText(str(failed_count))
                        
                        self.results_table.setItem(
                            row, 2, QTableWidgetItem(str(actual_page_count))
                        )  # Still show actual page count
                        self.results_table.setItem(row, 3, QTableWidgetItem("0"))
                        self.results_table.setItem(row, 4, QTableWidgetItem("0"))
                        self.results_table.setItem(row, 5, QTableWidgetItem("0"))

                except Exception as e:
                    print(f"Error processing file {pdf_path}: {str(e)}")
                    import traceback

                    traceback.print_exc()
                    
                    # Try to get page count even if processing failed
                    try:
                        with fitz.open(pdf_path) as pdf:
                            actual_page_count = len(pdf)
                    except:
                        actual_page_count = 0

                    # Add error to results table
                    row = self.results_table.rowCount()
                    self.results_table.insertRow(row)
                    self.results_table.setItem(
                        row, 0, QTableWidgetItem(os.path.basename(pdf_path))
                    )
                    
                    status_item = QTableWidgetItem(f"Error: {str(e)}")
                    status_item.setData(Qt.UserRole, "failed")
                    self.results_table.setItem(row, 1, status_item)
                    
                    # Update processed and failed counters
                    processed_count += 1
                    self.processed_count.setText(str(processed_count))
                    failed_count += 1
                    self.failed_count.setText(str(failed_count))
                    
                    self.results_table.setItem(
                        row, 2, QTableWidgetItem(str(actual_page_count))
                    )
                    self.results_table.setItem(row, 3, QTableWidgetItem("0"))
                    self.results_table.setItem(row, 4, QTableWidgetItem("0"))
                    self.results_table.setItem(row, 5, QTableWidgetItem("0"))

                    # Update progress
                self.progress_bar.setValue(index + 1)
                QApplication.processEvents()  # Keep UI responsive
                
            # Final update of processing time
            self.update_processing_time(is_final=True)
            
            # Hide stop button when done
            self.stop_button.setVisible(False)
            
            # Stop the processing timer
            self.processing_time_timer.stop()

            # Then update the color formatting for status items
            for row in range(self.results_table.rowCount()):
                status_item = self.results_table.item(row, 1)
                if status_item:
                    status_type = status_item.data(Qt.UserRole)
                    if status_type == "success":
                        status_item.setForeground(QColor(self.theme['secondary']))
                        status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    elif status_type == "partial":
                        status_item.setForeground(QColor(self.theme['warning']))
                        status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    elif status_type == "failed":
                        status_item.setForeground(QColor(self.theme['danger']))
                        status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))

            # Then modify the processing completion message and status labels to provide clearer information
            # Update status
            total_files = len(self.pdf_files)
            if success_count == total_files:
                self.status_label.setText("Processing complete: All files processed successfully!")
                self.status_label.setStyleSheet(f"""
                    padding: 4px 8px;
                    border-radius: 4px;
                    background-color: {self.theme['secondary'] + '20'};
                    color: {self.theme['secondary']};
                    font-weight: bold;
                """)
                QMessageBox.information(self, "Success", f"All {total_files} files have been processed successfully.\nTotal time: {self.processing_time_label.text().replace('Total Time: ', '')}")
            elif success_count > 0:
                self.status_label.setText(f"Processing complete: {success_count}/{total_files} files processed successfully")
                self.status_label.setStyleSheet(f"""
                    padding: 4px 8px;
                    border-radius: 4px;
                    background-color: {self.theme['warning'] + '20'};
                    color: {self.theme['warning']};
                    font-weight: bold;
                """)
                QMessageBox.warning(self, "Partial Success", f"{success_count} out of {total_files} files processed successfully.\n{failed_count} files failed.\nTotal time: {self.processing_time_label.text().replace('Total Time: ', '')}")
            else:
                self.status_label.setText("Processing complete: All files failed")
                self.status_label.setStyleSheet(f"""
                    padding: 4px 8px;
                    border-radius: 4px;
                    background-color: {self.theme['danger'] + '20'};
                    color: {self.theme['danger']};
                    font-weight: bold;
                """)
                QMessageBox.critical(self, "Processing Failed", f"All {total_files} files failed to process. Please check logs for details.\nTotal time: {self.processing_time_label.text().replace('Total Time: ', '')}")
                    
        except Exception as e:
            # Final update of processing time
            self.update_processing_time(is_final=True)
            
            # Hide stop button when done
            self.stop_button.setVisible(False)
            
            # Stop the processing timer
            if hasattr(self, 'processing_time_timer'):
                self.processing_time_timer.stop()
                
            print(f"Error in process_files: {str(e)}")
            import traceback

            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}\nTotal time: {self.processing_time_label.text().replace('Total Time: ', '')}")
            self.status_label.setText("Error occurred during processing")
    
    def add_files(self):
        """Add PDF files to the list"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select PDF Files", "", "PDF Files (*.pdf)"
        )
        
        for file in files:
            if file not in self.pdf_files:
                self.pdf_files.append(file)
                self.file_list.addItem(os.path.basename(file))
    
    def clear_files(self):
        """Clear the file list"""
        self.pdf_files.clear()
        self.file_list.clear()
        self.results_table.setRowCount(0)
        self.processed_data.clear()
    
    def export_data(self, section):
        """Export processed data in JSON format"""
        if not self.processed_data:
            QMessageBox.warning(
                self, "Warning", "No processed data available to export"
            )
            return
            
        try:
            # Create export directory if it doesn't exist
            export_dir = "exported_data"
            os.makedirs(export_dir, exist_ok=True)
            
            # Update status
            self.status_label.setText(f"Exporting {section} data...")
            self.status_label.setStyleSheet(f"""
                padding: 4px 8px;
                border-radius: 4px;
                background-color: {self.theme['primary'] + '20'};
                color: {self.theme['primary']};
                font-weight: bold;
            """)
            QApplication.processEvents()  # Ensure UI updates
            
            # Prepare data for export
            export_data = {}

            for pdf_path, data in self.processed_data.items():
                pdf_filename = os.path.basename(pdf_path)
                template_type = data.get("template_type", "single")
                pdf_page_count = data.get("pdf_page_count", 1)

                # Create an entry for this PDF file
                file_data = {
                    "metadata": {
                        "filename": pdf_filename,
                        "page_count": pdf_page_count,
                        "template_type": template_type,
                        "export_date": datetime.now().isoformat(),
                        "template_name": self.template_combo.currentText(),
                    }
                }

                # Process section data based on the template type
                print(f"\nExporting {section} data for {pdf_filename}")
                
                # Check if section exists in data
                if section not in data:
                    print(f"  No {section} data found for this file")
                    file_data[section] = []
                    continue
                    
                section_data = data[section]
                
                # Handle None or empty case
                if section_data is None:
                    print(f"  {section} data is None")
                    file_data[section] = []
                    continue

                # Handle case where data is a list of dataframes (multiple tables)
                if isinstance(section_data, list):
                    print(f"  Processing list of {len(section_data)} table(s)")
                        # Create a combined dictionary with table indexes
                    tables_dict = {}
                    valid_tables = 0
                    
                    for i, df in enumerate(section_data):
                        try:
                            if df is None:
                                print(f"  Table {i} is None, skipping")
                                continue
                                
                            # Convert string to DataFrame if needed
                            if isinstance(df, str):
                                print(f"  Table {i} is a string, converting to DataFrame")
                                df = pd.DataFrame([{"text": df}])

                            if df.empty:
                                print(f"  Table {i} is empty, skipping")
                                continue
                                
                            valid_tables += 1
                            # Check if dataframe has page information
                            if "pdf_page" in df.columns:
                                print(f"  Table {i} has page information, grouping by page")
                                # Group by page
                                page_data = {}
                                for page_num, page_df in df.groupby("pdf_page"):
                                    page_num_int = int(page_num)
                                    page_df = page_df.drop(columns=["pdf_page"])
                                    page_data[f"page_{page_num_int}"] = page_df.to_dict(orient="records")
                                    print(f"    Page {page_num_int}: {len(page_df)} rows")
                                tables_dict[f"table_{i}"] = page_data
                            else:
                                # Single page data
                                print(f"  Table {i}: {len(df)} rows (no page info)")
                                tables_dict[f"table_{i}"] = df.to_dict(orient="records")
                        except Exception as e:
                            print(f"  Error processing table {i}: {str(e)}")
                            import traceback
                            traceback.print_exc()

                    print(f"  Processed {valid_tables} valid tables")
                    file_data[section] = tables_dict

                else:
                    # Regular case - single dataframe or string
                    try:
                        if isinstance(section_data, str):
                            print(f"  {section} data is a string, converting to DataFrame")
                            section_data = pd.DataFrame([{"text": section_data}])
                        
                        if not hasattr(section_data, 'empty'):
                            print(f"  {section} data is not a DataFrame, converting")
                            # Try to convert to DataFrame if possible
                            try:
                                section_data = pd.DataFrame(section_data)
                            except:
                                print(f"  Cannot convert {section} data to DataFrame")
                                file_data[section] = [{"error": "Data format error"}]
                                continue

                        if section_data.empty:
                            print(f"  {section} DataFrame is empty")
                            file_data[section] = []
                            continue
                            
                        rows = len(section_data)
                        cols = len(section_data.columns)
                        print(f"  {section} DataFrame has {rows} rows and {cols} columns")

                        # Check if multi-page processing is needed
                        if "pdf_page" in section_data.columns and template_type == "multi":
                            print(f"  Multi-page processing for {section}")
                            # Group by page
                            page_data = {}
                            for page_num, page_df in section_data.groupby("pdf_page"):
                                page_num_int = int(page_num)
                                page_df = page_df.drop(columns=["pdf_page"])
                                page_data[f"page_{page_num_int}"] = page_df.to_dict(orient="records")
                                print(f"    Page {page_num_int}: {len(page_df)} rows")
                            file_data[section] = page_data
                        else:
                            # Single page data
                            if "pdf_page" in section_data.columns:
                                print(f"  Removing pdf_page column")
                                section_data = section_data.drop(columns=["pdf_page"])
                            print(f"  Exporting as single-page data: {len(section_data)} rows")
                            file_data[section] = section_data.to_dict(orient="records")
                    except Exception as e:
                        print(f"  Error processing {section} data: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        file_data[section] = [{"error": str(e)}]

                # Add the file data to the export
                export_data[pdf_filename] = file_data
            
            # Save to JSON file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{export_dir}/{section}_data_{timestamp}.json"
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            # Reset status label to normal
            self.status_label.setText(f"Exported {section} data successfully")
            self.status_label.setStyleSheet(f"""
                padding: 4px 8px;
                border-radius: 4px;
                background-color: {self.theme['secondary'] + '20'};
                color: {self.theme['secondary']};
                font-weight: bold;
            """)
            
            # Create a custom success message box
            success_box = QMessageBox(self)
            success_box.setWindowTitle("Export Successful")
            success_box.setIcon(QMessageBox.Information)
            
            # Calculate total rows exported
            total_exported_rows = 0
            total_exported_files = len(export_data)
            
            for file_data in export_data.values():
                section_content = file_data.get(section, {})
                if isinstance(section_content, list):
                    total_exported_rows += len(section_content)
                elif isinstance(section_content, dict):
                    for table_data in section_content.values():
                        if isinstance(table_data, list):
                            total_exported_rows += len(table_data)
                        elif isinstance(table_data, dict):
                            for page_data in table_data.values():
                                if isinstance(page_data, list):
                                    total_exported_rows += len(page_data)
            
            success_box.setText(f"Data exported successfully to")
            success_box.setInformativeText(
                f"<b>File:</b> {filename}<br><br>"
                f"<b>Export details:</b><br>"
                f"• Section: <b>{section.title()}</b><br>"
                f"• Files: <b>{total_exported_files}</b><br>"
                f"• Rows: <b>{total_exported_rows}</b><br>"
            )
            
            # Open folder button
            open_folder_btn = success_box.addButton("Open Folder", QMessageBox.ActionRole)
            open_folder_btn.clicked.connect(lambda: os.startfile(os.path.abspath(export_dir)))
            
            # OK button
            ok_btn = success_box.addButton(QMessageBox.Ok)
            ok_btn.setDefault(True)
            
            success_box.exec()
            
        except Exception as e:
            self.status_label.setText("Export error")
            self.status_label.setStyleSheet(f"""
                padding: 4px 8px;
                border-radius: 4px;
                background-color: {self.theme['danger'] + '20'};
                color: {self.theme['danger']};
                font-weight: bold;
            """)
            
            QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")
            import traceback

            traceback.print_exc()
    
    def navigate_back(self):
        """Return to the main screen"""
        self.go_back.emit()  # Emit the signal for parent to handle
        print("Emitted go_back signal")
    
    def reset_screen(self):
        """Reset the screen to its initial state"""
        # Clear all data
        self.pdf_files.clear()
        self.file_list.clear()
        self.results_table.setRowCount(0)
        self.processed_data.clear()
        
        # Reset progress bar
        self.progress_bar.setValue(0)
        
        # Reset status label
        self.status_label.setText("Ready")
        
        # Reset processing time label
        self.processing_time_label.setText("")
        self.start_time = None
        
        # Stop any running timer
        if hasattr(self, 'processing_time_timer') and self.processing_time_timer.isActive():
            self.processing_time_timer.stop()
        
        # Reset extraction statistics summary values
        self.processed_count.setText("0")
        self.success_count.setText("0")
        self.failed_count.setText("0")
        self.total_rows_count.setText("0")
        
        # Reset template selection if needed
        if self.template_combo.count() > 0:
            self.template_combo.setCurrentIndex(0)
        
        # Show confirmation message
        QMessageBox.information(
            self, "Screen Reset", "The screen has been reset to its initial state."
        )
    
    def clean_dataframe(self, df, section, config):
        """Clean DataFrame using regex patterns to identify table boundaries and filter unwanted rows"""
        if df is None or df.empty:
            return df
        
        # Get regex patterns from config
        regex_patterns = config.get("regex_patterns", {}).get(section, {})
        start_pattern = regex_patterns.get("start", None)
        end_pattern = regex_patterns.get("end", None)
        skip_pattern = regex_patterns.get("skip", None)
        
        print(f"Cleaning {section} DataFrame with patterns:")
        print(f"  Start pattern: {start_pattern}")
        print(f"  End pattern: {end_pattern}")
        print(f"  Skip pattern: {skip_pattern}")
        
        # Convert DataFrame to string for easier regex matching
        str_df = df.astype(str)
        
        # Apply boundary detection if patterns are provided
        if start_pattern or end_pattern:
            start_idx = None
            end_idx = None
            
            # Find start index based on pattern
            if start_pattern:
                for idx, row in str_df.iterrows():
                    row_text = " ".join(row.values)
                    if re.search(start_pattern, row_text, re.IGNORECASE):
                        start_idx = idx
                        print(
                            f"  Found start row at index {start_idx}: {row_text[:50]}..."
                        )
                        break
                
                # If start pattern is specified but not found, return empty DataFrame
                if start_idx is None:
                    print(f"  Start pattern '{start_pattern}' not found in the data")
                    return pd.DataFrame()
            else:
                # If no start pattern, start from the beginning
                start_idx = 0
            
            # Find end index based on pattern
            if end_pattern:
                for idx, row in str_df.loc[start_idx:].iterrows():
                    row_text = " ".join(row.values)
                    if re.search(end_pattern, row_text, re.IGNORECASE):
                        end_idx = idx
                        print(f"  Found end row at index {end_idx}: {row_text[:50]}...")
                        break
                
                # If end pattern is specified but not found, use the last row
                if end_idx is None:
                    end_idx = df.index[-1]
                    print(
                        f"  End pattern '{end_pattern}' not found, using last row at index {end_idx}"
                    )
            else:
                # If no end pattern, end at the last row
                end_idx = df.index[-1]
            
            # Slice DataFrame to keep only rows between boundaries (inclusive)
            df = df.loc[start_idx:end_idx]
            print(f"  Applied boundary detection: {len(df)} rows remaining")
        
        # Filter out rows matching skip pattern
        if skip_pattern:
            before_count = len(df)
            df = df[
                ~str_df.apply(
                    lambda row: bool(
                        re.search(skip_pattern, " ".join(row.values), re.IGNORECASE)
                    ),
                    axis=1,
                )
            ]
            skipped = before_count - len(df)
            print(f"  Skipped {skipped} rows matching pattern")
        
        # Basic cleaning - remove empty rows/columns and whitespace
        df = df.replace(r"^\s*$", pd.NA, regex=True)
        df = df.dropna(how="all")
        df = df.dropna(axis=1, how="all")
        
        # Clean string values
        for col in df.columns:
            if df[col].dtype == object:  # Only clean string columns
                df[col] = df[col].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
        
        print(f"  Final DataFrame size: {len(df)} rows, {len(df.columns)} columns")
        return df

    def extract_invoice_tables(self, pdf_path, template_id):
        try:
            print("\n" + "=" * 80)
            print(f"STEP 1: DATABASE CONNECTION AND TEMPLATE RETRIEVAL")
            print("=" * 80)

            # Connect to database
            print("Connecting to database: 'invoice_templates.db'")
            conn = sqlite3.connect("invoice_templates.db")
            cursor = conn.cursor()

            # Fetch template data
            cursor.execute(
                """
                SELECT id, name, description, template_type, regions, column_lines, config, creation_date,
                       page_count, page_regions, page_column_lines, page_configs
                FROM templates WHERE id = ?
            """,
                (template_id,),
            )
            template = cursor.fetchone()

            if not template:
                raise Exception(f"Template with ID {template_id} not found")

            # Extract template data
            template_data = {
                "id": template[0],
                "name": template[1],
                "description": template[2],
                "template_type": template[3],
                "regions": json.loads(template[4]),
                "column_lines": json.loads(template[5]),
                "config": json.loads(template[6]),
                "creation_date": template[7],
                "page_count": template[8] if template[8] else 1,
            }

            # Load multi-page data if available
            if template[9]:  # page_regions
                template_data["page_regions"] = json.loads(template[9])

            if template[10]:  # page_column_lines
                template_data["page_column_lines"] = json.loads(template[10])

            if template[11]:  # page_configs
                template_data["page_configs"] = json.loads(template[11])

            # Close database connection
            conn.close()

            print("\n" + "=" * 80)
            print(f"STEP 2: PDF DOCUMENT LOADING")
            print("=" * 80)

            # Load the PDF document
            print(f"Loading PDF document: {pdf_path}")
            pdf_document = fitz.open(pdf_path)
            pdf_page_count = len(pdf_document)
            print(f"✓ PDF document loaded successfully with {pdf_page_count} pages")

            print("\n" + "=" * 80)
            print(f"STEP 3: TABLE EXTRACTION")
            print("=" * 80)

            # Initialize results dictionary with extraction statuses
            results = {
                "header_tables": [],
                "items_tables": [],
                "summary_tables": [],
                "extraction_status": {
                    "header": "not_processed",
                    "items": "not_processed",
                    "summary": "not_processed",
                    "overall": "not_processed"
                }
            }

            # Get config parameters
            config = template_data.get("config", {})

            # Get middle page settings for multi-page templates
            use_middle_page = False
            fixed_page_count = False

            if template_data["template_type"] == "multi":
                # For multi-page templates, check if it uses middle page pattern or fixed pages
                if "use_middle_page" in config:
                    use_middle_page = config.get("use_middle_page", False)

                if "fixed_page_count" in config:
                    fixed_page_count = config.get("fixed_page_count", False)

                print(f"Multi-page template settings:")
                print(f"  Use middle page: {use_middle_page}")
                print(f"  Fixed page count: {fixed_page_count}")

            # Determine which pages to process
            pages_to_process = []

            if template_data["template_type"] == "single":
                # For single-page templates, only process the first page
                pages_to_process = [0]  # First page
            else:
                # For multi-page templates
                if fixed_page_count:
                    # Use all pages defined in the template
                    template_page_count = template_data.get("page_count", 1)
                    pages_to_process = list(
                        range(min(template_page_count, pdf_page_count))
                    )
                elif use_middle_page:
                    # Special handling for middle page templates
                    if pdf_page_count == 1:
                        # If only one page, apply both first and last page regions
                        pages_to_process = [
                            0
                        ]  # Process the single page as both first and last
                    else:
                        # Process first, middle (if exists), and last pages
                        pages_to_process = [0]  # First page

                        if pdf_page_count > 2:
                            # Add middle page(s) if more than 2 pages
                            middle_pages = list(range(1, pdf_page_count - 1))
                            pages_to_process.extend(middle_pages)

                        pages_to_process.append(pdf_page_count - 1)  # Last page
                else:
                    # Standard multi-page: process all pages up to template defined count
                    template_page_count = template_data.get("page_count", 1)
                    pages_to_process = list(
                        range(min(template_page_count, pdf_page_count))
                    )

            print(f"Pages to process: {[p+1 for p in pages_to_process]}")

            # Process each selected page
            for page_index in pages_to_process:
                print(f"\nProcessing page {page_index + 1}/{pdf_page_count}")

                try:
                    # Get the current page
                    page = pdf_document[page_index]

                    # Get regions and column lines for current page
                    current_regions = {}
                    current_column_lines = {}

                    if template_data["template_type"] == "multi":
                        # Handle multi-page templates
                        page_regions = template_data.get("page_regions", [])
                        page_column_lines = template_data.get("page_column_lines", [])

                        if fixed_page_count:
                            # For fixed page templates, use the exact page index
                            if page_index < len(page_regions):
                                current_regions = page_regions[page_index]
                                if page_index < len(page_column_lines):
                                    current_column_lines = page_column_lines[page_index]
                            else:
                                print(
                                    f"Warning: No template data for page {page_index + 1}"
                                )
                                continue

                        elif use_middle_page:
                            # For middle page templates, select regions based on position
                            if pdf_page_count == 1:
                                # For single page PDFs with middle page template,
                                # combine first and last page regions
                                if len(page_regions) >= 1:
                                    # Add all regions from first page
                                    first_page_regions = page_regions[0]
                                    for section in ["header", "items", "summary"]:
                                        if section in first_page_regions:
                                            current_regions[section] = (
                                                first_page_regions.get(section, [])
                                            )

                                if len(page_regions) >= 3:
                                    # Add any additional regions from last page
                                    last_page_regions = page_regions[2]
                                    for section in ["header", "items", "summary"]:
                                        if section in last_page_regions:
                                            if section not in current_regions:
                                                current_regions[section] = []
                                            current_regions[section].extend(
                                                last_page_regions.get(section, [])
                                            )

                                # Combine column lines similarly
                                if len(page_column_lines) >= 1:
                                    first_page_cols = page_column_lines[0]
                                    for section in ["header", "items", "summary"]:
                                        if section in first_page_cols:
                                            current_column_lines[section] = (
                                                first_page_cols.get(section, [])
                                            )

                                if len(page_column_lines) >= 3:
                                    last_page_cols = page_column_lines[2]
                                    for section in ["header", "items", "summary"]:
                                        if section in last_page_cols:
                                            if section not in current_column_lines:
                                                current_column_lines[section] = []
                                            current_column_lines[section].extend(
                                                last_page_cols.get(section, [])
                                            )
                            else:
                                # Multi-page PDF with middle page template
                                if page_index == 0 and len(page_regions) >= 1:
                                    # First page
                                    current_regions = page_regions[0]
                                    if len(page_column_lines) >= 1:
                                        current_column_lines = page_column_lines[0]
                                elif page_index == pdf_page_count - 1 and len(page_regions) >= 3:
                                    # Last page
                                    current_regions = page_regions[2]
                                    if len(page_column_lines) >= 3:
                                        current_column_lines = page_column_lines[2]
                                elif len(page_regions) >= 2:
                                    # Middle page(s)
                                    current_regions = page_regions[1]
                                    if len(page_column_lines) >= 2:
                                        current_column_lines = page_column_lines[1]

                        else:
                            # Standard multi-page template
                            if page_index < len(page_regions):
                                current_regions = page_regions[page_index]
                                if page_index < len(page_column_lines):
                                    current_column_lines = page_column_lines[page_index]
                            else:
                                print(
                                    f"Warning: No template data for page {page_index + 1}"
                                )
                                continue

                    else:
                        # For single page templates
                        current_regions = template_data.get("regions", {})
                        current_column_lines = template_data.get("column_lines", {})
                        
                        # Debug column lines for single page templates
                        print(f"\nSingle-page template column lines:")
                        for section, lines in current_column_lines.items():
                            print(f"  {section}: {len(lines)} column lines")
                            if lines and len(lines) > 0:
                                print(f"    First column line format: {type(lines[0])}")
                                print(f"    Sample: {lines[0]}")
                        
                        # Verify column_lines structure - it should be a dict with sections as keys
                        if not isinstance(current_column_lines, dict):
                            print(f"  WARNING: column_lines is not a dict: {type(current_column_lines)}")
                            # Try to fix it - common issue is an array with a single entry
                            if isinstance(current_column_lines, list) and len(current_column_lines) > 0:
                                print(f"  Attempting to fix column_lines format (found list with {len(current_column_lines)} entries)")
                                # Use the first item if it's a dict
                                if isinstance(current_column_lines[0], dict):
                                    current_column_lines = current_column_lines[0]
                                    print(f"  Fixed column_lines to use first entry: {type(current_column_lines)}")

                    # Debug the regions we're using
                    print(f"Using regions format: {type(current_regions)}")
                    if current_regions:
                        for section, regions in current_regions.items():
                            print(f"  {section}: {len(regions)} region(s)")
                            if regions:
                                print(f"    First region type: {type(regions[0])}")

                    # Process each section (header, items, summary)
                    for section in ["header", "items", "summary"]:
                        if section in current_regions and current_regions[section]:
                            section_regions = current_regions[section]
                            section_column_lines = current_column_lines.get(section, [])
                            
                            print(
                                f"\nExtracting {section} section from page {page_index + 1}"
                            )
                            print(f"  Found {len(section_regions)} region(s)")
                            print(f"  Found {len(section_column_lines)} column line(s)")
                            
                            # Ensure section_column_lines is a list
                            if not isinstance(section_column_lines, list):
                                print(f"  WARNING: section_column_lines is not a list: {type(section_column_lines)}")
                                if isinstance(section_column_lines, dict):
                                    # Try to convert dict to list
                                    section_column_lines = [section_column_lines]
                                    print(f"  Converted dict to list with 1 item")
                                else:
                                    # Initialize as empty list as fallback
                                    section_column_lines = []
                                    print(f"  Reset to empty list as fallback")

                            # Get table extraction parameters
                            table_areas = []
                            columns_list = []

                            for region_idx, region in enumerate(section_regions):
                                # Handle different region formats
                                if isinstance(region, dict):
                                    # Format from single page viewer: {x1, y1, x2, y2}
                                    x1 = region.get("x1", 0)
                                    y1 = region.get("y1", 0)
                                    x2 = region.get("x2", 0)
                                    y2 = region.get("y2", 0)
                                elif isinstance(region, list) and len(region) >= 2:
                                    # Format from multi-page viewer: [{x,y}, {x,y}]
                                    x1 = region[0].get("x", 0)
                                    y1 = region[0].get("y", 0)
                                    x2 = region[1].get("x", 0)
                                    y2 = region[1].get("y", 0)
                                else:
                                    print(f"  Warning: Unrecognized region format: {region}")
                                    continue

                                # Create table area string
                                table_area = f"{x1},{y1},{x2},{y2}"
                                table_areas.append(table_area)
                                
                                # Process column lines for this region
                                region_columns = []
                                
                                # Debug all column lines for this section
                                print(f"  Processing column lines for region {region_idx} in {section} section")
                                print(f"  Column lines count: {len(section_column_lines)}")
                                print(f"  Column lines type: {type(section_column_lines)}")
                                
                                # Fix for single page templates: check structure of column lines
                                if len(section_column_lines) == 0 and template_data["template_type"] == "single":
                                    print(f"  WARNING: No column lines found for {section} section in single page template")
                                    print(f"  Template data column_lines structure: {type(template_data.get('column_lines', {}))}")
                                    
                                    # Try to directly access the column lines from the template data
                                    all_column_lines = template_data.get("column_lines", {})
                                    if isinstance(all_column_lines, dict) and section in all_column_lines:
                                        direct_section_column_lines = all_column_lines.get(section, [])
                                        if direct_section_column_lines:
                                            print(f"  Found {len(direct_section_column_lines)} column lines directly in template data")
                                            section_column_lines = direct_section_column_lines
                                            print(f"  First entry type: {type(direct_section_column_lines[0])}")
                                    
                                    # Also check if column_lines might be an array itself (format inconsistency)
                                    if isinstance(all_column_lines, list) and len(all_column_lines) > 0:
                                        print(f"  Column lines is a list with {len(all_column_lines)} entries")
                                        # Use the first entry for single page templates
                                        if isinstance(all_column_lines[0], dict) and section in all_column_lines[0]:
                                            first_page_column_lines = all_column_lines[0].get(section, [])
                                            if first_page_column_lines:
                                                print(f"  Found {len(first_page_column_lines)} column lines in first page entry")
                                                section_column_lines = first_page_column_lines
                                
                                for line in section_column_lines:
                                    # Handle different column line formats
                                    if isinstance(line, list):
                                        if len(line) >= 3 and line[2] == region_idx:
                                            x_val = line[0].get("x", 0)
                                            region_columns.append(x_val)
                                            print(f"    Using column at x={x_val} (matched region_idx={region_idx})")
                                        elif len(line) == 2:
                                            # Format without region index: [{x,y}, {x,y}]
                                            x_val = line[0].get("x", 0)
                                            region_columns.append(x_val)
                                            print(f"    Using column at x={x_val} (list format)")
                                    elif isinstance(line, dict):
                                        # Try different known formats
                                        if "x" in line:
                                            # Direct format: {x, y}
                                            x_val = line.get("x", 0)
                                            region_columns.append(x_val)
                                            print(f"    Using column at x={x_val} (dict format with x key)")
                                        elif "x1" in line:
                                            # Rectangle format: {x1, y1, x2, y2}
                                            x_val = line.get("x1", 0)
                                            region_columns.append(x_val)
                                            print(f"    Using column at x={x_val} (dict format with x1 key)")
                                        elif "value" in line and isinstance(line["value"], (int, float)):
                                            # Value format: {value: 123}
                                            x_val = line["value"]
                                            region_columns.append(x_val)
                                            print(f"    Using column at x={x_val} (dict format with value key)")
                                        elif "position" in line:
                                            # Position format: {position: 123}
                                            x_val = line["position"]
                                            region_columns.append(x_val)
                                            print(f"    Using column at x={x_val} (dict format with position key)")
                                        else:
                                            # Unknown dict format, try to extract any numeric value
                                            print(f"    Unknown dict format: {line}")
                                            for key, val in line.items():
                                                if isinstance(val, (int, float)):
                                                    print(f"    Using numeric value {val} from key '{key}'")
                                                    region_columns.append(val)
                                                    break
                                    elif isinstance(line, (int, float)):
                                        # Direct numeric value
                                        region_columns.append(line)
                                        print(f"    Using direct numeric value: x={line}")
                                    else:
                                        print(f"    Unsupported column line format: {type(line)}, value: {line}")
                                        # Try to extract a numeric value if it's a string
                                        if isinstance(line, str):
                                            try:
                                                numeric_val = float(line)
                                                region_columns.append(numeric_val)
                                                print(f"    Converted string to numeric value: x={numeric_val}")
                                            except ValueError:
                                                print(f"    Could not convert string to numeric value")

                                # Format column lines
                                col_str = (
                                    ",".join([str(x) for x in sorted(region_columns)])
                                    if region_columns
                                    else ""
                                )
                                columns_list.append(col_str)

                            # Handle special case for items section with multiple regions
                            if section == "items" and len(table_areas) > 1:
                                print(f"  Combining multiple item regions into one ({len(table_areas)} regions)")

                                # Parse all coordinates
                                area_coords = []
                                for area in table_areas:
                                    coords = [float(c) for c in area.split(",")]
                                    area_coords.append(coords)

                                # Find bounding box
                                x_coords = [c[0] for c in area_coords] + [
                                    c[2] for c in area_coords
                                ]
                                y_coords = [c[1] for c in area_coords] + [
                                    c[3] for c in area_coords
                                ]

                                x1 = min(x_coords)
                                y1 = min(y_coords)
                                x2 = max(x_coords)
                                y2 = max(y_coords)

                                # Replace with combined area
                                combined_area = f"{x1},{y1},{x2},{y2}"
                                table_areas = [combined_area]
                                print(f"  Combined area: {combined_area}")

                                # Combine column lines with deduplication
                                all_columns = set()  # Use set for deduplication
                                for col_str in columns_list:
                                    if col_str:
                                        for col in col_str.split(","):
                                            all_columns.add(float(col))
                                
                                # Convert back to list and sort
                                all_columns_list = sorted(list(all_columns))
                                
                                # Remove columns that are too close to each other (within 5 pixels)
                                if len(all_columns_list) > 1:
                                    deduplicated_columns = [all_columns_list[0]]
                                    for i in range(1, len(all_columns_list)):
                                        if all_columns_list[i] - deduplicated_columns[-1] >= 5:  # 5 pixel threshold
                                            deduplicated_columns.append(all_columns_list[i])
                                    all_columns_list = deduplicated_columns
                                
                                # Format as string
                                col_str = ",".join([str(x) for x in all_columns_list]) if all_columns_list else ""
                                columns_list = [col_str]
                                print(f"  Combined columns: {col_str}")

                            # Set extraction parameters from config
                            extraction_params = {}
                            # Check if we have extraction_params in the config
                            if "extraction_params" in config:
                                extraction_params = config["extraction_params"]
                                print(f"  Found extraction_params in config")
                            else:
                                print(
                                    f"  WARNING: No extraction_params found in config, using direct config values"
                                )

                            # Get section-specific parameters
                            section_params = {}
                            if section in extraction_params:
                                section_params = extraction_params.get(section, {})
                                print(
                                    f"  Found section-specific parameters for {section}"
                                )

                            # Extract row_tol with proper fallbacks
                            row_tol = section_params.get("row_tol", None)
                            if row_tol is not None:
                                print(
                                    f"  Using row_tol={row_tol} from extraction_params.{section}"
                                )
                            else:
                                # If not in section_params, check direct section config
                                section_config = config.get(section, {})
                                row_tol = section_config.get("row_tol", None)
                                if row_tol is not None:
                                    print(
                                        f"  Using row_tol={row_tol} from config.{section}"
                                    )
                                else:
                                    # If not in direct section config, check global config
                                    row_tol = config.get("row_tol", None)
                                if row_tol is not None:
                                    print(f"  Using global row_tol={row_tol}")
                                else:
                                    # STRICT MODE: Raise error instead of using default
                                    error_msg = f"ERROR: No row_tol defined for {section} in database config"
                                    print(f"  ❌ {error_msg}")
                                    raise ValueError(error_msg)

                            # Get other extraction parameters with fallbacks
                            split_text = extraction_params.get(
                                "split_text", config.get("split_text", True)
                            )
                            strip_text = extraction_params.get(
                                "strip_text", config.get("strip_text", "\n")
                            )
                            flavor = extraction_params.get(
                                "flavor", config.get("flavor", "stream")
                            )
                            print(f"  Extraction parameters for {section}:")
                            print(f"    Table areas: {table_areas}")
                            print(f"    Columns: {columns_list}")
                            print(f"    Row tolerance: {row_tol} (from database)")

                            # Extract tables for this section
                            for i, (table_area, columns) in enumerate(zip(table_areas, columns_list)):
                                try:
                                    params = {
                                        "pages": str(page_index + 1),
                                        "table_areas": [table_area],
                                        "columns": [columns] if columns else None,
                                        "split_text": split_text,
                                        "strip_text": strip_text,
                                        "flavor": flavor,
                                        "row_tol": row_tol,
                                        "parallel": True
                                    }

                                    # Extract table using pypdf_table_extraction
                                    table_result = pypdf_table_extraction.read_pdf(
                                        pdf_path, **params
                                    )

                                    if (table_result and len(table_result) > 0 and hasattr(table_result[0], "df")):
                                        table_df = table_result[0].df

                                        if table_df is not None and not table_df.empty:
                                            # Add page number to the dataframe
                                            table_df["pdf_page"] = page_index + 1

                                            # Basic cleaning
                                            table_df = table_df.replace(
                                                r"^\s*$", pd.NA, regex=True
                                            )
                                            table_df = table_df.dropna(how="all")
                                            table_df = table_df.dropna(
                                                axis=1, how="all"
                                            )

                                            # Find applicable regex patterns, if any
                                            regex_patterns = None

                                            # Check for section-specific regex patterns
                                            if (
                                                template_data["template_type"]
                                                == "multi"
                                                and "page_configs" in template_data
                                            ):
                                                # For multi-page templates, check page-specific config first
                                                if page_index < len(
                                                    template_data.get(
                                                        "page_configs", []
                                                    )
                                                ):
                                                    page_config = template_data[
                                                        "page_configs"
                                                    ][page_index]
                                                    if (
                                                        section in page_config
                                                        and "regex_patterns"
                                                        in page_config[section]
                                                    ):
                                                        regex_patterns = page_config[
                                                            section
                                                        ]["regex_patterns"]
                                                        print(
                                                            f"  Found page-specific regex patterns for {section}"
                                                        )

                                            # If no page-specific patterns, check section config
                                            if (
                                                regex_patterns is None
                                                and section in config
                                            ):
                                                section_config = config[section]
                                                if "regex_patterns" in section_config:
                                                    regex_patterns = section_config[
                                                        "regex_patterns"
                                                    ]
                                                    print(
                                                        f"  Found section-specific regex patterns for {section}"
                                                    )

                                            # As a fallback, check global regex patterns
                                            if (
                                                regex_patterns is None
                                                and "regex_patterns" in config
                                            ):
                                                if section in config["regex_patterns"]:
                                                    regex_patterns = config[
                                                        "regex_patterns"
                                                    ][section]
                                                    print(
                                                        f"  Found global regex patterns for {section}"
                                                    )

                                            # Apply regex patterns only if defined and contain at least one valid pattern
                                            if regex_patterns:
                                                # Check if there's at least one non-None pattern
                                                has_valid_pattern = False
                                                for pattern_type in [
                                                    "start",
                                                    "end",
                                                    "skip",
                                                ]:
                                                    if (
                                                        pattern_type in regex_patterns
                                                        and regex_patterns[pattern_type]
                                                    ):
                                                        has_valid_pattern = True
                                                        break

                                                if has_valid_pattern:
                                                    print(
                                                        f"  Applying regex patterns to {section} table"
                                                    )
                                                    
                                                    # Save original row count for comparison
                                                    orig_rows = len(table_df)
                                                    
                                                    # Apply patterns
                                                    table_df, regex_status = self.apply_regex_to_dataframe(
                                                        table_df, regex_patterns
                                                    )
                                                    
                                                    # Report results with more detailed status information
                                                    if table_df.empty:
                                                        print(f"  ⚠️ All rows filtered out by regex patterns! Reason: {regex_status['reason']}")
                                                    elif regex_status['status'] == 'success':
                                                        filtered_rows = orig_rows - len(table_df)
                                                        print(f"  ✅ Successfully filtered {filtered_rows} rows, kept {len(table_df)} rows")
                                                    elif regex_status['status'] == 'partial':
                                                        filtered_rows = orig_rows - len(table_df)
                                                        print(f"  ⚠️ Partially successful: {regex_status['reason']}, kept {len(table_df)} rows")
                                                    else:
                                                        print(f"  ❌ Regex application issues: {regex_status['reason']}")

                                                    # Store the regex status in the results for later use
                                                    if not hasattr(table_df, 'regex_status'):
                                                        table_df.regex_status = regex_status['status']

                                            else:
                                                print(f"  No regex patterns defined for {section}, using raw extraction")

                                            # Store the table
                                        if not table_df.empty:
                                            if section == "header":
                                                results["header_tables"].append(
                                                    table_df
                                                )
                                                print(
                                                    f"  ✓ Extracted header table with {len(table_df)} rows"
                                                )
                                                # Track extraction status
                                                if hasattr(table_df, 'regex_status'):
                                                    results["extraction_status"]["header"] = table_df.regex_status
                                                elif not table_df.empty:
                                                    results["extraction_status"]["header"] = "success" 
                                                else:
                                                    results["extraction_status"]["header"] = "failed"
                                            elif section == "items":
                                                results["items_tables"].append(
                                                    table_df
                                                )
                                                print(
                                                    f"  ✓ Extracted items table with {len(table_df)} rows"
                                                )
                                                # Track extraction status
                                                if hasattr(table_df, 'regex_status'):
                                                    results["extraction_status"]["items"] = table_df.regex_status
                                                elif not table_df.empty:
                                                    results["extraction_status"]["items"] = "success"
                                                else:
                                                    results["extraction_status"]["items"] = "failed"
                                            else:  # summary
                                                results["summary_tables"].append(
                                                    table_df
                                                )
                                                print(
                                                    f"  ✓ Extracted summary table with {len(table_df)} rows"
                                                )
                                            # Track extraction status
                                            if hasattr(table_df, 'regex_status'):
                                                results["extraction_status"]["summary"] = table_df.regex_status
                                            elif not table_df.empty:
                                                results["extraction_status"]["summary"] = "success"
                                            else:
                                                results["extraction_status"]["summary"] = "failed"
                                        else:
                                            print(f"  ℹ Table is empty after processing")
                                except Exception as e:
                                    print(f"  ✗ Error extracting table: {str(e)}")
                                    import traceback

                                    traceback.print_exc()

                                else:
                                    print(f"No {section} regions defined for page {page_index + 1}")

                except Exception as e:
                    print(f"Error processing page {page_index + 1}: {str(e)}")
                    import traceback
                    traceback.print_exc()

            # Close the PDF document
            pdf_document.close()

            # At the end of processing all pages, update the overall extraction status
            # Update the overall extraction status before returning results
            if results["extraction_status"]["items"] == "success":
                # If items were successfully extracted, that's most important
                results["extraction_status"]["overall"] = "success"
            elif results["extraction_status"]["items"] == "partial" or results["extraction_status"]["header"] == "success" or results["extraction_status"]["summary"] == "success":
                # Partial success if we at least got some data
                results["extraction_status"]["overall"] = "partial"
            else:
                # Failed if nothing was successfully extracted
                results["extraction_status"]["overall"] = "failed"

            print(f"\nExtraction summary:")
            print(f"  Header: {results['extraction_status']['header']}")
            print(f"  Items: {results['extraction_status']['items']}")
            print(f"  Summary: {results['extraction_status']['summary']}")
            print(f"  Overall: {results['extraction_status']['overall']}")

            # Return the results
            return results

        except Exception as e:
            print(f"Error in extract_invoice_tables: {str(e)}")
            import traceback

            traceback.print_exc()
            if "pdf_document" in locals():
                pdf_document.close()
            return None

    def apply_regex_to_dataframe(self, df, regex_patterns):
        """Apply regex patterns to filter and extract relevant rows from DataFrame"""
        if df is None or df.empty:
            print("    ⚠️ DataFrame is None or empty, skipping regex processing")
            return df, {"status": "failed", "reason": "Empty input data"}
        
        if not regex_patterns:
            print("    ⚠️ No regex patterns provided, skipping regex processing")
            return df, {"status": "partial", "reason": "No regex patterns"}

        # Get patterns, checking if each one is defined
        start_pattern = regex_patterns.get("start", None)
        end_pattern = regex_patterns.get("end", None)
        skip_pattern = regex_patterns.get("skip", None)

        # Print original row count
        orig_row_count = len(df)
        print(f"    Starting with {orig_row_count} rows")
        
        # Check for empty strings and set them to None
        if start_pattern == "":
            print("    Start pattern is empty string, treating as None")
            start_pattern = None
        if end_pattern == "":
            print("    End pattern is empty string, treating as None")
            end_pattern = None
        if skip_pattern == "":
            print("    Skip pattern is empty string, treating as None")
            skip_pattern = None

        # Only proceed if at least one pattern is defined and not None
        if not (start_pattern or end_pattern or skip_pattern):
            print("    No valid regex patterns found, returning original DataFrame")
            return df, {"status": "partial", "reason": "No valid regex patterns"}

        print(f"    Applying regex patterns:")
        if start_pattern:
            print(f"    • Start pattern: '{start_pattern}'")
        if end_pattern:
            print(f"    • End pattern: '{end_pattern}'")
        if skip_pattern:
            print(f"    • Skip pattern: '{skip_pattern}'")
        
        # Sample the data to show what we're matching against
        if not df.empty:
            sample_rows = min(3, len(df))
            print(f"    Sample data (first {sample_rows} rows):")
            for i in range(sample_rows):
                row_values = " ".join([str(val) for val in df.iloc[i].values])
                print(f"      Row {i}: {row_values[:100]}...")

        # Convert DataFrame to string for easier regex matching
        try:
            str_df = df.astype(str)
            print("    Converted DataFrame to string for regex matching")
        except Exception as e:
            print(f"    ⚠️ Error converting DataFrame to string: {str(e)}")
            return df, {"status": "partial", "reason": f"Error in conversion: {str(e)}"}

        # Apply boundary detection if patterns are provided
        if start_pattern or end_pattern:
            start_idx = None
            end_idx = None

            # Find start index based on pattern - only if start_pattern is explicitly defined
            if start_pattern:
                try:
                    print(f"    Searching for start pattern '{start_pattern}'...")
                    for idx, row in str_df.iterrows():
                        row_text = " ".join(row.values)
                        if re.search(start_pattern, row_text, re.IGNORECASE):
                            start_idx = idx
                            print(f"    ✓ Found start pattern match at row {start_idx}")
                            print(f"      Matched text: {row_text[:100]}...")
                            break

                    # If start pattern is specified but not found, return empty DataFrame
                    if start_idx is None:
                        print(f"    ⚠️ Start pattern '{start_pattern}' not found in any row")
                        print(f"    Returning empty DataFrame as no start pattern match was found")
                        return pd.DataFrame(), {"status": "failed", "reason": f"Start pattern '{start_pattern}' not found"}
                except re.error as e:
                    print(f"    ❌ Invalid start pattern '{start_pattern}': {str(e)}")
                    # Skip this pattern but continue with the others
                    start_pattern = None

            # If start_pattern had an error or was None, start from the beginning
            if start_pattern is None:
                start_idx = 0
                print(f"    No valid start pattern, starting from first row (index {start_idx})")

            # Find end index based on pattern - only if end_pattern is explicitly defined
            if end_pattern:
                try:
                    print(f"    Searching for end pattern '{end_pattern}' starting from row {start_idx}...")
                    for idx, row in str_df.loc[start_idx:].iterrows():
                        row_text = " ".join(row.values)
                        if re.search(end_pattern, row_text, re.IGNORECASE):
                            end_idx = idx
                            print(f"    ✓ Found end pattern match at row {end_idx}")
                            print(f"      Matched text: {row_text[:100]}...")
                            break

                    # If end pattern is specified but not found, use the last row
                    if end_idx is None:
                        end_idx = df.index[-1]
                        print(f"    ⚠️ End pattern '{end_pattern}' not found, using last row at index {end_idx}")
                except re.error as e:
                    print(f"    ❌ Invalid end pattern '{end_pattern}': {str(e)}")
                    # Skip this pattern but continue with the others
                    end_pattern = None

            # If end_pattern had an error or was None, use the last row
            if end_pattern is None:
                end_idx = df.index[-1]
                print(f"    No valid end pattern, using last row (index {end_idx})")

            try:
                # Slice DataFrame to keep only rows between boundaries (inclusive)
                before_slice = len(df)
                df = df.loc[start_idx:end_idx]
                after_slice = len(df)
                rows_removed = before_slice - after_slice
                
                if rows_removed > 0:
                    print(f"    ✓ Applied boundary slicing: removed {rows_removed} rows, kept {after_slice} rows")
                else:
                    print(f"    ℹ Boundary slicing had no effect: kept all {after_slice} rows")
            except Exception as e:
                print(f"    ❌ Error during boundary slicing: {str(e)}")
                # If there's an error in slicing, return the original DataFrame
                return df, {"status": "partial", "reason": f"Error in boundary slicing: {str(e)}"}

        # Filter out rows matching skip pattern - only if skip_pattern is explicitly defined
        if skip_pattern and not df.empty:
            try:
                print(f"    Applying skip pattern '{skip_pattern}'...")
                before_count = len(df)
                
                # Create a string version of the current DataFrame
                str_df = df.astype(str)
                
                # Apply the filter
                df = df[~str_df.apply(lambda row: any(re.search(skip_pattern, str(val), re.IGNORECASE) for val in row), axis=1)]
                
                # Report results
                after_count = len(df)
                skipped_rows = before_count - after_count
                
                if skipped_rows > 0:
                    print(f"    ✓ Skipped {skipped_rows} rows based on pattern")
                    print(f"    Final DataFrame size: {after_count} rows")
                else:
                    print(f"    ℹ Skip pattern did not match any rows")
                
                # Check if we have any rows left
                if df.empty:
                    print(f"    ⚠️ All rows were filtered out by skip pattern!")
                    return df, {"status": "failed", "reason": "All rows filtered out by skip pattern"}
                    
            except re.error as e:
                print(f"    ❌ Invalid skip pattern '{skip_pattern}': {str(e)}")
                # If there's an error with the skip pattern, continue with what we have
                pass
            except Exception as e:
                print(f"    ❌ Error applying skip pattern: {str(e)}")
                # Continue with what we have
                pass
        
        # Check final state
        final_status = "success"
        reason = "Regex patterns applied successfully"
        
        # Empty result is a failure
        if  df.empty:
            final_status = "failed"
            reason = "No data remained after applying patterns"
        # If we have significantly fewer rows than we started with, consider it partial
        elif len(df) < orig_row_count * 0.5 and orig_row_count > 10:
            final_status = "partial"
            reason = f"Only {len(df)} of {orig_row_count} rows remained after filtering"
        # For very small datasets, just having data is good
        elif len(df) < 5 and orig_row_count > 10:
            final_status = "partial"
            reason = f"Only {len(df)} rows extracted from {orig_row_count}"
            
        print(f"    ✓ Regex processing complete: {final_status} - {reason}")
        print(f"    Final row count: {len(df)}")
        
        return df, {"status": final_status, "reason": reason}

    def stop_processing(self):
        """Stop the processing of files"""
        self.should_stop = True
        self.status_label.setText("Stopping processing...")
        
    def update_processing_time(self, is_final=False):
        """Update the processing time display"""
        if self.start_time:
            elapsed_time = time.time() - self.start_time
            minutes, seconds = divmod(int(elapsed_time), 60)
            hours, minutes = divmod(minutes, 60)
            
            if hours > 0:
                time_str = f"Time: {hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                time_str = f"Time: {minutes}m {seconds}s"
            else:
                time_str = f"Time: {seconds}s"
                
            if is_final:
                time_str = f"Total {time_str}"
                
            self.processing_time_label.setText(time_str)

    def get_selected_template_id(self):
        """Get the ID of the selected template"""
        if self.template_combo.count() == 0:
            return None
        return self.template_combo.currentData()
