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

echo Stopping phdwinv2 MCP Python processes...
for /f "skip=1 tokens=2 delims=," %%P in ('wmic process where "commandline like '%%phdwinv2_mcp_server.py%%'" get processid /format:csv 2^>nul') do (
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

echo.
echo Done. Reopen Claude / Cowork from the Start Menu.

endlocal
