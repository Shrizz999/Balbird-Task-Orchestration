@echo off
echo ============================================================
echo   BALBIRD TASK ORCHESTRATOR - BUILD SCRIPT (v11 PRODUCTION)
echo   Building standalone executables (Crash-Proof Release)...
echo ============================================================
echo.

:: Clean previous build cache (leave dist intact, just overwrite target exes)
if exist build rmdir /s /q build

:: Build Employee App (Task Updater v11)
echo [1/2] Building Employee App (Stauff Task Updater v11)...
echo       This may take a few minutes...
pyinstaller task_updater_v11.spec --noconfirm 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       [ERROR] Failed to build Employee App v11!
    pause
    exit /b 1
)
echo       Employee App v11 built successfully!
echo.

:: Build Admin Dashboard (v11)
echo [2/2] Building Admin Dashboard (Stauff Admin Dashboard v11)...
echo       This may take a few minutes...
pyinstaller admin_dashboard_v11.spec --noconfirm 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       [ERROR] Failed to build Admin Dashboard v11!
    pause
    exit /b 1
)
echo       Admin Dashboard v11 built successfully!
echo.

echo ============================================================
echo   BUILD COMPLETE!
echo   OUTPUT FILES:
echo   Employee App:  dist\Stauff Task Updater v11.exe
echo   Admin App:     dist\Stauff Admin Dashboard v11.exe
echo ============================================================
pause
