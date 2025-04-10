@echo off
echo Building PDF Harvest (Standard Version)...
echo.

python build_protected.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo Build failed. See error messages above.
    pause
    exit /b 1
)

echo.
echo Build completed successfully!
echo The executable is available in the dist/PDFHarvest directory.
echo.
echo Users will need to activate the software with a license key.
echo Use the license_generator.py tool to create license keys for your users.
echo.
pause
