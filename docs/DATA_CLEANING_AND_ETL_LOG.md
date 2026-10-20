# KoDes Retail Data Cleansing and ETL Pipeline Documentation

This technical log documents the data cleaning, imputation, and relational normalization pipeline executed on the KoDes Retail transaction dataset.

The pipeline enforces a strict separation between row deletions (governed by a 10% maximum deletion budget) and in-place data corrections. All operations are deterministic, vectorized via Pandas, and produce normalized Third Normal Form (3NF) relational tables with zero null values and complete referential integrity.

---

## 1. Pipeline Overview and Architecture

The source dataset consists of historical transactions recorded between 2009 and 2011. In its raw form, the data is unnormalized, containing mixed timestamp granularities, inconsistent product descriptions for identical SKUs, zero-price anomalies, unauthenticated guest checkouts, and non-merchandise administrative entries.

The ETL pipeline resolves these issues across three sequential stages:
1. Deletion Budget Execution: Prunes unrecoverable administrative entries, blank descriptions, non-UK anonymous records, and exact row duplicates while remaining within the 10% budget constraint.
2. Data Correction and Imputation: Resolves multi-timestamp orders, standardizes product titles, imputes missing catalog prices, assigns a unified guest account, and classifies order lifecycle statuses.
3. 3NF Relational Deconstruction: Normalizes clean transactions into five relational entities: customer, product, inventory, invoice, and invoice_line.

---

## 2. Raw Dataset Dimensions and Excel Row Ceiling

A key finding during initial profiling relates to the total row count of the source spreadsheet:

* The reference Online Retail II dataset historically contains 1,067,371 rows when distributed across two Excel sheets (2009-2010 and 2010-2011).
* The provided single-sheet file (`data/raw/online_retail_data.xlsx`) contains exactly 1,048,575 data records plus 1 header row, totaling 1,048,576 rows.
* 1,048,576 rows represents the hard physical row limit ($2^{20}$) of a Microsoft Excel (.xlsx) worksheet. The remaining rows (~18,796 lines) were truncated during the initial file export to a single Excel sheet.

All deletion budget calculations, union operations, and relational integrity ratios scale consistently and proportionally on this complete single-sheet dataset.

---

## 3. Data Alteration Audit Log

### 3.1 Deletion Budget Summary (Ceiling: 10.0%)

Row deletions are strictly restricted to unrecoverable or non-merchandise records. The table below outlines row reductions relative to the raw count of 1,048,575 rows:

| Step | Alteration Category | Rows Purged | Percentage of Raw | Remaining Budget | Engineering Rationale |
|:---|:---|:---:|:---:|:---:|:---|
| 1 | Exact duplicate rows (identical across all 8 columns) | 34,150 | 3.26% | 6.74% | Eliminates identical recorded lines caused by transmission or logging duplication. |
| 2-4 | Union of Admin SKUs, blank descriptions, and non-UK blank Customer IDs | 12,954 | 1.23% | 5.51% | Purges non-physical postal/banking fees and unidentifiable international records without double-counting 90 overlapping rows. |
| Total | Net rows purged | 47,104 | 4.49% | 5.51% | Fully compliant with the 10% deletion constraint. |

Gross category breakdown for Steps 2 to 4 prior to union overlap deduplication:
* Administrative StockCodes (`POST`, `DOT`, `M`, `C2`, `D`, `BANK CHARGES`, etc.): 5,834 rows.
* Blank or empty descriptions: 4,265 rows.
* Non-UK missing Customer IDs: 2,945 rows.
* Multi-category overlap: 90 rows belonged to more than one deletion category.

Retained transaction rows ready for normalization: 1,001,471 records (95.51% of raw data).

---

### 3.2 Correction and Imputation Pipeline

Instead of purging records with partial anomalies, the pipeline applies deterministic data imputation and standardization:

1. Canonical Timestamp Resolution:  
   83 invoice numbers contained multiple conflicting timestamps across their item lines. The pipeline resolves each invoice to a single authoritative timestamp using the minimum timestamp observed (`MIN(InvoiceDate)`).

2. Product Description Standardization:  
   SKUs with drifting or variant descriptions are standardized to the statistical mode (the most frequently recorded description) for each respective `StockCode`.

3. Zero-Price Imputation:  
   953 lines represented authentic physical retail transactions (`Quantity > 0`) but recorded a unit price of 0.00. The pipeline imputes these prices using the arithmetic mean price of the corresponding `StockCode` across valid positive sales.

4. Single Guest Account Architecture:  
   Anonymous transactions originating from the United Kingdom are assigned to a unified synthetic guest record:
   * `customer_id = 0`, `customer_type = 'Guest'`, `country = 'United Kingdom'`.
   * This design satisfies referential integrity constraints, ensuring that `invoice.customer_id` remains `NOT NULL` while retaining more than 2.8 million GBP in authentic commercial sales volume.

5. Order Lifecycle Status and Quantity Handling:  
   * Invoices prefixed with 'C' indicate cancellations. The order status is set to `'Cancelled'`, and quantities are normalized to absolute positive values (`Quantity = ABS(Quantity)`).
   * Non-prefixed lines with negative quantities represent damaged stock, write-offs, or warehouse adjustments. Their status is set to `'Loss'`.
   * Standard sales transactions with positive quantities are assigned the status `'Completed'`.
   * The final invoice header status is determined through a majority mode vote across its constituent lines.

---

## 4. Final Relational Table Statistics

The normalized output tables contain the following record counts in production:

| Table | Primary Key | Total Records | Role and Description |
|:---|:---|:---:|:---|
| customer | customer_id | 5,861 | Master customer directory (5,860 registered members + 1 guest account). |
| product | stock_code | 4,751 | Official SKU merchandise catalog with modal descriptions. |
| inventory | stock_code | 4,751 | Warehouse stock tracker (1:1 with product). |
| invoice | invoice_no | 47,164 | Order transaction headers with canonical dates and statuses. |
| invoice_line | line_id | 1,001,471 | Detailed atomic transaction line items. |

### Invoice Status Distribution:
* Completed: 39,117 invoices (82.9%)
* Cancelled: 7,308 invoices (15.5%)
* Loss: 739 invoices (1.6%)

---

## 5. Implementation Code Highlights

### 5.1 Deletion Budget Union Logic (Pandas Vectorized)

```python
# Step 1: Remove exact row duplicates across all columns
df = df_raw.drop_duplicates().copy()

# Step 2-4: Identify administrative SKUs, missing descriptions, and non-UK anonymous checkouts
admin_stockcodes = {
    'POST', 'DOT', 'M', 'C2', 'D', 'S', 'BANK CHARGES', 'ADJUST', 
    'AMAZONFEE', 'DCGS0058', 'DCGS0068', 'DCGS0069', 'DCGS0070', 'DCGS0076',
    'DCGSSGIRL', 'DCGSSBOY', 'PADS', 'TEST', 'B', 'CRUK'
}
is_admin = df['StockCode'].isin(admin_stockcodes) | df['StockCode'].str.startswith('GIFT_0001_')
is_missing_desc = df['Description'].isna() | (df['Description'].astype(str).str.strip() == '')
is_non_uk_missing_cust = df['Customer ID'].isna() & (df['Country'] != 'United Kingdom')

# Union mask without double-counting overlap
union_delete_mask = is_admin | is_missing_desc | is_non_uk_missing_cust
df_clean = df[~union_delete_mask].copy()
```

### 5.2 Single Guest Account and Zero-Price Imputation

```python
# Map anonymous UK transactions to single guest ID 0
df_clean['Customer_ID_Clean'] = df_clean['Customer ID'].fillna(0).astype(int)

# Impute zero prices on legitimate items using SKU mean price
valid_prices = df_clean[df_clean['Price'] > 0]
stock_avg_price = valid_prices.groupby('StockCode')['Price'].mean().to_dict()
price_zero_mask = (df_clean['Price'] == 0) & (df_clean['Quantity'] > 0)
df_clean.loc[price_zero_mask, 'Price'] = (
    df_clean.loc[price_zero_mask, 'StockCode']
    .map(stock_avg_price)
    .fillna(0.00)
    .round(2)
)
```

---

## 6. Analytical Query Validation

The local SQLite database (`data/retail.db`, 68.14 MB) was evaluated against production reporting queries to confirm data cleanliness and query performance:

### Query 3: Top 5 Regional Sales Breakdown (Completed Transactions Only)

| Country | Completed Invoices | Total Sales Revenue | Average Line Value |
|:---|---:|---:|---:|
| United Kingdom | 35,938 | $17,352,685.15 | $19.12 |
| EIRE | 521 | $581,078.21 | $38.57 |
| Netherlands | 214 | $539,077.55 | $110.02 |
| Germany | 739 | $377,027.70 | $24.28 |
| France | 578 | $305,158.88 | $23.81 |

### Query 4: Top 5 VIP High-Spenders (Registered Accounts Only)

| Customer ID | Account Type | Country | Calculated Total Spend |
|:---|:---|:---|---:|
| 18102 | Registered | United Kingdom | $569,501.50 |
| 14646 | Registered | Netherlands | $516,055.66 |
| 14156 | Registered | EIRE | $303,069.88 |
| 14911 | Registered | EIRE | $266,704.92 |
| 17450 | Registered | United Kingdom | $245,788.65 |

---

## 7. Database Verification Guidelines

1. SQLite Inspection:  
   Open `data/retail.db` directly using any SQLite-compatible database client (DBeaver, DataGrip, or VSCode SQLite Viewer) to query physical tables and `view_customer_rfm`.
2. PostgreSQL Cloud Ingestion:  
   Deploy DDL statements from `sql/schema.sql` to initialize tables, constraints, and views on PostgreSQL. Then stream processed CSVs from `data/processed/` using the native COPY command or via `scripts/sync_supabase.py --push`.
