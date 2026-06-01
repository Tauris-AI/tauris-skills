@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
set "DATA_DIR=%ROOT%data"

echo PHDWinv2_MCP Cowork restart / cleanup
echo Package: %ROOT%
echo.

echo Closing Claude / Cowork processes...
taskkill /IM Claude.exe /F >nul 2>nul
taskkill /IM claude.exe /F >nul 2>nul

echo Stopping phdwin-v2 MCP Python processes...
for /f "skip=1 tokens=2 delims=," %%P in ('wmic process where "commandline like '%%phdwin_mcp_server.py%%'" get processid /format:csv 2^>nul') do (
    if not "%%P"=="" (
        echo   killing PID %%P
        taskkill /PID %%P /F >nul 2>nul
    )
)

echo.
echo Restarting Cowork VM service...
sc stop CoworkVMService >nul 2>nul
timeout /t 3 /nobreak >nul
sc start CoworkVMService
timeout /t 2 /nobreak >nul
sc query CoworkVMService

echo.
echo Removing SQLite lock / fragment files under %DATA_DIR%...
if exist "%DATA_DIR%" (
    del /s /q "%DATA_DIR%\*.sqlite-journal" >nul 2>nul
    del /s /q "%DATA_DIR%\*.sqlite-wal" >nul 2>nul
    del /s /q "%DATA_DIR%\*.sqlite-shm" >nul 2>nul
    del /s /q "%DATA_DIR%\*.db-journal" >nul 2>nul
    del /s /q "%DATA_DIR%\*.db-wal" >nul 2>nul
    del /s /q "%DATA_DIR%\*.db-shm" >nul 2>nul
    del /s /q "%DATA_DIR%\*.tmp" >nul 2>nul
)

if /I "%~1"=="/DELETE_REVIEW_DB" (
    echo.
    echo WARNING: deleting review SQLite databases under %DATA_DIR%\review...
    del /q "%DATA_DIR%\review\*.sqlite" >nul 2>nul
    del /q "%DATA_DIR%\review\*.db" >nul 2>nul
)

echo.
echo Done.
echo Reopen Claude / Cowork from the Start Menu, then retry the export.
echo.
echo To also delete review SQLite DBs, run:
echo   %~nx0 /DELETE_REVIEW_DB

endlocal
