try:
    print("Attempting to import InvoiceSectionViewer...")
    from invoice_section_viewer import InvoiceSectionViewer
    print("Import successful!")
    print("Classes should be error-free")
except Exception as e:
    print(f"Error importing InvoiceSectionViewer: {str(e)}")
    import traceback
    traceback.print_exc() 