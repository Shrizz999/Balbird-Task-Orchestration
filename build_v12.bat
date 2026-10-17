@echo off
echo ============================================================
echo   BALBIRD TASK ORCHESTRATOR - BUILD SCRIPT (v12 PRODUCTION)
echo   Building standalone executables (Crash-Proof Release)...
echo ============================================================
echo.

:: Clean previous build cache (leave dist intact, just overwrite target exes)
if exist build rmdir /s /q build

:: Build Employee App (Task Updater v12)
echo [1/2] Building Employee App (Stauff Task Updater v12)...
echo       This may take a few minutes...
pyinstaller task_updater_v12.spec --noconfirm 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       [ERROR] Failed to build Employee App v12!
    pause
    exit /b 1
)
echo       Employee App v12 built successfully!
if exist build rmdir /s /q build
echo.

:: Build Admin Dashboard (v12)
echo [2/2] Building Admin Dashboard (Stauff Admin Dashboard v12)...
echo       This may take a few minutes...
pyinstaller admin_dashboard_v12.spec --noconfirm 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       [ERROR] Failed to build Admin Dashboard v12!
    pause
    exit /b 1
)
echo       Admin Dashboard v12 built successfully!
if exist build rmdir /s /q build
echo.

:: Sign Executables with Balbird Corporate Certificate
echo [3/3] Signing Executables with Balbird Industries Certificate...
powershell -NoProfile -ExecutionPolicy Bypass -File sign_exes.ps1
echo.

echo ============================================================
echo   BUILD & SIGNING COMPLETE!
echo   OUTPUT FILES:
echo   Employee App:  dist\Stauff Task Updater v12.exe
echo   Admin App:     dist\Stauff Admin Dashboard v12.exe
echo   Certificate:   dist\Balbird_Certificate.cer
echo ============================================================
pause
