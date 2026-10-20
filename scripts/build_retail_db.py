# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pandas>=2.2.0",
#     "rich>=13.7.0",
# ]
# ///
"""
Build data/retail.db (portable SQLite copy of the 3NF schema) from the five cleaned CSVs in data/processed/.

Cleaning/normalisation lives ONLY in imputer.py (single source of truth). This script deliberately does no
cleaning, so the CSVs, retail.db, the SQL scripts and the documentation can never disagree.

Run order:   python imputer.py --all     ->  python scripts/build_retail_db.py
"""
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

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE customer (
    customer_id     INTEGER PRIMARY KEY,
    customer_name   TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    phone           TEXT NOT NULL,
    customer_type   TEXT NOT NULL CHECK(customer_type IN ('Registered', 'Guest')),
    country         TEXT NOT NULL
);

CREATE TABLE product (
    stock_code          TEXT PRIMARY KEY,
    description         TEXT NOT NULL,
    current_unit_price  REAL NOT NULL DEFAULT 0.00 CHECK(current_unit_price >= 0)
);

CREATE TABLE inventory (
    stock_code      TEXT PRIMARY KEY,
    stock_level     INTEGER NOT NULL DEFAULT 1000,
    last_updated    TEXT NOT NULL,
    FOREIGN KEY (stock_code) REFERENCES product(stock_code) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE invoice (
    invoice_no      TEXT PRIMARY KEY,
    invoice_date    TEXT NOT NULL,
    customer_id     INTEGER NOT NULL,
    country         TEXT NOT NULL,
    status          TEXT NOT NULL CHECK(status IN ('Completed', 'Cancelled', 'Loss')),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE invoice_line (
    line_id             INTEGER PRIMARY KEY,
    invoice_no          TEXT NOT NULL,
    stock_code          TEXT NOT NULL,
    quantity            INTEGER NOT NULL CHECK(quantity > 0),
    unit_price_at_sale  REAL NOT NULL CHECK(unit_price_at_sale >= 0),
    FOREIGN KEY (invoice_no) REFERENCES invoice(invoice_no) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (stock_code) REFERENCES product(stock_code) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE INDEX idx_invoice_cust   ON invoice(customer_id);
CREATE INDEX idx_invoice_status ON invoice(status);
CREATE INDEX idx_line_inv       ON invoice_line(invoice_no);
CREATE INDEX idx_line_prod      ON invoice_line(stock_code);

CREATE VIEW view_customer_rfm AS
SELECT
    c.customer_id,
    c.customer_type,
    c.country,
    MIN(i.invoice_date)                                 AS first_purchase_date,
    MAX(i.invoice_date)                                 AS last_purchase_date,
    COUNT(DISTINCT i.invoice_no)                        AS total_completed_invoices,
    COALESCE(SUM(l.quantity * l.unit_price_at_sale), 0) AS total_lifetime_spend
FROM customer c
LEFT JOIN invoice i ON c.customer_id = i.customer_id AND i.status = 'Completed'
LEFT JOIN invoice_line l ON i.invoice_no = l.invoice_no
GROUP BY c.customer_id, c.customer_type, c.country;
"""

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
    conn.executescript(DDL)
    summary = Table(title="Loaded tables", box=box.ROUNDED)
    summary.add_column("Table")
    summary.add_column("Rows", justify="right")
    for table, name in FILES:
        df = pd.read_csv(data_dir / name)
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
