# PDF Harvest

A PyQt6-based application for extracting tables from PDF invoices with visual selection and mapping capabilities.

## Features

- Upload and process PDF invoices
- Visual table region selection
- Template management for recurring invoice formats
- Bulk upload support
- Modern and intuitive user interface

## Requirements

- Python 3.8 or higher
- PyQt6
- PyPDF2
- pdf2image
- Pillow
- numpy

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

## Development

The application is structured as follows:
- `main.py`: Main application window and UI components
- `requirements.txt`: Python package dependencies

## License

MIT License 