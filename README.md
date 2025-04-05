# PDF Harvest

A PyQt6-based application for extracting tables from PDF invoices with visual selection and mapping capabilities.

## Features

- Upload and process PDF invoices
- Visual table region selection
- Template management for recurring invoice formats
- Bulk upload support
- Modern and intuitive user interface
- Role-based access control for developers and users

## Requirements

- Python 3.8 or higher
- PySide6
- PyPDF2
- pdf2image
- Pillow
- numpy
- PyMuPDF

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/pdf_harvest.git
cd pdf_harvest
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application:
```bash
python main.py
```

### User Roles

The application implements role-based access control with two main roles:

1. **Developer** 
   - Full access to all features
   - Can manage templates and rules
   - Can perform bulk extraction
   
2. **User**
   - Limited to bulk extraction functionality
   - Cannot modify templates or rules

### Default Accounts

- **Developer Account**
  - Username: `admin`
  - Password: `admin`

- **User Account**
  - Username: `user`
  - Password: `user`

## Role-Based Components

The application uses a custom role-based UI component system:

- `RoleBasedWidget`: Base class for UI components with permission checks
- `LoginDialog`: Authentication dialog for user login
- `UserProfileWidget`: Displays current user and logout option
- `MainDashboard`: Role-aware dashboard showing appropriate features

## Development

The application is structured as follows:
- `main.py`: Main application window and UI components
- `user_management.py`: User authentication and permission handling
- `role_based_ui.py`: Role-based UI components
- `pdf_processor.py`: Core PDF processing logic
- `template_manager.py`: Template management functionality
- `bulk_processor.py`: Bulk PDF processing
- `requirements.txt`: Python package dependencies

## License

MIT License 