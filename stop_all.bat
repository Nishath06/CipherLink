@echo off
title Stopping CipherLink and Chat App Services...
powershell -ExecutionPolicy Bypass -File "%~dp0stop_all.ps1"
pause
