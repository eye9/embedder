@echo off
REM Batch Excel Processor Startup Script for Windows

if "%1"=="" (
    echo Usage: start_batch_processor.bat [web^|worker^|beat] [options]
    echo.
    echo Commands:
    echo   web     - Start the web server
    echo   worker  - Start a Celery worker
    echo   beat    - Start Celery beat scheduler
    echo.
    echo Options:
    echo   --config CONFIG_FILE  - Path to configuration file
    echo   --host HOST          - Host to bind web server to
    echo   --port PORT          - Port to bind web server to
    echo   --log-level LEVEL    - Logging level (DEBUG, INFO, WARNING, ERROR)
    exit /b 1
)

python start_batch_processor.py %*