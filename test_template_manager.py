from PySide6.QtWidgets import QApplication
from template_manager import TemplateManager
import traceback
import sys

print("Starting test...")

try:
    print("Creating QApplication...")
    app = QApplication(sys.argv)
    
    print("Creating TemplateManager instance...")
    tm = TemplateManager()
    print("TemplateManager instantiated successfully!")
    
    # Don't run the event loop to keep the test simple
    # app.exec()
except Exception as e:
    print(f"Error: {e}")
    print("Traceback:")
    traceback.print_exc()

print("Test completed.") 