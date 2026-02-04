@echo off
echo ==========================================
echo Telegram AI Bot - Full Docker Startup
echo ==========================================
echo.

REM Check if .env exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo Please copy .env.example to .env and configure it.
    echo.
    echo   copy .env.example .env
    echo.
    pause
    exit /b 1
)

echo Building and starting all services...
docker-compose up -d --build

echo.
echo ==========================================
echo All services started!
echo ==========================================
echo.
echo Services:
echo   - Bot: Running (check logs with: docker-compose logs -f bot)
echo   - API: http://localhost:8000
echo   - Admin Panel: http://localhost:3000
echo   - PostgreSQL: localhost:5432
echo   - Redis: localhost:6379
echo.
echo Admin credentials:
echo   Username: admin
echo   Password: admin123
echo.
echo Useful commands:
echo   - View bot logs:     docker-compose logs -f bot
echo   - View API logs:     docker-compose logs -f api
echo   - View worker logs:  docker-compose logs -f worker
echo   - Stop all:          docker-compose down
echo   - Restart all:       docker-compose restart
echo.
pause
