import sqlite3
import json
import os
from pathlib import Path
import datetime

class InvoiceDatabase:
    def __init__(self, db_path="invoice_templates.db"):
        """Initialize the database connection"""
        try:
            # Store the database path
            self.db_path = db_path
            
            # Ensure the database directory exists
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
                print(f"Created database directory: {db_dir}")
            
            # Check if the database exists and if it might be corrupted
            if os.path.exists(db_path):
                file_size = os.path.getsize(db_path)
                print(f"Database file exists: {db_path}, size: {file_size} bytes")
                
                if file_size == 0:
                    print("Warning: Database file exists but is empty, it may be corrupted")
                
                # Create a backup before opening if file exists and has content
                if file_size > 0:
                    backup_path = f"{db_path}.bak"
                    try:
                        import shutil
                        shutil.copy2(db_path, backup_path)
                        print(f"Created database backup at: {backup_path}")
                    except Exception as backup_e:
                        print(f"Warning: Could not create database backup: {str(backup_e)}")
            else:
                print(f"Creating new database at: {db_path}")
            
            # Try to connect to the database with timeout and error handling
            try:
                self.conn = sqlite3.connect(db_path, timeout=30.0)  # 30 second timeout
                self.conn.execute("PRAGMA journal_mode=WAL")  # Use Write-Ahead Logging for better concurrency
                self.conn.execute("PRAGMA synchronous=NORMAL")  # Balance between safety and performance
                self.cursor = self.conn.cursor()
                print(f"Connected to database: {db_path}")
                
                # Test the connection by running a simple query
                self.cursor.execute("SELECT sqlite_version()")
                version = self.cursor.fetchone()
                print(f"SQLite version: {version[0]}")
                
                # Create the tables
                self.create_tables()
            except sqlite3.DatabaseError as db_error:
                print(f"Database error during connection: {str(db_error)}")
                
                # Try to recover from backup if exists
                backup_path = f"{db_path}.bak"
                if os.path.exists(backup_path):
                    print(f"Attempting recovery from backup: {backup_path}")
                    try:
                        # Close any open connections
                        if hasattr(self, 'conn') and self.conn:
                            self.conn.close()
                        
                        # Rename the corrupted database
                        corrupted_path = f"{db_path}.corrupted"
                        os.rename(db_path, corrupted_path)
                        print(f"Renamed corrupted database to: {corrupted_path}")
                        
                        # Restore from backup
                        import shutil
                        shutil.copy2(backup_path, db_path)
                        print(f"Restored database from backup")
                        
                        # Try to connect again
                        self.conn = sqlite3.connect(db_path)
                        self.cursor = self.conn.cursor()
                        print("Successfully recovered database from backup")
                    except Exception as recovery_e:
                        print(f"Recovery failed: {str(recovery_e)}")
                        # Create a fresh database as last resort
                        if os.path.exists(db_path):
                            os.remove(db_path)
                        self.conn = sqlite3.connect(db_path)
                        self.cursor = self.conn.cursor()
                        print("Created fresh database after recovery failure")
                else:
                    # No backup exists, create a fresh database
                    print("No backup found, creating fresh database")
                    if os.path.exists(db_path):
                        os.remove(db_path)
                    self.conn = sqlite3.connect(db_path)
                    self.cursor = self.conn.cursor()
                    
                # Create the tables for the new/recovered database
                self.create_tables()
                
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Make sure we have a valid connection and cursor even after errors
            if not hasattr(self, 'conn') or self.conn is None:
                try:
                    self.conn = sqlite3.connect(":memory:")  # Use in-memory DB as fallback
                    self.cursor = self.conn.cursor()
                    print("Using in-memory database as fallback after error")
                    self.create_tables()
                except Exception as fallback_e:
                    print(f"Could not create fallback database: {str(fallback_e)}")
                    # Set to None to prevent further method calls from crashing
                    self.conn = None
                    self.cursor = None
    
    def create_tables(self):
        """Create the necessary database tables if they don't exist"""
        # Create templates table with support for both single and multi-page templates
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                template_type TEXT NOT NULL,  -- 'single' or 'multi'
                regions TEXT NOT NULL,  -- JSON string containing both scaled and drawn regions
                column_lines TEXT NOT NULL,  -- JSON string containing column line positions
                config TEXT NOT NULL,  -- JSON string containing additional configuration
                creation_date TEXT NOT NULL,
                last_modified TEXT,
                page_count INTEGER DEFAULT 1,  -- Number of pages in the template
                page_regions TEXT,  -- JSON string containing regions for each page
                page_column_lines TEXT,  -- JSON string containing column lines for each page
                page_configs TEXT,  -- JSON string containing configs for each page
                validation_rules TEXT  -- JSON string containing validation rules for fields
            )
        """)
        
        # Check if the required columns exist, and add them if they don't
        self.cursor.execute("PRAGMA table_info(templates)")
        columns = self.cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'page_count' not in column_names:
            print("Adding missing 'page_count' column to templates table")
            try:
                self.cursor.execute("ALTER TABLE templates ADD COLUMN page_count INTEGER DEFAULT 1")
            except sqlite3.Error as e:
                print(f"Error adding page_count column: {str(e)}")
        
        if 'last_modified' not in column_names:
            print("Adding missing 'last_modified' column to templates table")
            try:
                self.cursor.execute("ALTER TABLE templates ADD COLUMN last_modified TEXT")
                # Update existing records to use creation_date as the last_modified value
                self.cursor.execute("UPDATE templates SET last_modified = creation_date WHERE last_modified IS NULL")
            except sqlite3.Error as e:
                print(f"Error adding last_modified column: {str(e)}")
        
        if 'page_regions' not in column_names:
            print("Adding missing 'page_regions' column to templates table")
            try:
                self.cursor.execute("ALTER TABLE templates ADD COLUMN page_regions TEXT")
            except sqlite3.Error as e:
                print(f"Error adding page_regions column: {str(e)}")
        
        if 'page_column_lines' not in column_names:
            print("Adding missing 'page_column_lines' column to templates table")
            try:
                self.cursor.execute("ALTER TABLE templates ADD COLUMN page_column_lines TEXT")
            except sqlite3.Error as e:
                print(f"Error adding page_column_lines column: {str(e)}")
        
        if 'page_configs' not in column_names:
            print("Adding missing 'page_configs' column to templates table")
            try:
                self.cursor.execute("ALTER TABLE templates ADD COLUMN page_configs TEXT")
            except sqlite3.Error as e:
                print(f"Error adding page_configs column: {str(e)}")
        
        if 'validation_rules' not in column_names:
            print("Adding missing 'validation_rules' column to templates table")
            try:
                self.cursor.execute("ALTER TABLE templates ADD COLUMN validation_rules TEXT")
            except sqlite3.Error as e:
                print(f"Error adding validation_rules column: {str(e)}")
        
        self.conn.commit()
    
    def save_template(self, name, description, regions, column_lines, config, template_type="single", page_count=1, page_regions=None, page_column_lines=None, page_configs=None, validation_rules=None):
        """Save a template to the database"""
        try:
            # Validate inputs
            if not name or not isinstance(name, str):
                raise ValueError(f"Invalid template name: {name}")
                
            if template_type == "multi":
                # For multi-page templates, regions and column_lines can be empty
                if not isinstance(regions, dict):
                    regions = {}
                if not isinstance(column_lines, dict):
                    column_lines = {}
            else:
                # For single-page templates, regions and column_lines must be valid dictionaries
                if not isinstance(regions, dict):
                    raise ValueError(f"Invalid regions data type: {type(regions)}")
                if not isinstance(column_lines, dict):
                    raise ValueError(f"Invalid column_lines data type: {type(column_lines)}")
                
            if not isinstance(config, dict):
                raise ValueError(f"Invalid config data type: {type(config)}")
                
            # Debug information
            print(f"\nSaving template to database: {name}")
            print(f"  Template type: {template_type}")
            print(f"  Page count: {page_count}")
            print(f"  Regions count: {sum(len(rects) for rects in regions.values())}")
            print(f"  Column lines count: {sum(len(lines) for lines in column_lines.values())}")
            print(f"  Config keys: {list(config.keys())}")
            
            # Convert to JSON strings with error handling
            try:
                regions_json = json.dumps(regions)
                print(f"  Regions JSON size: {len(regions_json)} bytes")
                
                # Check if the JSON is too large
                if len(regions_json) > 5 * 1024 * 1024:  # 5 MB limit
                    raise ValueError(f"Regions data too large: {len(regions_json) / (1024*1024):.2f} MB")
                    
                column_lines_json = json.dumps(column_lines)
                print(f"  Column lines JSON size: {len(column_lines_json)} bytes")
                
                # Check if the JSON is too large
                if len(column_lines_json) > 1 * 1024 * 1024:  # 1 MB limit
                    raise ValueError(f"Column lines data too large: {len(column_lines_json) / (1024*1024):.2f} MB")
                
                config_json = json.dumps(config)
                print(f"  Config JSON size: {len(config_json)} bytes")
                
                # Check if the JSON is too large
                if len(config_json) > 1 * 1024 * 1024:  # 1 MB limit
                    raise ValueError(f"Config data too large: {len(config_json) / (1024*1024):.2f} MB")
                
                # Convert page-specific data to JSON if provided
                page_regions_json = json.dumps(page_regions) if page_regions else None
                page_column_lines_json = json.dumps(page_column_lines) if page_column_lines else None
                page_configs_json = json.dumps(page_configs) if page_configs else None
                
                # Convert validation_rules to JSON if provided
                validation_rules_json = json.dumps(validation_rules) if validation_rules else None
                
            except TypeError as json_error:
                # Handle JSON serialization errors for specific types
                error_msg = f"JSON serialization error: {str(json_error)}"
                print(error_msg)
                raise ValueError(error_msg)
            
            # Get current date in ISO format
            creation_date = datetime.datetime.now().isoformat()
            last_modified = creation_date
            
            # Check if template with this name already exists
            self.cursor.execute("SELECT id FROM templates WHERE name = ?", (name,))
            existing_template = self.cursor.fetchone()
            
            # Check which columns exist in the templates table
            self.cursor.execute("PRAGMA table_info(templates)")
            columns = self.cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            has_last_modified = 'last_modified' in column_names
            has_page_count = 'page_count' in column_names
            has_page_regions = 'page_regions' in column_names
            has_page_column_lines = 'page_column_lines' in column_names
            has_page_configs = 'page_configs' in column_names
            has_validation_rules = 'validation_rules' in column_names
            
            if existing_template:
                print(f"  Updating existing template with ID: {existing_template[0]}")
                
                # Build the SQL UPDATE statement dynamically based on available columns
                update_fields = [
                    "description = ?",
                    "regions = ?",
                    "column_lines = ?",
                    "config = ?",
                    "template_type = ?",
                    "validation_rules = ?"
                ]
                update_values = [
                    description,
                    regions_json,
                    column_lines_json,
                    config_json,
                    template_type,
                    validation_rules_json
                ]
                
                if has_last_modified:
                    update_fields.append("last_modified = ?")
                    update_values.append(last_modified)
                
                if has_page_count:
                    update_fields.append("page_count = ?")
                    update_values.append(page_count)
                
                if has_page_regions:
                    update_fields.append("page_regions = ?")
                    update_values.append(page_regions_json)
                
                if has_page_column_lines:
                    update_fields.append("page_column_lines = ?")
                    update_values.append(page_column_lines_json)
                
                if has_page_configs:
                    update_fields.append("page_configs = ?")
                    update_values.append(page_configs_json)
                
                # Add the WHERE clause parameter
                update_values.append(name)
                
                # Build and execute the final UPDATE query
                update_query = f"UPDATE templates SET {', '.join(update_fields)} WHERE name = ?"
                print(f"  Executing update query: {update_query}")
                self.cursor.execute(update_query, update_values)
                
                template_id = existing_template[0]
            else:
                print(f"  Creating new template")
                
                # Build the SQL INSERT statement dynamically based on available columns
                insert_fields = [
                    "name",
                    "description",
                    "regions",
                    "column_lines",
                    "config",
                    "template_type",
                    "creation_date",
                    "validation_rules"
                ]
                insert_values = [
                    name,
                    description,
                    regions_json,
                    column_lines_json,
                    config_json,
                    template_type,
                    creation_date,
                    validation_rules_json
                ]
                
                if has_last_modified:
                    insert_fields.append("last_modified")
                    insert_values.append(last_modified)
                
                if has_page_count:
                    insert_fields.append("page_count")
                    insert_values.append(page_count)
                
                if has_page_regions:
                    insert_fields.append("page_regions")
                    insert_values.append(page_regions_json)
                
                if has_page_column_lines:
                    insert_fields.append("page_column_lines")
                    insert_values.append(page_column_lines_json)
                
                if has_page_configs:
                    insert_fields.append("page_configs")
                    insert_values.append(page_configs_json)
                
                # Build and execute the final INSERT query
                placeholders = ", ".join(["?"] * len(insert_values))
                insert_query = f"INSERT INTO templates ({', '.join(insert_fields)}) VALUES ({placeholders})"
                print(f"  Executing insert query: {insert_query}")
                self.cursor.execute(insert_query, insert_values)
                
                template_id = self.cursor.lastrowid
                print(f"  New template created with ID: {template_id}")
            
            # Commit the transaction
            print("  Committing transaction to database")
            self.conn.commit()
            print("  Template saved successfully")
            return template_id
            
        except sqlite3.Error as sql_e:
            print(f"SQLite error saving template: {str(sql_e)}")
            print(f"Database path: {self.db_path}")
            if os.path.exists(self.db_path):
                print(f"Database file size: {os.path.getsize(self.db_path)} bytes")
                print(f"Database file permissions: {oct(os.stat(self.db_path).st_mode)[-3:]}")
            self.conn.rollback()
            raise
        except Exception as e:
            print(f"Error saving template: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
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
        
        # First check which columns exist in the templates table
        self.cursor.execute("PRAGMA table_info(templates)")
        columns = self.cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Build the select query based on available columns
        select_columns = ["id", "name", "description", "template_type", "regions", "column_lines", 
                         "config", "creation_date"]
        
        if "last_modified" in column_names:
            select_columns.append("last_modified")
        
        if "page_count" in column_names:
            select_columns.append("page_count")
            
        if "page_regions" in column_names:
            select_columns.append("page_regions")
            
        if "page_column_lines" in column_names:
            select_columns.append("page_column_lines")
            
        if "page_configs" in column_names:
            select_columns.append("page_configs")
        
        if "validation_rules" in column_names:
            select_columns.append("validation_rules")
        
        # Get template info including all available JSON data
        query = f"SELECT {', '.join(select_columns)} FROM templates WHERE id = ?"
        self.cursor.execute(query, (template_id,))
        
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
        
        # Add optional columns with appropriate index handling
        column_index = 8  # Starting after creation_date
        
        if "last_modified" in column_names:
            template["last_modified"] = template_row[column_index]
            column_index += 1
        else:
            template["last_modified"] = template_row[7]  # Use creation_date as fallback
        
        if "page_count" in column_names:
            template["page_count"] = template_row[column_index]
            column_index += 1
        else:
            template["page_count"] = 1  # Default value
        
        # Parse JSON data
        try:
            # Parse regions JSON (always present at index 4)
            regions_json = template_row[4]
            regions = json.loads(regions_json)
            template["regions"] = regions
            
            # Parse column lines JSON (always present at index 5)
            column_lines_json = template_row[5]
            column_lines = json.loads(column_lines_json)
            template["column_lines"] = column_lines
            
            # Parse config JSON (always present at index 6)
            config_json = template_row[6]
            config = json.loads(config_json)
            template["config"] = config
            
            # Add multi-page data if columns exist and data is present
            if "page_regions" in column_names and column_index < len(template_row):
                page_regions_json = template_row[column_index]
                if page_regions_json:
                    template["page_regions"] = json.loads(page_regions_json)
                column_index += 1
            
            if "page_column_lines" in column_names and column_index < len(template_row):
                page_column_lines_json = template_row[column_index]
                if page_column_lines_json:
                    template["page_column_lines"] = json.loads(page_column_lines_json)
                column_index += 1
            
            if "page_configs" in column_names and column_index < len(template_row):
                page_configs_json = template_row[column_index]
                if page_configs_json:
                    template["page_configs"] = json.loads(page_configs_json)
            
            # Add validation_rules if column exists and data is present
            if "validation_rules" in column_names:
                column_index = select_columns.index("validation_rules")
                validation_rules_json = template_row[column_index]
                if validation_rules_json:
                    template["validation_rules"] = json.loads(validation_rules_json)
                else:
                    template["validation_rules"] = []
            else:
                template["validation_rules"] = []
            
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
            # First check if columns exist
            self.cursor.execute("PRAGMA table_info(templates)")
            columns = self.cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            has_last_modified = 'last_modified' in column_names
            has_page_count = 'page_count' in column_names
            
            # Build the appropriate query based on available columns
            select_columns = ["id", "name", "description", "template_type", "creation_date"]
            
            if has_last_modified:
                select_columns.append("last_modified")
                
            if has_page_count:
                select_columns.append("page_count")
                
            query = f"SELECT {', '.join(select_columns)} FROM templates ORDER BY name"
            self.cursor.execute(query)
            
            templates = []
            for row in self.cursor.fetchall():
                template_dict = {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "template_type": row[3],
                    "creation_date": row[4]
                }
                
                # Add last_modified if it exists, otherwise use creation_date
                if has_last_modified:
                    template_dict["last_modified"] = row[5]
                else:
                    template_dict["last_modified"] = row[4]  # Use creation_date as fallback
                
                # Add page_count if it exists, otherwise use default of 1
                if has_page_count:
                    index = 6 if has_last_modified else 5
                    template_dict["page_count"] = row[index]
                else:
                    template_dict["page_count"] = 1  # Default value
                    
                templates.append(template_dict)
            
            return templates
        except Exception as e:
            print(f"Error in get_all_templates: {str(e)}")
            import traceback
            traceback.print_exc()
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
        try:
            # First close the cursor if it exists
            if hasattr(self, 'cursor') and self.cursor:
                try:
                    self.cursor.close()
                    print("Database cursor closed")
                except Exception as cursor_e:
                    print(f"Error closing database cursor: {str(cursor_e)}")
            
            # Then close the connection
            if hasattr(self, 'conn') and self.conn:
                try:
                    self.conn.close()
                    print("Database connection closed")
                except Exception as conn_e:
                    print(f"Error closing database connection: {str(conn_e)}")
            
            # Clear references to prevent further use
            self.cursor = None
            self.conn = None
        except Exception as e:
            print(f"Error in database close method: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def optimize_database(self):
        """
        Optimize the database by running VACUUM and ANALYZE commands.
        This defragments the database file, reclaims unused space,
        and updates statistics used by the query optimizer.
        
        Returns:
            bool: True if optimization succeeded, False otherwise
        """
        try:
            print("Starting database optimization...")
            
            # Check database size before optimization
            if os.path.exists(self.db_path):
                size_before = os.path.getsize(self.db_path)
                print(f"Database size before optimization: {size_before/1024:.2f} KB")
            
            # Enable auto vacuum for future operations
            self.conn.execute("PRAGMA auto_vacuum = INCREMENTAL")
            
            # Update SQLite statistics for query optimization
            print("Running ANALYZE...")
            self.conn.execute("ANALYZE")
            
            # Defragment the database and reclaim unused space
            print("Running VACUUM...")
            self.conn.execute("VACUUM")
            
            # Optimize database indices
            print("Rebuilding indices...")
            self.conn.execute("PRAGMA optimize")
            
            # Commit changes
            self.conn.commit()
            
            # Check database size after optimization
            if os.path.exists(self.db_path):
                size_after = os.path.getsize(self.db_path)
                print(f"Database size after optimization: {size_after/1024:.2f} KB")
                print(f"Space saved: {(size_before - size_after)/1024:.2f} KB ({100 * (size_before - size_after) / size_before:.2f}%)")
            
            print("Database optimization completed successfully")
            return True
        except Exception as e:
            print(f"Error optimizing database: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
    def check_integrity(self, repair=True):
        """
        Check the integrity of the database and optionally repair issues.
        
        Args:
            repair (bool): Whether to attempt repairs if issues are found
            
        Returns:
            tuple: (bool, str) - Success status and message with details
        """
        try:
            print("Checking database integrity...")
            
            # Run quick integrity check
            self.cursor.execute("PRAGMA quick_check")
            result = self.cursor.fetchone()
            integrity_status = result[0] if result else "unknown"
            
            if integrity_status == "ok":
                print("Quick integrity check passed")
                
                # Run more thorough integrity check
                self.cursor.execute("PRAGMA integrity_check")
                result = self.cursor.fetchall()
                integrity_details = [row[0] for row in result]
                
                if len(integrity_details) == 1 and integrity_details[0] == "ok":
                    print("Full integrity check passed")
                    return True, "Database integrity verified: no issues found"
                else:
                    error_msg = f"Integrity issues found: {', '.join(integrity_details[:5])}"
                    if len(integrity_details) > 5:
                        error_msg += f" and {len(integrity_details) - 5} more issues"
                    print(error_msg)
                    
                    if repair:
                        return self._repair_database(integrity_details)
                    else:
                        return False, error_msg
            else:
                error_msg = f"Quick integrity check failed: {integrity_status}"
                print(error_msg)
                
                if repair:
                    return self._repair_database([integrity_status])
                else:
                    return False, error_msg
                    
        except Exception as e:
            error_msg = f"Error checking database integrity: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            
            if repair:
                return self._repair_database([str(e)])
            else:
                return False, error_msg
                
    def _repair_database(self, issues):
        """
        Attempt to repair database issues by:
        1. Creating a backup
        2. Exporting data to an in-memory database
        3. Recreating the database file
        4. Importing the data back
        
        Args:
            issues (list): List of integrity issues found
            
        Returns:
            tuple: (bool, str) - Success status and message with details
        """
        try:
            print(f"Attempting database repair for {len(issues)} issues...")
            
            # 1. Create a backup
            backup_path = f"{self.db_path}.repair_backup"
            import shutil
            shutil.copy2(self.db_path, backup_path)
            print(f"Created repair backup at: {backup_path}")
            
            # 2. Export data to in-memory database
            print("Exporting data to temporary database...")
            temp_conn = sqlite3.connect(":memory:")
            temp_cursor = temp_conn.cursor()
            
            # Create tables in temp database
            temp_cursor.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    template_type TEXT NOT NULL,
                    regions TEXT NOT NULL,
                    column_lines TEXT NOT NULL,
                    config TEXT NOT NULL,
                    creation_date TEXT NOT NULL
                )
            """)
            
            # Export salvageable data
            try:
                self.cursor.execute("SELECT id, name, description, template_type, regions, column_lines, config, creation_date FROM templates")
                templates = self.cursor.fetchall()
                print(f"Found {len(templates)} templates to export")
                
                # Insert into temp database
                for template in templates:
                    try:
                        temp_cursor.execute("""
                            INSERT INTO templates (id, name, description, template_type, regions, column_lines, config, creation_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, template)
                    except Exception as insert_e:
                        print(f"Error importing template {template[1]}: {str(insert_e)}")
                        
                temp_conn.commit()
                exported_count = temp_cursor.execute("SELECT COUNT(*) FROM templates").fetchone()[0]
                print(f"Successfully exported {exported_count} of {len(templates)} templates")
                
            except Exception as export_e:
                print(f"Error exporting data: {str(export_e)}")
                # Continue with repair even if export fails
            
            # 3. Close connections and recreate the database file
            self.close()
            
            # Remove the corrupted database
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                print(f"Removed corrupted database: {self.db_path}")
            
            # Create a fresh database
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.create_tables()
            print("Created fresh database")
            
            # 4. Import the data back
            if exported_count > 0:
                print(f"Importing {exported_count} templates back to the database...")
                temp_cursor.execute("SELECT id, name, description, template_type, regions, column_lines, config, creation_date FROM templates")
                templates = temp_cursor.fetchall()
                
                # Use a transaction for faster import
                self.conn.execute("BEGIN TRANSACTION")
                
                # Insert each template
                import_count = 0
                for template in templates:
                    try:
                        self.cursor.execute("""
                            INSERT INTO templates (id, name, description, template_type, regions, column_lines, config, creation_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, template)
                        import_count += 1
                    except Exception as import_e:
                        print(f"Error importing template {template[1]}: {str(import_e)}")
                
                self.conn.commit()
                print(f"Successfully imported {import_count} of {exported_count} templates")
            
            # Close the temporary connection
            temp_conn.close()
            
            # Run optimization after repair
            print("Running optimization after repair...")
            self.optimize_database()
            
            if exported_count > 0 and import_count == exported_count:
                return True, f"Database successfully repaired: recovered {import_count} templates"
            elif import_count > 0:
                return True, f"Database partially repaired: recovered {import_count} of {exported_count} templates"
            else:
                return False, "Database structure repaired but no data could be recovered"
            
        except Exception as e:
            error_msg = f"Error during database repair: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return False, error_msg
            
    def perform_maintenance(self, create_backup=True, max_backups=5, check_integrity=True, optimize=True):
        """
        Perform routine database maintenance tasks including:
        - Creating a timestamped backup
        - Checking database integrity
        - Optimizing the database
        - Managing backup files (keeping only the most recent ones)
        
        Args:
            create_backup (bool): Whether to create a backup
            max_backups (int): Maximum number of backups to keep (oldest will be deleted)
            check_integrity (bool): Whether to check database integrity
            optimize (bool): Whether to optimize the database
            
        Returns:
            dict: Results of maintenance operations
        """
        results = {
            "success": True,
            "backup": None,
            "integrity": None,
            "optimize": None,
            "errors": []
        }
        
        try:
            print("Starting database maintenance...")
            
            # Step 1: Create a backup if requested
            if create_backup and os.path.exists(self.db_path):
                try:
                    # Create a timestamped backup
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = f"{self.db_path}.{timestamp}.bak"
                    
                    import shutil
                    shutil.copy2(self.db_path, backup_path)
                    results["backup"] = {
                        "success": True,
                        "path": backup_path,
                        "size": os.path.getsize(backup_path)
                    }
                    print(f"Created backup at: {backup_path} ({results['backup']['size']/1024:.2f} KB)")
                    
                    # Manage backups - keep only the most recent ones
                    if max_backups > 0:
                        backup_files = []
                        db_dir = os.path.dirname(self.db_path) or "."
                        db_name = os.path.basename(self.db_path)
                        
                        # Find all backup files matching our pattern
                        for file in os.listdir(db_dir):
                            if file.startswith(db_name + ".") and file.endswith(".bak"):
                                full_path = os.path.join(db_dir, file)
                                backup_files.append((full_path, os.path.getmtime(full_path)))
                        
                        # Sort by modification time, newest first
                        backup_files.sort(key=lambda x: x[1], reverse=True)
                        
                        # Remove excess backups
                        if len(backup_files) > max_backups:
                            for path, _ in backup_files[max_backups:]:
                                try:
                                    os.remove(path)
                                    print(f"Removed old backup: {path}")
                                except Exception as rm_e:
                                    print(f"Failed to remove old backup {path}: {str(rm_e)}")
                                    results["errors"].append(f"Backup cleanup error: {str(rm_e)}")
                        
                        results["backup"]["managed"] = len(backup_files)
                        results["backup"]["kept"] = min(max_backups, len(backup_files))
                        results["backup"]["removed"] = max(0, len(backup_files) - max_backups)
                        
                except Exception as backup_e:
                    error_msg = f"Backup error: {str(backup_e)}"
                    print(error_msg)
                    results["backup"] = {"success": False, "error": error_msg}
                    results["errors"].append(error_msg)
                    results["success"] = False
            
            # Step 2: Check integrity if requested
            if check_integrity:
                try:
                    # Just check without repair
                    integrity_success, integrity_msg = self.check_integrity(repair=False)
                    results["integrity"] = {
                        "success": integrity_success,
                        "message": integrity_msg
                    }
                    
                    # If issues found and we have a backup, repair the database
                    if not integrity_success and results.get("backup", {}).get("success", False):
                        print("Issues found during integrity check, attempting repair...")
                        repair_success, repair_msg = self.check_integrity(repair=True)
                        results["integrity"]["repair"] = {
                            "success": repair_success,
                            "message": repair_msg
                        }
                        
                        # Update overall success status
                        if not repair_success:
                            results["success"] = False
                            results["errors"].append(f"Integrity repair failed: {repair_msg}")
                    
                except Exception as integrity_e:
                    error_msg = f"Integrity check error: {str(integrity_e)}"
                    print(error_msg)
                    results["integrity"] = {"success": False, "error": error_msg}
                    results["errors"].append(error_msg)
                    results["success"] = False
            
            # Step 3: Optimize if requested
            if optimize:
                try:
                    optimize_result = self.optimize_database()
                    results["optimize"] = {"success": optimize_result}
                    
                    if not optimize_result:
                        results["success"] = False
                        results["errors"].append("Optimization failed")
                        
                except Exception as optimize_e:
                    error_msg = f"Optimization error: {str(optimize_e)}"
                    print(error_msg)
                    results["optimize"] = {"success": False, "error": error_msg}
                    results["errors"].append(error_msg)
                    results["success"] = False
            
            # Summarize results
            print("\nMaintenance summary:")
            print(f"- Overall success: {results['success']}")
            if results.get("backup"):
                print(f"- Backup: {'✓' if results['backup'].get('success') else '✗'}")
            if results.get("integrity"):
                print(f"- Integrity: {'✓' if results['integrity'].get('success') else '✗'}")
            if results.get("optimize"):
                print(f"- Optimize: {'✓' if results['optimize'].get('success') else '✗'}")
            if results["errors"]:
                print(f"- Errors: {len(results['errors'])}")
                for i, error in enumerate(results["errors"]):
                    print(f"  {i+1}. {error}")
            
            return results
            
        except Exception as e:
            error_msg = f"Maintenance error: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            
            results["success"] = False
            results["errors"].append(error_msg)
            return results 