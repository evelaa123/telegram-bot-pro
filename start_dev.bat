@echo off
echo ==========================================
echo Telegram AI Bot - Development Startup
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

echo [1/3] Starting PostgreSQL and Redis...
docker-compose -f docker-compose.dev.yml up -d

echo.
echo [2/3] Waiting for databases to start...
timeout /t 5 /nobreak > nul

echo.
echo [3/3] Databases are ready!
echo.
echo ==========================================
echo Next steps:
echo ==========================================
echo.
echo 1. Install Python dependencies (if not done):
echo    pip install -r requirements.txt
echo.
echo 2. Initialize database (first time only):
echo    python scripts/init_db.py
echo.
echo 3. Run the bot:
echo    python main.py
echo.
echo 4. Run API (in separate terminal):
echo    python run_api.py
echo.
echo 5. Run worker for video (in separate terminal):
echo    python run_worker.py
echo.
echo 6. Admin panel (optional):
echo    cd admin-frontend
echo    npm install
echo    npm run dev
echo.
echo ==========================================
echo Ports:
echo   - PostgreSQL: localhost:5432
echo   - Redis: localhost:6379
echo   - API: localhost:8000
echo   - Admin: localhost:3000 (or 5173)
echo ==========================================
echo.
pause
