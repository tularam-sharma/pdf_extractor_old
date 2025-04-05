"""Script to add the extract_invoice_tables method to bulk_processor.py"""

try:
    print("Reading files...")
    # Read current file
    with open('bulk_processor.py', 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Read the method
    with open('extract_invoice_tables_method.txt', 'r', encoding='utf-8') as file:
        method = file.read()
    
    # Find the right position to insert the method
    # It should be before apply_regex_to_dataframe method
    method_position = content.find('def apply_regex_to_dataframe')
    
    if method_position == -1:
        print("Could not find the insertion point in bulk_processor.py")
        exit(1)
    
    # Create the new content
    new_content = content[:method_position] + method + content[method_position:]
    
    # Create a backup of the original file
    with open('bulk_processor_pre_add.py', 'w', encoding='utf-8') as file:
        file.write(content)
    print("Created backup in bulk_processor_pre_add.py")
    
    # Write the updated content
    with open('bulk_processor.py', 'w', encoding='utf-8') as file:
        file.write(new_content)
    
    print("✅ Successfully added extract_invoice_tables method to bulk_processor.py")
    
    # Verify the file compiles
    import py_compile
    py_compile.compile('bulk_processor.py')
    print("✅ File compiles without syntax errors")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc() 