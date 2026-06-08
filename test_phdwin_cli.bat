@echo off
setlocal

set "LOG=%~dp0phdwin_cli_test.log"
set "UTILS_EXE=C:\Program Files (x86)\Tauris\PHDWin Utils\phdwin-utils.exe"
set "CONVERTER_EXE=C:\Program Files (x86)\Tauris\PHDWin Converter CLI\Tauris.PhdWin.Cli.exe"

echo PHDWin CLI smoke test > "%LOG%"
echo Started: %DATE% %TIME% >> "%LOG%"
echo. >> "%LOG%"

echo Testing installed PHDWin command-line tools...
echo Log: "%LOG%"
echo.

call :test_exe "PHDWin Utils" "%UTILS_EXE%"
call :test_exe "PHDWin Converter CLI" "%CONVERTER_EXE%"

echo.
echo Done. Review the log at:
echo "%LOG%"
exit /b 0

:test_exe
set "NAME=%~1"
set "EXE=%~2"

echo ==== %NAME% ==== >> "%LOG%"
echo Path: %EXE% >> "%LOG%"

if exist "%EXE%" goto exe_found

echo MISSING: %EXE%
echo Result: MISSING >> "%LOG%"
echo. >> "%LOG%"
exit /b 0

:exe_found

echo Found: %EXE%
echo Result: FOUND >> "%LOG%"

echo. >> "%LOG%"
echo --help output: >> "%LOG%"
"%EXE%" --help >> "%LOG%" 2>&1
echo Exit code: %ERRORLEVEL% >> "%LOG%"

echo. >> "%LOG%"
echo help output: >> "%LOG%"
"%EXE%" help >> "%LOG%" 2>&1
echo Exit code: %ERRORLEVEL% >> "%LOG%"

echo. >> "%LOG%"
echo --version output: >> "%LOG%"
"%EXE%" --version >> "%LOG%" 2>&1
echo Exit code: %ERRORLEVEL% >> "%LOG%"

echo. >> "%LOG%"
exit /b 0
