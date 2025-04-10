from setuptools import setup
from setuptools.extension import Extension
from Cython.Build import cythonize
from Cython.Distutils import build_ext
import os

# List of modules to compile
extensions = [
    Extension("license_manager", ["license_manager.py"]),
    Extension("activation_dialog", ["activation_dialog.py"]),
    Extension("pdf_processor", ["pdf_processor.py"]),
    Extension("template_manager", ["template_manager.py"]),
    Extension("invoice_section_viewer", ["invoice_section_viewer.py"]),
    Extension("bulk_processor", ["bulk_processor.py"]),
    Extension("user_management", ["user_management.py"]),
    Extension("role_based_ui", ["role_based_ui.py"]),
    Extension("user_management_ui", ["user_management_ui.py"]),
    Extension("validation_screen", ["validation_screen.py"]),
    Extension("main", ["main.py"])
]

# Cython compiler directives for better security
compiler_directives = {
    'language_level': 3,
    'boundscheck': False,
    'wraparound': False,
    'nonecheck': False,
    'cdivision': True,
    'embedsignature': False,  # Don't include docstrings
    'binding': False,  # Don't generate binding code
}

setup(
    name="PDFHarvest",
    version="1.0.0",
    author="PDF Harvest Team",
    description="PDF invoice data extraction tool",
    ext_modules=cythonize(
        extensions,
        compiler_directives=compiler_directives,
        annotate=False  # Don't generate .html annotation files
    ),
    cmdclass={'build_ext': build_ext},
    zip_safe=False,
)
