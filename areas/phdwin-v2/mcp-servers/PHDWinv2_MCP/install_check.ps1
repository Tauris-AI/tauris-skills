$ErrorActionPreference = "Stop"

Write-Host "PHDWin v2 MCP install check"
Write-Host "Package: $PSScriptRoot"
Write-Host ""

Write-Host "Checking Python launcher..."
py -3.14 --version

Write-Host ""
Write-Host "Installing Python requirements..."
py -3.14 -m pip install -r "$PSScriptRoot\requirements.txt"

Write-Host ""
Write-Host "Checking pyodbc and FastMCP..."
py -3.14 -c "import pyodbc, fastmcp; print('pyodbc', pyodbc.version); print('fastmcp ok')"

Write-Host ""
Write-Host "Installed ODBC drivers visible to Python 3.14:"
py -3.14 -c "import pyodbc; print('\n'.join(pyodbc.drivers()))"

Write-Host ""
Write-Host "If the Clarion / TopSpeed / SoftVelocity driver is not listed above, get it here:"
Write-Host "https://softvelocity.myshopify.com/"

Write-Host ""
Write-Host "Compiling MCP server..."
py -3.14 -m py_compile "$PSScriptRoot\scripts\phdwinv2_mcp_server.py"

Write-Host ""
Write-Host "Done. SQLite review mode does not require the Clarion driver once a SQLite export exists."
