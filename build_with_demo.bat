@echo off
echo Building PDF Harvest with Demo License...
echo.

python build_protected.py --demo-license

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
echo The application includes a 30-day demo license with a limit of 10 files for bulk processing.
echo.
pause
