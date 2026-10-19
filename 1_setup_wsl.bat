@echo off
title PipeGen WSL2 Automated Installer
echo ========================================================
echo   CraftifAI PipeGen Environment Setup (Drive D: Target)
echo ========================================================
echo.

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Administrator permissions required.
    echo [!] Requesting administrative privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo [+] Running with Administrator privileges.
echo.

:: Step 1: Create WSL Directory on Drive D
if not exist "D:\WSL" (
    echo [+] Creating D:\WSL for high-capacity storage...
    mkdir "D:\WSL"
)

:: Step 2: Enable Windows Subsystem for Linux and Virtual Machine Platform
echo [+] Enabling WSL and VirtualMachinePlatform features...
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

:: Step 3: Install or Update WSL2 with Ubuntu
echo [+] Installing Ubuntu 22.04 on WSL2...
wsl.exe --install -d Ubuntu-22.04 --no-launch

echo.
echo ========================================================
echo   WSL2 features have been activated!
echo   If Windows requires a restart, please restart now.
echo ========================================================
pause
