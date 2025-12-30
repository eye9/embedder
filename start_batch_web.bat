@echo off
echo Starting Batch Excel Processor Web Application...
echo.

REM Set the configuration file path
set BATCH_PROCESSOR_CONFIG=batch_processor_config.yaml

REM Check if config file exists
if not exist "%BATCH_PROCESSOR_CONFIG%" (
    echo Warning: batch_processor_config.yaml not found
    echo Using default configuration
    echo.
)

echo Configuration file: %BATCH_PROCESSOR_CONFIG%
echo.
echo Starting web server...
echo Access the web interface at: http://localhost:8000
echo.
echo Login credentials:
echo   Username: admin
echo   Password: admin123
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the web application
python -m uvicorn batch_processor.web.app:app --host 0.0.0.0 --port 8000 --reload

pause