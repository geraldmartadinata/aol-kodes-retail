import time
from pathlib import Path
import pandas as pd
import numpy as np

def run():
    raw_path = Path("data/raw/online_retail_data.xlsx")
    print(f"Loading {raw_path}...")
    df = pd.read_excel(raw_path, sheet_name=0)
    print(f"Total raw rows: {len(df):,}")
    
    # 1. Exact duplicates
    n_dups = df.duplicated().sum()
    print(f"Exact duplicates: {n_dups:,}")
    df_clean = df.drop_duplicates().copy()
    print(f"After Step 1 (dedup): {len(df_clean):,}")
    
    # Standardize string fields
    df_clean['Invoice'] = df_clean['Invoice'].astype(str).str.strip()
    df_clean['StockCode'] = df_clean['StockCode'].astype(str).str.strip().str.upper()
    df_clean['Country'] = df_clean['Country'].astype(str).str.strip()
    
    # Known admin StockCodes
    admin_stockcodes = [
        'POST', 'DOT', 'M', 'C2', 'D', 'S', 'BANK CHARGES', 'ADJUST', 
        'AMAZONFEE', 'DCGS0058', 'DCGS0068', 'DCGS0069', 'DCGS0070', 'DCGS0076',
        'DCGSSGIRL', 'DCGSSBOY', 'PADS', 'TEST', 'B', 'CRUK'
    ]
    # Check exact match on admin stockcodes vs general non-product
    is_admin = df_clean['StockCode'].isin(admin_stockcodes) | df_clean['StockCode'].str.contains('GIFT_0001_', na=False)
    print(f"Step 2 - StockCode admin gross: {is_admin.sum():,}")
    
    # Step 3 - Description missing gross
    is_missing_desc = df_clean['Description'].isna() | (df_clean['Description'].astype(str).str.strip() == '')
    print(f"Step 3 - Description missing gross: {is_missing_desc.sum():,}")
    
    # Step 4 - Customer ID missing non-UK gross
    is_missing_cust = df_clean['Customer ID'].isna()
    is_non_uk_missing_cust = is_missing_cust & (df_clean['Country'] != 'United Kingdom')
    print(f"Step 4 - Customer ID non-UK missing gross: {is_non_uk_missing_cust.sum():,}")
    
    # Union of 2, 3, 4
    union_delete = is_admin | is_missing_desc | is_non_uk_missing_cust
    print(f"Union (Steps 2-4) to delete: {union_delete.sum():,}")
    
    # Overlap count
    overlap = (is_admin.astype(int) + is_missing_desc.astype(int) + is_non_uk_missing_cust.astype(int)) > 1
    print(f"Overlap rows (>1 category): {overlap.sum():,}")
    
    # Apply deletion
    df_retained = df_clean[~union_delete].copy()
    print(f"Retained rows for SQL: {len(df_retained):,}")
    
    # Customer ID check in retained rows:
    retained_missing_cust = df_retained['Customer ID'].isna()
    print(f"Retained missing Customer ID (all UK): {retained_missing_cust.sum():,}")
    print(f"Countries of retained missing Customer ID: {df_retained[retained_missing_cust]['Country'].unique()}")
    
    # Unique invoices
    print(f"Unique Invoices: {df_retained['Invoice'].nunique():,}")
    print(f"Unique StockCodes: {df_retained['StockCode'].nunique():,}")
    
    # Check C-invoices vs normal vs negative
    is_c = df_retained['Invoice'].str.startswith('C')
    print(f"C-prefix invoices lines: {is_c.sum():,}")
    
    neg_qty_non_c = (~is_c) & (df_retained['Quantity'] < 0)
    print(f"Negative Qty (non-C, i.e. Loss): {neg_qty_non_c.sum():,}")
    
    price_zero = (df_retained['Price'] == 0) & (df_retained['Quantity'] > 0)
    print(f"Price == 0 and Qty > 0 (goods to impute): {price_zero.sum():,}")

if __name__ == "__main__":
    run()
