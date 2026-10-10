@echo off
echo ============================================================
echo   STAUFF TASK ORCHESTRATOR - BUILD SCRIPT
echo   Building standalone executables (v4)...
echo ============================================================
echo.

:: Clean previous builds
echo [1/4] Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
echo       Done.
echo.

:: Build Employee App (Task Updater)
echo [2/4] Building Employee App (Stauff Task Updater v4)...
echo       This may take a few minutes...
pyinstaller task_updater_v4.spec --noconfirm 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       [ERROR] Failed to build Employee App!
    pause
    exit /b 1
)
echo       Employee App built successfully!
echo.

:: Build Admin Dashboard
echo [3/4] Building Admin Dashboard (Stauff Admin Dashboard v4)...
echo       This may take a few minutes...
pyinstaller admin_dashboard_v4.spec --noconfirm 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       [ERROR] Failed to build Admin Dashboard!
    pause
    exit /b 1
)
echo       Admin Dashboard built successfully!
echo.

:: Summary
echo [4/4] Build complete!
echo.
echo ============================================================
echo   OUTPUT FILES:
echo   Employee App:  dist\Stauff Task Updater v4.exe
echo   Admin App:     dist\Stauff Admin Dashboard v4.exe
echo ============================================================
echo.
pause
