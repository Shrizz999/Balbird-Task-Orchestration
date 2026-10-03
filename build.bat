@echo off
echo ============================================================
echo   STAUFF TASK ORCHESTRATOR - BUILD SCRIPT
echo   Building standalone executables...
echo ============================================================
echo.

:: Clean previous builds
echo [1/4] Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
echo       Done.
echo.

:: Build Employee App (Task Updater)
echo [2/4] Building Employee App (Stauff Task Updater)...
echo       This may take a few minutes...
pyinstaller task_updater.spec --noconfirm 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       [ERROR] Failed to build Employee App!
    pause
    exit /b 1
)
echo       Employee App built successfully!
echo.

:: Build Admin Dashboard
echo [3/4] Building Admin Dashboard (Stauff Admin Dashboard)...
echo       This may take a few minutes...
pyinstaller admin_dashboard.spec --noconfirm 2>&1
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
echo   Employee App:  dist\Stauff Task Updater.exe
echo   Admin App:     dist\Stauff Admin Dashboard.exe
echo ============================================================
echo.
echo   IMPORTANT: Both .exe files must be placed in the SAME
echo   folder to share the extension_requests.json file for
echo   deadline extension requests to flow between them.
echo.
echo   The employee app also creates recent_task_updates.json
echo   next to its .exe for caching status changes.
echo ============================================================
echo.
pause
