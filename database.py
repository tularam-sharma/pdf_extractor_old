import sqlite3
import json
import os
from pathlib import Path
import datetime

class InvoiceDatabase:
    def __init__(self, db_path="invoice_templates.db"):
        """Initialize the database connection"""
        # Ensure the database directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        """Create the necessary database tables if they don't exist"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                template_type TEXT NOT NULL,
                regions TEXT NOT NULL,  -- JSON string containing both scaled and drawn regions
                column_lines TEXT NOT NULL,  -- JSON string containing column line positions
                config TEXT NOT NULL,  -- JSON string containing additional configuration
                creation_date TEXT NOT NULL
            )
        """)
        self.conn.commit()
    
    def save_template(self, name, description, regions, column_lines, config, template_type="single"):
        """Save a template to the database"""
        try:
            # Convert regions to JSON string
            regions_json = json.dumps(regions)
            
            # Convert column lines to JSON string
            column_lines_json = json.dumps(column_lines)
            
            # Convert config to JSON string
            config_json = json.dumps(config)
            
            # Get current date in ISO format
            creation_date = datetime.datetime.now().isoformat()
            
            # Check if template with this name already exists
            self.cursor.execute("SELECT id FROM templates WHERE name = ?", (name,))
            existing_template = self.cursor.fetchone()
            
            if existing_template:
                # Update existing template
                self.cursor.execute("""
                    UPDATE templates 
                    SET description = ?, regions = ?, column_lines = ?, config = ?, template_type = ?
                    WHERE name = ?
                """, (description, regions_json, column_lines_json, config_json, template_type, name))
                template_id = existing_template[0]
            else:
                # Insert new template
                self.cursor.execute("""
                    INSERT INTO templates (name, description, regions, column_lines, config, template_type, creation_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (name, description, regions_json, column_lines_json, config_json, template_type, creation_date))
                template_id = self.cursor.lastrowid
            
            self.conn.commit()
            return template_id
            
        except Exception as e:
            print(f"Error saving template: {str(e)}")
            self.conn.rollback()
            raise
    
    def get_template(self, template_id=None, template_name=None):
        """
        Retrieve a template by ID or name
        
        Args:
            template_id (int, optional): Template ID
            template_name (str, optional): Template name
            
        Returns:
            dict: Template data including regions and column lines
        """
        from PySide6.QtCore import QPoint, QRect
        
        if template_id is None and template_name is None:
            raise ValueError("Either template_id or template_name must be provided")
        
        if template_name:
            self.cursor.execute("SELECT id FROM templates WHERE name = ?", (template_name,))
            result = self.cursor.fetchone()
            if not result:
                return None
            template_id = result[0]
        
        # Get template info including all JSON data
        self.cursor.execute(
            "SELECT id, name, description, template_type, regions, column_lines, config, creation_date FROM templates WHERE id = ?", 
            (template_id,)
        )
        
        template_row = self.cursor.fetchone()
        if not template_row:
            return None
        
        # Create base template dictionary
        template = {
            "id": template_row[0],
            "name": template_row[1],
            "description": template_row[2],
            "template_type": template_row[3],
            "creation_date": template_row[7]
        }
        
        # Parse JSON data
        try:
            # Parse regions JSON
            regions_json = template_row[4]
            regions = json.loads(regions_json)
            template["regions"] = regions
            
            # Parse column lines JSON
            column_lines_json = template_row[5]
            column_lines = json.loads(column_lines_json)
            template["column_lines"] = column_lines
            
            # Parse config JSON
            config_json = template_row[6]
            config = json.loads(config_json)
            template["config"] = config
            
        except json.JSONDecodeError as e:
            print(f"Error parsing template JSON data: {str(e)}")
            # Return partial template data even if JSON parsing fails
        
        return template
    
    def get_all_templates(self):
        """
        Retrieve a list of all available templates
        
        Returns:
            list: List of template basic info (id, name, description, type)
        """
        try:
            # First check if the last_modified column exists
            self.cursor.execute("PRAGMA table_info(templates)")
            columns = self.cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'last_modified' in column_names:
                # If column exists, use it
                self.cursor.execute(
                    "SELECT id, name, description, template_type, creation_date, last_modified FROM templates ORDER BY name"
                )
                templates = []
                for row in self.cursor.fetchall():
                    templates.append({
                        "id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "template_type": row[3],
                        "creation_date": row[4],
                        "last_modified": row[5]
                    })
            else:
                # If column doesn't exist, don't include it
                self.cursor.execute(
                    "SELECT id, name, description, template_type, creation_date FROM templates ORDER BY name"
                )
                templates = []
                for row in self.cursor.fetchall():
                    templates.append({
                        "id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "template_type": row[3],
                        "creation_date": row[4]
                    })
            
            return templates
        except Exception as e:
            print(f"Error in get_all_templates: {str(e)}")
            # Return empty list if there's an error
            return []
    
    def delete_template(self, template_id=None, template_name=None):
        """
        Delete a template by ID or name
        
        Args:
            template_id (int, optional): Template ID
            template_name (str, optional): Template name
            
        Returns:
            bool: True if deleted successfully
        """
        if template_id is None and template_name is None:
            raise ValueError("Either template_id or template_name must be provided")
        
        try:
            if template_name:
                self.cursor.execute("SELECT id FROM templates WHERE name = ?", (template_name,))
                result = self.cursor.fetchone()
                if not result:
                    return False
                template_id = result[0]
            
            # The foreign key constraints will handle deletion of related records
            self.cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            self.conn.rollback()
            return False
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close() 