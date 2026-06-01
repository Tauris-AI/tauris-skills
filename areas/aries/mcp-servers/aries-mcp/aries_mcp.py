"""
ARIES MCP Server
Exposes ARIES .accdb/.mdb database tools to Claude/Cowork via the MCP protocol.
Requires: pip install fastmcp pyodbc
Requires: Microsoft ACE ODBC driver (64-bit)
"""

import pyodbc
import subprocess
import os
import datetime
from fastmcp import FastMCP

mcp = FastMCP("aries-mcp")


def _validate_access_path(db_path: str) -> str:
    ext = os.path.splitext(db_path)[1].lower()
    if ext not in {".accdb", ".mdb"}:
        raise ValueError(f"Expected an .accdb or .mdb path, got: {db_path}")
    return db_path


def _get_conn_str(db_path: str) -> str:
    db_path = _validate_access_path(db_path)
    return (
        r"Driver={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"Dbq={db_path};"
        "ExtendedAnsiSQL=1;"
    )


# ---------------------------------------------------------------------------
# READ TOOLS
# ---------------------------------------------------------------------------

@mcp.tool()
def list_tables(db_path: str) -> list[str]:
    """List all user tables in an ARIES .accdb or .mdb database."""
    conn = pyodbc.connect(_get_conn_str(db_path))
    try:
        cursor = conn.cursor()
        tables = [
            row.table_name
            for row in cursor.tables(tableType="TABLE")
            if not row.table_name.startswith("MSys")
        ]
        return sorted(tables)
    finally:
        conn.close()


@mcp.tool()
def get_columns(db_path: str, table_name: str) -> list[dict]:
    """Get column names and data types for a table in an ARIES .accdb or .mdb database."""
    conn = pyodbc.connect(_get_conn_str(db_path))
    try:
        cursor = conn.cursor()
        cols = [
            {"column": row.column_name, "type": row.type_name}
            for row in cursor.columns(table=table_name)
        ]
        return cols
    finally:
        conn.close()


@mcp.tool()
def read_table(db_path: str, table_name: str, limit: int = 2000) -> list[dict]:
    """Read rows from a table. Use limit=0 for all rows."""
    conn = pyodbc.connect(_get_conn_str(db_path))
    try:
        cursor = conn.cursor()
        if limit and limit > 0:
            sql = f"SELECT TOP {limit} * FROM [{table_name}]"
        else:
            sql = f"SELECT * FROM [{table_name}]"
        cursor.execute(sql)
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


@mcp.tool()
def query(db_path: str, sql: str) -> list[dict]:
    """
    Run an arbitrary SELECT query against an ARIES .accdb or .mdb using Access SQL.
    Use TOP n (not LIMIT), and % wildcards (not *) for LIKE.
    COUNT(DISTINCT col) is not supported — aggregate in Python instead.
    """
    conn = pyodbc.connect(_get_conn_str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# WRITE TOOLS
# ---------------------------------------------------------------------------

@mcp.tool()
def execute(db_path: str, sql: str) -> str:
    """
    Run an INSERT, UPDATE, DELETE, or DDL statement against an ARIES .accdb or .mdb.
    Returns row count affected.
    Always backup_table before using this on production data.
    """
    conn = pyodbc.connect(_get_conn_str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        return f"OK — {cursor.rowcount} row(s) affected"
    finally:
        conn.close()


@mcp.tool()
def backup_table(db_path: str, table_name: str) -> str:
    """
    Create a timestamped backup of a table within the same database.
    Backup is named <table_name>_bak_YYYYMMDD_HHMMSS.
    """
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{table_name}_bak_{ts}"
    conn = pyodbc.connect(_get_conn_str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * INTO [{backup_name}] FROM [{table_name}]")
        conn.commit()
        return f"Backup created: {backup_name}"
    finally:
        conn.close()


@mcp.tool()
def setup_import_db(client_db_path: str) -> str:
    """
    Prepare a client .accdb or .mdb for ComboCurve import.
    Drops AC_ONELINE table if present.
    """
    conn = pyodbc.connect(_get_conn_str(client_db_path))
    try:
        cursor = conn.cursor()
        tables = [row.table_name for row in cursor.tables(tableType="TABLE")]
        dropped = []
        if "AC_ONELINE" in tables:
            cursor.execute("DROP TABLE [AC_ONELINE]")
            conn.commit()
            dropped.append("AC_ONELINE")
        msg = "setup_import_db complete."
        if dropped:
            msg += f" Dropped: {', '.join(dropped)}."
        else:
            msg += " AC_ONELINE not present — nothing dropped."
        return msg
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# FILE / ADMIN TOOLS
# ---------------------------------------------------------------------------

@mcp.tool()
def unblock_file(file_path: str) -> str:
    """Remove Windows download Zone.Identifier block from a file."""
    result = subprocess.run(
        ["powershell", "-Command", f"Unblock-File -Path '{file_path}'"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return f"Unblocked: {file_path}"
    return f"Error: {result.stderr.strip()}"


@mcp.tool()
def compact_repair(db_path: str) -> str:
    """
    Compact & repair an .accdb or .mdb in-place using MS Access COM automation.
    Requires Microsoft Access to be installed.
    The database must not be open in ARIES during this operation.
    """
    db_path = _validate_access_path(db_path)
    script = f"""
$access = New-Object -ComObject Access.Application
$access.Visible = $false
$tmp = '{db_path}.tmp_compact'
try {{
    $access.CompactRepair('{db_path}', $tmp)
    Copy-Item $tmp '{db_path}' -Force
    Remove-Item $tmp -Force
    Write-Output "OK"
}} finally {{
    $access.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($access) | Out-Null
}}
"""
    result = subprocess.run(["powershell", "-Command", script], capture_output=True, text=True)
    if "OK" in result.stdout:
        return f"Compact & repair complete: {db_path}"
    return f"Error: {result.stderr.strip() or result.stdout.strip()}"


@mcp.tool()
def convert_to_accdb(mdb_path: str) -> str:
    """
    Convert a .mdb file to .accdb using MS Access COM automation.
    Requires Microsoft Access to be installed.
    Output file is written alongside the source with .accdb extension.
    """
    if os.path.splitext(mdb_path)[1].lower() != ".mdb":
        raise ValueError(f"Expected a .mdb path, got: {mdb_path}")
    accdb_path = os.path.splitext(mdb_path)[0] + ".accdb"
    script = f"""
$access = New-Object -ComObject Access.Application
$access.Visible = $false
try {{
    $access.ConvertAccessProject('{mdb_path}', '{accdb_path}', 12)
    Write-Output "OK"
}} finally {{
    $access.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($access) | Out-Null
}}
"""
    result = subprocess.run(["powershell", "-Command", script], capture_output=True, text=True)
    if "OK" in result.stdout:
        return f"Converted: {accdb_path}"
    return f"Error: {result.stderr.strip() or result.stdout.strip()}"


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
