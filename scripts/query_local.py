# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "rich>=13.7.0",
#     "psycopg2-binary>=2.9.9",
#     "python-dotenv>=1.0.1",
# ]
# ///

import os
import sys
import sqlite3
import argparse
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Enforce UTF-8 on Windows Consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(highlight=False)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "retail.db"

def list_tables_sqlite(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY type, name;")
    items = cur.fetchall()
    tbl = Table(title="Database Tables & Views (Local SQLite)", box=box.ROUNDED)
    tbl.add_column("Type", style="yellow")
    tbl.add_column("Name", style="cyan")
    tbl.add_column("Row Count", justify="right", style="green")

    for item in items:
        name = item[0]
        try:
            cur.execute(f"SELECT COUNT(*) FROM {name};")
            count = f"{cur.fetchone()[0]:,}"
        except Exception:
            count = "N/A"
        item_type = "VIEW" if name.startswith("view_") else "TABLE"
        tbl.add_row(item_type, name, count)
    console.print(tbl)

def describe_table_sqlite(cur, table_name):
    try:
        cur.execute(f"PRAGMA table_info({table_name});")
        cols = cur.fetchall()
        if not cols:
            console.print(f"[bold red]Table '{table_name}' not found.[/bold red]")
            return
        tbl = Table(title=f"Schema Definition: {table_name}", box=box.ROUNDED)
        tbl.add_column("Col #", justify="right", style="dim")
        tbl.add_column("Column Name", style="cyan")
        tbl.add_column("Data Type", style="yellow")
        tbl.add_column("Not Null?", justify="center", style="magenta")
        tbl.add_column("PK?", justify="center", style="green")

        for col in cols:
            # col: (cid, name, type, notnull, dflt_value, pk)
            tbl.add_row(
                str(col[0] + 1),
                col[1],
                col[2],
                "YES" if col[3] else "NO",
                "PRIMARY KEY" if col[5] else ""
            )
        console.print(tbl)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

def list_tables_pg(cur):
    query = """
    SELECT table_type, table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    ORDER BY table_type, table_name;
    """
    cur.execute(query)
    items = cur.fetchall()
    tbl = Table(title="Database Tables & Views (Supabase PostgreSQL Cloud)", box=box.ROUNDED)
    tbl.add_column("Type", style="yellow")
    tbl.add_column("Name", style="cyan")
    tbl.add_column("Row Count", justify="right", style="green")

    for item_type, name in items:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {name};")
            count = f"{cur.fetchone()[0]:,}"
        except Exception:
            count = "N/A"
        t_label = "VIEW" if "VIEW" in item_type else "TABLE"
        tbl.add_row(t_label, name, count)
    console.print(tbl)

def describe_table_pg(cur, table_name):
    query = f"""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = '{table_name}'
    ORDER BY ordinal_position;
    """
    cur.execute(query)
    cols = cur.fetchall()
    if not cols:
        console.print(f"[bold red]Table '{table_name}' not found.[/bold red]")
        return
    tbl = Table(title=f"Schema Definition: {table_name} (PostgreSQL)", box=box.ROUNDED)
    tbl.add_column("Col #", justify="right", style="dim")
    tbl.add_column("Column Name", style="cyan")
    tbl.add_column("Data Type", style="yellow")
    tbl.add_column("Nullable?", justify="center", style="magenta")

    for idx, col in enumerate(cols, 1):
        tbl.add_row(str(idx), col[0], col[1], col[2])
    console.print(tbl)

def run_console(is_cloud: bool = False):
    if is_cloud:
        import psycopg2
        load_dotenv(PROJECT_ROOT / ".env")
        url = os.getenv("SUPABASE_DB_URL")
        if not url:
            console.print("[bold red]Error:[/bold red] SUPABASE_DB_URL not found in .env!")
            sys.exit(1)
        console.print("[yellow]Connecting to Supabase PostgreSQL Cloud...[/yellow]")
        conn = psycopg2.connect(url)
        db_type = "POSTGRESQL (SUPABASE)"
        loc_str = "aws-0-ap-southeast-1.pooler.supabase.com:5432"
    else:
        if not DB_PATH.exists():
            console.print(f"[bold red]Database not found at {DB_PATH}![/bold red]")
            console.print("Run 'uv run scripts/build_retail_db.py' first to generate it.")
            sys.exit(1)
        conn = sqlite3.connect(DB_PATH)
        db_type = "SQLITE (LOCAL)"
        loc_str = str(DB_PATH)

    cur = conn.cursor()

    console.print(Panel(
        f"[bold white]Connected To:[/bold white] [bold green]{db_type}[/bold green]\n"
        f"[bold white]Target Location:[/bold white] [cyan]{loc_str}[/cyan]\n\n"
        "[bold yellow]Quick Commands:[/bold yellow]\n"
        " • [bold cyan]tables[/bold cyan]            : Show all tables, views, and live row counts\n"
        " • [bold cyan]desc <table_name>[/bold cyan] : Inspect column names, data types & constraints\n"
        " • [bold cyan]preview <table_name>[/bold cyan]: View the first 10 rows of a table\n"
        " • [bold cyan]<SQL Query>[/bold cyan]      : Execute any SQL query (e.g. SELECT * FROM customer LIMIT 5)\n"
        " • [bold cyan]exit[/bold cyan]              : Exit the CLI console",
        title="[bold green]KoDes Retail — Interactive Database CLI[/bold green]",
        box=box.ROUNDED
    ))

    while True:
        try:
            cmd = console.input("\n[bold cyan]SQL>[/bold cyan] ").strip()
            if not cmd:
                continue
            if cmd.lower() in ['exit', 'quit', 'q']:
                console.print("[green]Exited database console.[/green]")
                break

            cmd_lower = cmd.lower().rstrip(';')

            # Helper 1: list tables
            if cmd_lower in ['tables', 'show tables', '\\dt']:
                if is_cloud:
                    list_tables_pg(cur)
                else:
                    list_tables_sqlite(cur)
                continue

            # Helper 2: describe table
            if cmd_lower.startswith('desc ') or cmd_lower.startswith('schema '):
                t_name = cmd_lower.split()[1]
                if is_cloud:
                    describe_table_pg(cur, t_name)
                else:
                    describe_table_sqlite(cur, t_name)
                continue

            # Helper 3: preview table
            if cmd_lower.startswith('preview '):
                t_name = cmd_lower.split()[1]
                cmd = f"SELECT * FROM {t_name} LIMIT 10;"

            # Generic SQL Execution
            cur.execute(cmd)
            if cur.description:
                rows = cur.fetchall()
                col_names = [d[0] for d in cur.description]
                if not rows:
                    console.print("[yellow]0 rows returned.[/yellow]")
                    continue

                table = Table(box=box.ROUNDED, show_lines=False)
                for col in col_names:
                    table.add_column(col, style="cyan")

                # Show up to 50 rows
                for row in rows[:50]:
                    table.add_row(*[str(val) if val is not None else "[dim]NULL[/dim]" for val in row])

                console.print(table)
                if len(rows) > 50:
                    console.print(f"[dim]Showing first 50 of {len(rows):,} total rows.[/dim]")
                else:
                    console.print(f"[dim]Total: {len(rows):,} rows.[/dim]")
            else:
                conn.commit()
                console.print(f"[green]Command executed successfully.[/green]")

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]SQL Error:[/bold red] {e}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive Database CLI for KoDes Retail")
    parser.add_argument("--cloud", "--supabase", action="store_true", help="Connect to Supabase PostgreSQL Cloud instead of local SQLite")
    args = parser.parse_args()
    run_console(is_cloud=args.cloud)
