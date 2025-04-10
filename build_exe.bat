@echo off
echo Building PDF Harvest Executable...
echo.

REM Check if Python is available
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python not found. Please install Python 3.8 or higher.
    exit /b 1
)

REM Parse command line arguments
set DEMO_LICENSE=
set SKIP_CLEAN=
set SKIP_DEPS=

:parse_args
if "%~1"=="" goto :end_parse_args
if /i "%~1"=="--demo-license" set DEMO_LICENSE=--demo-license
if /i "%~1"=="--skip-clean" set SKIP_CLEAN=--skip-clean
if /i "%~1"=="--skip-deps" set SKIP_DEPS=--skip-deps
shift
goto :parse_args
:end_parse_args

REM Build the executable
python build_protected.py %DEMO_LICENSE% %SKIP_CLEAN% %SKIP_DEPS%

if %ERRORLEVEL% neq 0 (
    echo.
    echo Build failed. See error messages above.
    exit /b 1
)

echo.
echo Build completed successfully!
echo The executable is available in the dist/PDFHarvest directory.
echo.

REM Check if the executable was created
if exist "dist\PDFHarvest\PDFHarvest.exe" (
    echo You can run the application by executing dist\PDFHarvest\PDFHarvest.exe
) else (
    echo Warning: Executable not found at the expected location.
)

echo.
pause
