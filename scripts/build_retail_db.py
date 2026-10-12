# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pandas>=2.2.0",
#     "openpyxl>=3.1.2",
#     "rich>=13.7.0",
# ]
# ///

import sys
import time
import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console(highlight=False)

def execute_pipeline():
    start_time = time.time()
    raw_path = Path("data/raw/online_retail_data.xlsx")
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)
    sqlite_db_path = Path("data/retail.db")

    console.print(Panel(
        f"[bold white]Raw Dataset:[/bold white] [cyan]{raw_path}[/cyan]\n"
        f"[bold white]Processed CSV Directory:[/bold white] [cyan]{processed_dir}[/cyan]\n"
        f"[bold white]Target SQLite Database:[/bold white] [cyan]{sqlite_db_path}[/cyan]\n"
        "[bold white]Pipeline Standard:[/bold white] 3NF Relational Architecture (Single Guest Account Model)",
        title="[bold green]KoDes Retail - Data Cleansing, 3NF Normalization & DB Generator[/bold green]",
        box=box.ROUNDED
    ))

    # =========================================================================
    # STAGE 1: INGESTION
    # =========================================================================
    console.print("\n[bold yellow]Stage 1: Ingesting Raw Dataset...[/bold yellow]")
    df_raw = pd.read_excel(raw_path, sheet_name=0)
    total_raw = len(df_raw)
    console.print(f" [bold green][OK][/bold green] Ingested {total_raw:,} records.")

    # =========================================================================
    # STAGE 2: DELETION STEPS (Strict Deletion Budget ≤ 10%)
    # =========================================================================
    console.print("\n[bold yellow]Stage 2: Executing Deletion Steps (B.1 & B.2)...[/bold yellow]")
    
    # Step 1: Remove exact 8-column duplicates
    n_exact_dups = df_raw.duplicated().sum()
    df = df_raw.drop_duplicates().copy()
    console.print(f" [bold green][Step 1][/bold green] Purged {n_exact_dups:,} exact duplicates ({n_exact_dups/total_raw*100:.2f}% of raw).")

    # Standardize string representations
    df['Invoice'] = df['Invoice'].astype(str).str.strip()
    df['StockCode'] = df['StockCode'].astype(str).str.strip().str.upper()
    df['Country'] = df['Country'].astype(str).str.strip()

    # Step 2: Non-product / Admin StockCode exact match
    admin_stockcodes = {
        'POST', 'DOT', 'M', 'C2', 'D', 'S', 'BANK CHARGES', 'ADJUST', 
        'AMAZONFEE', 'DCGS0058', 'DCGS0068', 'DCGS0069', 'DCGS0070', 'DCGS0076',
        'DCGSSGIRL', 'DCGSSBOY', 'PADS', 'TEST', 'B', 'CRUK'
    }
    is_admin = df['StockCode'].isin(admin_stockcodes) | df['StockCode'].str.startswith('GIFT_0001_')

    # Step 3: Missing Description
    is_missing_desc = df['Description'].isna() | (df['Description'].astype(str).str.strip() == '')

    # Step 4: Missing Customer ID Non-UK
    is_non_uk_missing_cust = df['Customer ID'].isna() & (df['Country'] != 'United Kingdom')

    # Union without double-count
    union_delete_mask = is_admin | is_missing_desc | is_non_uk_missing_cust
    overlap_count = (is_admin.astype(int) + is_missing_desc.astype(int) + is_non_uk_missing_cust.astype(int) > 1).sum()
    total_union_deleted = union_delete_mask.sum()

    console.print(f"   • Administrative StockCodes (gross): {is_admin.sum():,}")
    console.print(f"   • Missing Descriptions (gross): {is_missing_desc.sum():,}")
    console.print(f"   • Non-UK Missing Customer IDs (gross): {is_non_uk_missing_cust.sum():,}")
    console.print(f"   • Overlapping rows (>1 category): {overlap_count:,}")
    console.print(f" [bold green][Step 2-4][/bold green] Union rows purged: {total_union_deleted:,}")

    total_deleted = n_exact_dups + total_union_deleted
    budget_pct = (total_deleted / total_raw) * 100
    console.print(f" [bold cyan][Summary][/bold cyan] Total rows purged: {total_deleted:,} ({budget_pct:.2f}% of raw | Remaining budget: {10.0 - budget_pct:.2f}%).")

    df_clean = df[~union_delete_mask].copy()
    console.print(f" [bold green][OK][/bold green] Retained active rows: {len(df_clean):,}")

    # =========================================================================
    # STAGE 3: CORRECTION STEPS (B.3)
    # =========================================================================
    console.print("\n[bold yellow]Stage 3: Executing Correction & Resolution Steps (B.3)...[/bold yellow]")

    # 1. Multi-timestamp invoices: assign MIN(InvoiceDate)
    df_clean['InvoiceDate'] = pd.to_datetime(df_clean['InvoiceDate'])
    inv_min_dates = df_clean.groupby('Invoice')['InvoiceDate'].transform('min')
    multi_ts_invoices = (df_clean.groupby('Invoice')['InvoiceDate'].nunique() > 1).sum()
    df_clean['InvoiceDate'] = inv_min_dates
    console.print(f" [bold green][Correction 1][/bold green] Normalized timestamps across {multi_ts_invoices} multi-timestamp invoices via MIN(InvoiceDate).")

    # 2. Multi-description StockCode: majority mode
    df_clean['Description'] = df_clean['Description'].astype(str).str.strip().str.upper()
    stock_mode_desc = (
        df_clean[df_clean['Description'].str.len() > 1]
        .groupby('StockCode')['Description']
        .agg(lambda s: s.mode()[0] if not s.empty else 'UNLISTED ITEM')
        .to_dict()
    )
    df_clean['Description'] = df_clean['StockCode'].map(stock_mode_desc).fillna(df_clean['Description'])
    console.print(f" [bold green][Correction 2][/bold green] Standardized official product descriptions via statistical mode per StockCode.")

    # 3. Impute Price == 0 on legitimate items (Quantity > 0)
    valid_prices = df_clean[df_clean['Price'] > 0]
    stock_avg_price = valid_prices.groupby('StockCode')['Price'].mean().to_dict()
    price_zero_mask = (df_clean['Price'] == 0) & (df_clean['Quantity'] > 0)
    n_price_zero = price_zero_mask.sum()
    df_clean.loc[price_zero_mask, 'Price'] = df_clean.loc[price_zero_mask, 'StockCode'].map(stock_avg_price).fillna(0.00).round(2)
    console.print(f" [bold green][Correction 3][/bold green] Imputed prices on {n_price_zero:,} legitimate items (Price=0) with respective StockCode mean price.")

    # 4. Single Guest Account (customer_id = 0) & Registered Customer majority Country
    df_clean['Customer_ID_Clean'] = df_clean['Customer ID'].fillna(0).astype(int)
    cust_majority_country = (
        df_clean[df_clean['Customer_ID_Clean'] > 0]
        .groupby('Customer_ID_Clean')['Country']
        .agg(lambda s: s.mode()[0] if not s.empty else 'United Kingdom')
        .to_dict()
    )
    cust_majority_country[0] = 'United Kingdom' # Single guest account UK
    df_clean['Customer_Primary_Country'] = df_clean['Customer_ID_Clean'].map(cust_majority_country)
    console.print(f" [bold green][Correction 4][/bold green] Assigned Single Guest Account (customer_id = 0, UK) and resolved customer country via mode.")

    # 5. Status & Quantity Handling
    is_c_invoice = df_clean['Invoice'].str.startswith('C')
    is_loss_line = (~is_c_invoice) & (df_clean['Quantity'] < 0)

    line_status = pd.Series('Completed', index=df_clean.index)
    line_status[is_c_invoice] = 'Cancelled'
    line_status[is_loss_line] = 'Loss'
    df_clean['Line_Status'] = line_status

    # Invoice-level majority status
    inv_majority_status = df_clean.groupby('Invoice')['Line_Status'].agg(lambda s: s.mode()[0]).to_dict()
    df_clean['Invoice_Status'] = df_clean['Invoice'].map(inv_majority_status)

    # Qty -> ABS for Cancelled as specified in document B.3 #3
    df_clean.loc[is_c_invoice, 'Quantity'] = df_clean.loc[is_c_invoice, 'Quantity'].abs()
    console.print(f" [bold green][Correction 5][/bold green] Partitioned order statuses ('Completed', 'Cancelled', 'Loss') and normalized cancelled quantities to absolute values.")

    # =========================================================================
    # STAGE 4: 3NF RELATIONAL DECONSTRUCTION
    # =========================================================================
    console.print("\n[bold yellow]Stage 4: Normalizing into 3NF Relational Tables...[/bold yellow]")

    # 1. CUSTOMER
    cust_df = df_clean[['Customer_ID_Clean', 'Customer_Primary_Country']].drop_duplicates(subset=['Customer_ID_Clean']).copy()
    cust_df.rename(columns={'Customer_ID_Clean': 'customer_id', 'Customer_Primary_Country': 'country'}, inplace=True)
    cust_df['customer_type'] = cust_df['customer_id'].apply(lambda cid: 'Guest' if cid == 0 else 'Registered')
    cust_df.sort_values(by='customer_id', inplace=True)

    # 2. PRODUCT
    valid_prod_prices = df_clean[df_clean['Price'] > 0]
    stock_catalog_price = valid_prod_prices.groupby('StockCode')['Price'].median().to_dict()
    prod_df = df_clean[['StockCode', 'Description']].drop_duplicates(subset=['StockCode']).copy()
    prod_df.rename(columns={'StockCode': 'stock_code', 'Description': 'description'}, inplace=True)
    prod_df['current_unit_price'] = prod_df['stock_code'].apply(lambda s: round(stock_catalog_price.get(s, 0.00), 2))
    prod_df.sort_values(by='stock_code', inplace=True)

    # 3. INVENTORY
    inventory_df = prod_df[['stock_code']].copy()
    inventory_df['stock_level'] = 1000
    inventory_df['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 4. INVOICE
    inv_df = df_clean[['Invoice', 'InvoiceDate', 'Customer_ID_Clean', 'Country', 'Invoice_Status']].drop_duplicates(subset=['Invoice']).copy()
    inv_df.rename(columns={
        'Invoice': 'invoice_no',
        'InvoiceDate': 'invoice_date',
        'Customer_ID_Clean': 'customer_id',
        'Country': 'country',
        'Invoice_Status': 'status'
    }, inplace=True)
    inv_df.sort_values(by='invoice_date', inplace=True)

    # 5. INVOICE_LINE
    items_df = pd.DataFrame({
        'invoice_no': df_clean['Invoice'],
        'stock_code': df_clean['StockCode'],
        'quantity': df_clean['Quantity'].astype(int),
        'unit_price_at_sale': df_clean['Price'].round(2)
    })
    items_df.reset_index(drop=True, inplace=True)
    items_df['line_id'] = items_df.index + 1
    items_df = items_df[['line_id', 'invoice_no', 'stock_code', 'quantity', 'unit_price_at_sale']]

    # =========================================================================
    # STAGE 5: EXPORT CSVs
    # =========================================================================
    console.print("\n[bold yellow]Stage 5: Writing Production CSV Files...[/bold yellow]")
    cust_df.to_csv(processed_dir / "customers.csv", index=False)
    prod_df.to_csv(processed_dir / "products.csv", index=False)
    inventory_df.to_csv(processed_dir / "inventory.csv", index=False)
    inv_df.to_csv(processed_dir / "invoices.csv", index=False)
    items_df.to_csv(processed_dir / "invoice_lines.csv", index=False)
    console.print(" [bold green][OK][/bold green] 5 CSV files successfully written.")

    # =========================================================================
    # STAGE 6: GENERATE SQLITE DATABASE (data/retail.db)
    # =========================================================================
    console.print("\n[bold yellow]Stage 6: Instantiating Accessible SQLite Database...[/bold yellow]")
    if sqlite_db_path.exists():
        sqlite_db_path.unlink()

    conn = sqlite3.connect(sqlite_db_path)
    cur = conn.cursor()

    # DDL
    cur.executescript("""
    CREATE TABLE customer (
        customer_id     INTEGER PRIMARY KEY,
        customer_type   TEXT NOT NULL CHECK(customer_type IN ('Registered', 'Guest')),
        country         TEXT NOT NULL
    );

    CREATE TABLE product (
        stock_code          TEXT PRIMARY KEY,
        description         TEXT NOT NULL,
        current_unit_price  REAL NOT NULL DEFAULT 0.00
    );

    CREATE TABLE inventory (
        stock_code      TEXT PRIMARY KEY,
        stock_level     INTEGER NOT NULL DEFAULT 1000,
        last_updated    TEXT NOT NULL,
        FOREIGN KEY (stock_code) REFERENCES product(stock_code)
    );

    CREATE TABLE invoice (
        invoice_no      TEXT PRIMARY KEY,
        invoice_date    TEXT NOT NULL,
        customer_id     INTEGER NOT NULL,
        country         TEXT NOT NULL,
        status          TEXT NOT NULL CHECK(status IN ('Completed', 'Cancelled', 'Loss')),
        FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
    );

    CREATE TABLE invoice_line (
        line_id             INTEGER PRIMARY KEY,
        invoice_no          TEXT NOT NULL,
        stock_code          TEXT NOT NULL,
        quantity            INTEGER NOT NULL,
        unit_price_at_sale  REAL NOT NULL,
        FOREIGN KEY (invoice_no) REFERENCES invoice(invoice_no),
        FOREIGN KEY (stock_code) REFERENCES product(stock_code)
    );

    CREATE INDEX idx_invoice_cust ON invoice(customer_id);
    CREATE INDEX idx_invoice_status ON invoice(status);
    CREATE INDEX idx_line_inv ON invoice_line(invoice_no);
    CREATE INDEX idx_line_prod ON invoice_line(stock_code);

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
    LEFT JOIN invoice i 
        ON c.customer_id = i.customer_id 
       AND i.status = 'Completed'
    LEFT JOIN invoice_line l 
        ON i.invoice_no = l.invoice_no
    GROUP BY 
        c.customer_id, 
        c.customer_type, 
        c.country;
    """)

    # Fast bulk insertion
    cust_df.to_sql('customer', conn, if_exists='append', index=False)
    prod_df.to_sql('product', conn, if_exists='append', index=False)
    inventory_df.to_sql('inventory', conn, if_exists='append', index=False)
    inv_df.to_sql('invoice', conn, if_exists='append', index=False)
    items_df.to_sql('invoice_line', conn, if_exists='append', index=False)

    conn.commit()
    conn.close()
    console.print(f" [bold green][OK][/bold green] Database active at [cyan]{sqlite_db_path}[/cyan] ({sqlite_db_path.stat().st_size / (1024*1024):.2f} MB).")

    # =========================================================================
    # SUMMARY TABLE
    # =========================================================================
    summary = Table(title="[bold green]Final Entity Statistics[/bold green]", box=box.ROUNDED)
    summary.add_column("Table Name", style="cyan")
    summary.add_column("Primary Key", style="yellow")
    summary.add_column("Row Count", justify="right", style="green")
    summary.add_row("customer", "customer_id", f"{len(cust_df):,}")
    summary.add_row("product", "stock_code", f"{len(prod_df):,}")
    summary.add_row("inventory", "stock_code", f"{len(inventory_df):,}")
    summary.add_row("invoice", "invoice_no", f"{len(inv_df):,}")
    summary.add_row("invoice_line", "line_id", f"{len(items_df):,}")
    console.print(summary)

    status_counts = inv_df['status'].value_counts()
    console.print(f"\n[bold white]Invoice Status Distribution:[/bold white]")
    for st, count in status_counts.items():
        console.print(f" • {st}: {count:,} ({count/len(inv_df)*100:.1f}%)")

    console.print(f"\n[bold green]Pipeline finished in {time.time() - start_time:.2f} seconds![/bold green]")

if __name__ == "__main__":
    execute_pipeline()
