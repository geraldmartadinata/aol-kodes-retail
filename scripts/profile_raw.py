# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pandas>=2.2.0",
#     "openpyxl>=3.1.2",
#     "rich>=13.7.0",
# ]
# ///

import time
from pathlib import Path
import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()

def profile():
    raw_path = Path("data/raw/online_retail_data.xlsx")
    console.print(f"[bold cyan]Reading raw dataset: {raw_path}...[/bold cyan]")
    start = time.time()
    
    # Read raw
    df = pd.read_excel(raw_path, sheet_name=0)
    console.print(f"Loaded {len(df):,} rows in {time.time() - start:.2f}s")
    console.print(f"Columns: {list(df.columns)}")
    
    # Check Step 1: Exact Duplicates
    dup_mask = df.duplicated()
    console.print(f"\n[bold yellow]1. Exact Duplicates:[/bold yellow] {dup_mask.sum():,} rows")
    
    df_no_dups = df.drop_duplicates().copy()
    console.print(f"Remaining after deduplication: {len(df_no_dups):,} rows")
    
    # Clean string columns for analysis
    df_no_dups['StockCode_clean'] = df_no_dups['StockCode'].astype(str).str.strip().str.upper()
    df_no_dups['Country_clean'] = df_no_dups['Country'].astype(str).str.strip()
    df_no_dups['Invoice_clean'] = df_no_dups['Invoice'].astype(str).str.strip()
    
    # Step 2-4: Identify categories
    # StockCode admin / non-product (e.g. POST, D, M, BANK CHARGES, etc.)
    # Let's inspect non-numeric or special StockCodes
    non_numeric_stock = df_no_dups[~df_no_dups['StockCode_clean'].str.match(r'^\d{5}')]
    console.print(f"\nNon-standard StockCode count: {len(non_numeric_stock):,}")
    console.print(f"Top non-standard StockCodes:\n{non_numeric_stock['StockCode_clean'].value_counts().head(15)}")
    
    # Description missing / blank
    missing_desc = df_no_dups['Description'].isna() | (df_no_dups['Description'].astype(str).str.strip() == '')
    console.print(f"\nMissing Description count: {missing_desc.sum():,}")
    
    # Customer ID missing
    missing_cust = df_no_dups['Customer ID'].isna()
    console.print(f"Missing Customer ID total: {missing_cust.sum():,}")
    
    missing_cust_non_uk = missing_cust & (df_no_dups['Country_clean'] != 'United Kingdom')
    missing_cust_uk = missing_cust & (df_no_dups['Country_clean'] == 'United Kingdom')
    console.print(f"Missing Customer ID (non-UK): {missing_cust_non_uk.sum():,}")
    console.print(f"Missing Customer ID (UK): {missing_cust_uk.sum():,}")

if __name__ == "__main__":
    profile()
