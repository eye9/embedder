@echo off
REM Quick restart script for development environment (Windows)

echo 🔄 Restarting development environment...
echo.

REM Stop containers
echo ⏹️  Stopping containers...
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

REM Clear Redis cache (optional)
echo 🗑️  Clearing Redis cache...
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d redis
timeout /t 2 /nobreak >nul
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T redis redis-cli FLUSHALL
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

REM Start containers with build
echo 🚀 Starting containers with fresh build...
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

REM Wait for services to be ready
echo ⏳ Waiting for services to start...
timeout /t 5 /nobreak >nul

REM Show status
echo.
echo 📊 Container status:
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps

echo.
echo ✅ Development environment restarted!
echo.
echo 📝 Useful commands:
echo   View logs:        docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
echo   View worker logs: docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f worker
echo   Restart worker:   docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart worker
echo   Stop all:         docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
echo.
echo 🌐 Web interface: http://localhost:8000
echo 🔑 Login: admin / admin123
echo.
pause