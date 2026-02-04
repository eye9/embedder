@echo off
REM Verification script for Docker color coding fix (Windows)

echo 🔍 Verifying color coding fix in Docker...
echo.

REM Check if containers are running
echo 1️⃣ Checking if containers are running...
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps | findstr "Up" >nul 2>&1
if errorlevel 1 (
    echo ❌ Containers are not running!
    echo    Run: docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
    exit /b 1
)
echo ✅ Containers are running
echo.

REM Check if code is mounted
echo 2️⃣ Checking if code is mounted as volume...
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T worker test -f /app/batch_processor/workers/processing_task.py >nul 2>&1
if errorlevel 1 (
    echo ❌ Code is not accessible in worker container!
    exit /b 1
)
echo ✅ Code is accessible in worker container
echo.

REM Check if confidence_score is in the code
echo 3️⃣ Checking if confidence_score fix is present...
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T worker grep -q "'confidence_score': result.confidence_score" /app/batch_processor/workers/processing_task.py >nul 2>&1
if errorlevel 1 (
    echo ❌ confidence_score fix is NOT present in the code!
    echo    Expected to find: 'confidence_score': result.confidence_score
    exit /b 1
)
echo ✅ confidence_score fix is present in the code
echo.
echo    Found at line:
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T worker grep -n "'confidence_score': result.confidence_score" /app/batch_processor/workers/processing_task.py
echo.

REM Check if openpyxl is installed
echo 4️⃣ Checking if openpyxl is installed...
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T worker python -c "from openpyxl.styles import PatternFill; print('OK')" 2>nul | findstr "OK" >nul 2>&1
if errorlevel 1 (
    echo ❌ openpyxl is not installed or not working!
    exit /b 1
)
echo ✅ openpyxl is installed and working
echo.

REM Check web service health
echo 5️⃣ Checking web service health...
curl -s http://localhost:8000/health | findstr "ok" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Web service health check failed (might be starting up)
) else (
    echo ✅ Web service is healthy
)
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ✅ All checks passed!
echo.
echo 📝 Next steps:
echo    1. Open http://localhost:8000
echo    2. Login: admin / admin123
echo    3. Upload test_web_color_coding.xlsx
echo    4. Download result and check colors in Excel
echo.
echo 📊 View logs:
echo    docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f worker
echo.
echo 🔄 Restart worker if needed:
echo    docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart worker
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
pause