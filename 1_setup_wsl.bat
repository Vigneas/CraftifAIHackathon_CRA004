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
    echo [!] Please right-click this file and select 'Run as administrator'.
    pause
    exit /b
)

echo [+] Verified Administrator privileges!
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
echo [+] Installing Ubuntu on WSL2...
wsl.exe --install -d Ubuntu-22.04 --no-launch

echo.
echo ========================================================
echo   [SUCCESS] WSL2 features and Ubuntu have been installed!
echo   If Windows requires a system restart, restart now.
echo ========================================================
pause
