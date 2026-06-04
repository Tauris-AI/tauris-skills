$ErrorActionPreference = "Stop"

Write-Host "PHDWin Cowork MCP install check"
Write-Host "Package: $PSScriptRoot"
Write-Host ""

Write-Host "Checking Python launcher..."
py -3.12-32 --version

Write-Host ""
Write-Host "Installing Python requirements..."
py -3.12-32 -m pip install -r "$PSScriptRoot\requirements.txt"

Write-Host ""
Write-Host "Checking pyodbc and FastMCP..."
py -3.12-32 -c "import pyodbc, fastmcp; print('pyodbc', pyodbc.version); print('fastmcp ok')"

Write-Host ""
Write-Host "Installed ODBC drivers visible to Python 3.12 32-bit:"
py -3.12-32 -c "import pyodbc; print('\n'.join(pyodbc.drivers()))"

Write-Host ""
Write-Host "If the Clarion / TopSpeed / SoftVelocity driver is not listed above, get it here:"
Write-Host "https://softvelocity.myshopify.com/"
Write-Host "Then rerun this check with a Python bitness that matches the installed driver."

Write-Host ""
Write-Host "Compiling MCP server..."
py -3.12-32 -m py_compile "$PSScriptRoot\scripts\phdwin_mcp_server.py"

Write-Host ""
Write-Host "Done. If no Clarion / TopSpeed driver appears above, Cowork will start but native PHDWin-to-Aries source inspection will not work until the matching ODBC driver is visible to this Python."
Write-Host "SQLite review mode does not require the Clarion driver once a phdwin_to_aries_review.sqlite file has been created."
Write-Host "Next: open Cowork -> Settings -> Developer -> Edit Config, then merge cowork_config.example.json."
