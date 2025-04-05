import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from template_manager import TemplateManager

if __name__ == "__main__":
    print("Starting Template Manager...")
    app = QApplication(sys.argv)
    
    # Create and show the Template Manager
    template_manager = TemplateManager()
    template_manager.setWindowTitle("Invoice Template Manager")
    template_manager.resize(900, 700)
    
    # In standalone mode, connect the go_back signal to close the application
    # with a confirmation dialog
    def handle_go_back():
        msg = QMessageBox()
        msg.setWindowTitle("Confirm Exit")
        msg.setText("Are you sure you want to exit?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.setStyleSheet("QLabel { color: black; }")
        if msg.exec() == QMessageBox.Yes:
            template_manager.close()
    
    # Connect the go_back signal to our handler
    template_manager.go_back.connect(handle_go_back)
    
    # Handle template selection in standalone mode
    def handle_template_selected(template):
        msg = QMessageBox()
        msg.setWindowTitle("Template Selected")
        msg.setText(f"Template Selected: {template['name']}")
        msg.setInformativeText("In standalone mode, templates cannot be applied to a PDF processor.")
        msg.setStyleSheet("QLabel { color: black; }")
        msg.exec()
    
    # Connect the template_selected signal to our handler
    template_manager.template_selected.connect(handle_template_selected)
    
    template_manager.show()
    print("Template Manager initialized and displayed")
    
    # Start the application event loop
    sys.exit(app.exec()) 