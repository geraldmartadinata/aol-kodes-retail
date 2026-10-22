# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pandas>=2.2.0",
#     "rich>=13.7.0",
# ]
# ///
"""
Build data/retail.db (portable SQLite copy of the 3NF schema) from the five cleaned CSVs in data/processed/.

The schema comes from sql/schema.sql and the cleaning from imputer.py (single source of truth). This script deliberately does no
cleaning, so the CSVs, retail.db, the SQL scripts and the documentation can never disagree.

Run order:   python imputer.py --all     ->  python scripts/build_retail_db.py
"""
import re
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console(highlight=False)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

SCHEMA_SQL = PROJECT_ROOT / "sql" / "schema.sql"


def load_ddl() -> str:
    """Use sql/schema.sql as the single source of truth (PostgreSQL syntax -> SQLite with two harmless rewrites)."""
    ddl = SCHEMA_SQL.read_text(encoding="utf-8")
    ddl = re.sub(r"\s+CASCADE;", ";", ddl)                       # SQLite has no DROP ... CASCADE
    ddl = ddl.replace("CREATE OR REPLACE VIEW", "CREATE VIEW")    # SQLite has no CREATE OR REPLACE VIEW
    return "PRAGMA foreign_keys = ON;\n" + ddl


FILES = [  # (table, csv name) - parents first so foreign keys are satisfied during load
    ("customer", "customers.csv"),
    ("product", "products.csv"),
    ("inventory", "inventory.csv"),
    ("invoice", "invoices.csv"),
    ("invoice_line", "invoice_lines.csv"),
]


def main(data_dir: Path = PROJECT_ROOT / "data" / "processed", db_path: Path = PROJECT_ROOT / "data" / "retail.db"):
    start = time.time()
    missing = [n for _, n in FILES if not (data_dir / n).exists()]
    if missing:
        console.print(f"[bold red]Missing CSV(s) in {data_dir}:[/bold red] {', '.join(missing)}")
        console.print("Run [cyan]python imputer.py --all[/cyan] first.")
        sys.exit(1)

    console.print(Panel(f"Source CSVs : [cyan]{data_dir}[/cyan]\nTarget DB   : [cyan]{db_path}[/cyan]",
                        title="[bold green]KoDes Retail - SQLite builder[/bold green]", box=box.ROUNDED))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.executescript(load_ddl())
    summary = Table(title="Loaded tables", box=box.ROUNDED)
    summary.add_column("Table")
    summary.add_column("Rows", justify="right")
    for table, name in FILES:
        df = pd.read_csv(data_dir / name, dtype=str, keep_default_na=False)   # keep the text 'N/A' (payment_method)
        df.to_sql(table, conn, if_exists="append", index=False, chunksize=100_000)
        summary.add_row(table, f"{len(df):,}")
    conn.commit()

    bad = conn.execute("PRAGMA foreign_key_check").fetchall()
    conn.close()
    console.print(summary)
    console.print(f"Foreign-key violations: [bold]{len(bad)}[/bold]")
    console.print(f"[bold green]Done in {time.time() - start:.1f}s - {db_path} ({db_path.stat().st_size / 1_048_576:.1f} MB)[/bold green]")


if __name__ == "__main__":
    main()