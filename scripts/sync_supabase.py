# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "psycopg2-binary>=2.9.9",
#     "python-dotenv>=1.0.1",
#     "rich>=13.7.0",
#     "pandas>=2.2.0",
# ]
# ///

import os
import sys
import time
import argparse
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
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

def get_connection_url(cli_url: str = None) -> str:
    load_dotenv(PROJECT_ROOT / ".env")
    url = cli_url or os.getenv("SUPABASE_DB_URL")
    if not url:
        console.print("[bold red]Error:[/bold red] SUPABASE_DB_URL is not provided.")
        console.print(f"Please set SUPABASE_DB_URL in {PROJECT_ROOT / '.env'} or pass via --url argument.")
        sys.exit(1)
    return url.strip()

def test_connection(url: str):
    console.print("\n[bold cyan]Testing Supabase PostgreSQL Connection...[/bold cyan]")
    try:
        conn = psycopg2.connect(url, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        ver = cur.fetchone()[0]
        cur.close()
        conn.close()
        console.print(Panel(
            f"[bold green]Connection Successful![/bold green]\n\n"
            f"[white]{ver}[/white]",
            title="[bold green]Supabase Online[/bold green]",
            box=box.ROUNDED
        ))
        return True
    except Exception as e:
        console.print(f"[bold red]Connection Failed:[/bold red] {e}")
        console.print("\n[dim]Tips:\n- Make sure the password inside the URL is correct.\n- If your network does not support direct IPv6, use the Connection Pooler URL from Supabase Settings -> Database.[/dim]")
        return False

def push_to_supabase(url: str):
    start_time = time.time()
    console.print(Panel(
        "[bold white]Operation:[/bold white] Local 3NF Tables & CSVs -> Supabase Cloud DB\n"
        "[bold white]Target:[/bold white] Live PostgreSQL Cloud Instance",
        title="[bold cyan]Sync Action: PUSH to Supabase[/bold cyan]",
        box=box.ROUNDED
    ))

    schema_file = PROJECT_ROOT / "sql" / "schema.sql"
    data_dir = PROJECT_ROOT / "data" / "processed"

    if not schema_file.exists():
        console.print(f"[bold red]Missing:[/bold red] {schema_file}")
        sys.exit(1)

    console.print("\n[bold yellow]Step 1: Connecting to Supabase...[/bold yellow]")
    conn = psycopg2.connect(url)
    conn.autocommit = False
    cur = conn.cursor()

    # Step 2: Execute DDL Schema
    console.print("[bold yellow]Step 2: Deploying 3NF DDL Schema (schema.sql)...[/bold yellow]")
    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # Filter out client-side \copy and load data comments if any
    cur.execute(schema_sql)
    conn.commit()
    console.print(" [bold green][OK][/bold green] Tables, constraints, and views created successfully.")

    # Step 3: Fast Ingestion via COPY
    console.print("\n[bold yellow]Step 3: Fast Streaming CSV Data into Supabase Tables...[/bold yellow]")
    tables = [
        ("customer", data_dir / "customers.csv", "(customer_id, customer_name, email, phone_number, address, city, customer_type, country)"),
        ("product", data_dir / "products.csv", "(stock_code, description, category, current_unit_price)"),
        ("inventory", data_dir / "inventory.csv", "(stock_code, stock_level, reorder_level, last_updated)"),
        ("invoice", data_dir / "invoices.csv", "(invoice_no, invoice_date, customer_id, country, status, payment_method)"),
        ("invoice_line", data_dir / "invoice_lines.csv", "(line_id, invoice_no, stock_code, quantity, unit_price_at_sale)"),
    ]

    for table_name, csv_path, cols in tables:
        if not csv_path.exists():
            console.print(f" [bold red][FAIL][/bold red] Missing file: {csv_path.name}")
            conn.rollback()
            sys.exit(1)

        t_start = time.time()
        with open(csv_path, "r", encoding="utf-8") as f:
            copy_sql = f"COPY {table_name} {cols} FROM STDIN WITH (FORMAT csv, HEADER true);"
            cur.copy_expert(copy_sql, f)
        conn.commit()
        console.print(f" [bold green][OK][/bold green] Loaded [cyan]{table_name}[/cyan] from {csv_path.name} in {time.time() - t_start:.2f}s")

    # Step 4: Verification
    console.print("\n[bold yellow]Step 4: Verifying Live Record Counts on Supabase...[/bold yellow]")
    summary = Table(title="[bold green]Live Supabase Cloud Database Summary[/bold green]", box=box.ROUNDED)
    summary.add_column("Table Name", style="cyan")
    summary.add_column("Row Count on Supabase", justify="right", style="green")

    for table_name, _, _ in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table_name};")
        cnt = cur.fetchone()[0]
        summary.add_row(table_name, f"{cnt:,}")

    console.print(summary)
    cur.close()
    conn.close()

    console.print(Panel(
        f"[bold green]ALL DATA SUCCESSFULLY PUSHED TO SUPABASE![/bold green]\n"
        f"Duration: {time.time() - start_time:.2f} seconds\n"
        "Your teammates can now immediately view the live data on the Supabase Dashboard or connect via DBeaver!",
        border_style="green",
        box=box.DOUBLE
    ))

def pull_from_supabase(url: str):
    start_time = time.time()
    console.print(Panel(
        "[bold white]Operation:[/bold white] Supabase Cloud DB -> Local CSVs & SQLite DB\n"
        "[bold white]Target:[/bold white] Keeping local workspace synchronized with cloud edits",
        title="[bold cyan]Sync Action: PULL from Supabase[/bold cyan]",
        box=box.ROUNDED
    ))

    import pandas as pd
    data_dir = PROJECT_ROOT / "data" / "processed"
    sqlite_db_path = PROJECT_ROOT / "data" / "retail.db"

    conn = psycopg2.connect(url)
    tables = ["customer", "product", "inventory", "invoice", "invoice_line"]
    csv_names = {
        "customer": "customers.csv",
        "product": "products.csv",
        "inventory": "inventory.csv",
        "invoice": "invoices.csv",
        "invoice_line": "invoice_lines.csv"
    }

    # Open SQLite to sync local db
    sq_conn = sqlite3.connect(sqlite_db_path)

    for tbl in tables:
        console.print(f"Pulling [cyan]{tbl}[/cyan] from Supabase...")
        df = pd.read_sql_query(f"SELECT * FROM {tbl};", conn)
        # Save to CSV
        csv_file = data_dir / csv_names[tbl]
        df.to_csv(csv_file, index=False)
        # Update SQLite table
        df.to_sql(tbl, sq_conn, if_exists='replace', index=False)
        console.print(f" [bold green][OK][/bold green] Synced {len(df):,} rows for {tbl}")

    sq_conn.close()
    conn.close()
    console.print(f"\n[bold green]Local files and retail.db synchronized with Supabase in {time.time() - start_time:.2f}s![/bold green]")

def main():
    parser = argparse.ArgumentParser(description="Supabase Cloud Synchronization CLI for KoDes Retail")
    parser.add_argument("--url", help="Supabase Database Connection String")
    parser.add_argument("--test", action="store_true", help="Test connection to Supabase")
    parser.add_argument("--push", action="store_true", help="Push local schema & 3NF CSV data to Supabase")
    parser.add_argument("--pull", action="store_true", help="Pull latest data from Supabase to local CSV & SQLite")
    args = parser.parse_args()

    url = get_connection_url(args.url)

    if args.push:
        push_to_supabase(url)
    elif args.pull:
        pull_from_supabase(url)
    elif args.test:
        test_connection(url)
    else:
        # Default test then ask
        if test_connection(url):
            console.print("\n[bold yellow]Options:[/bold yellow]")
            console.print(" Run [cyan]uv run scripts/sync_supabase.py --push[/cyan] to push data to Supabase.")
            console.print(" Run [cyan]uv run scripts/sync_supabase.py --pull[/cyan] to pull data from Supabase.")

if __name__ == "__main__":
    main()