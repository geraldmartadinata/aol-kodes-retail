# KoDes Retail — Relational Database Overhaul (3NF)

[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17+-336791?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Supabase](https://img.shields.io/badge/Supabase-Cloud%20Database-3ECF8E?style=flat&logo=supabase&logoColor=white)](https://supabase.com/)
[![SQLite](https://img.shields.io/badge/SQLite-Local%203NF-003B57?style=flat&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An enterprise-grade database engineering project overhauling the unnormalized transactional spreadsheet data of **KoDes Retail** (an all-occasion gift specialist) into a production-ready, ACID-compliant **Third Normal Form (3NF)** relational database deployed on **PostgreSQL (Supabase)** and **SQLite**.

---

## 1. Background & Executive Overview

KoDes Retail previously operated on flat, denormalized transaction logs (`online_retail_data.xlsx`, containing over 1 million records). The legacy flat-file structure caused severe database anomalies:
* **Update & Redundancy Anomalies:** Product descriptions and catalog unit prices were repeated across hundreds of thousands of lines, causing drift and inconsistent descriptions for identical SKUs.
* **Deletion Anomalies:** Removing a transaction risked destroying catalog metadata for rare gift items.
* **Integrity Deficits:** Mixed timestamps within single invoices, drifting customer residency data, untracked inventory adjustments, and unindexed full-table scans.

This overhaul deconstructs the dataset into **five normalized 3NF relational entities**, enforces referential integrity constraints, institutes a deterministic data cleansing and imputation pipeline, deploys an automated inventory trigger, and syncs the entire dataset to a live **PostgreSQL (Supabase)** cloud cluster.

---

## 2. Relational Architecture (3NF Normalization)

The database strictly complies with **Third Normal Form (3NF)**: all non-key attributes are fully functionally dependent on the primary key, with zero transitive dependencies.

```text
       ┌──────────────┐                  ┌──────────────┐
       │   CUSTOMER   │                  │   PRODUCT    │
       ├──────────────┤                  ├──────────────┤
       │ customer_id  │◄───┐        ┌───►│ stock_code   │◄───┐
       │ customer_type│    │        │    │ description  │    │
       │ country      │    │        │    │ current_price│    │
       └──────────────┘    │        │    └──────────────┘    │
                           │        │                        │
       ┌──────────────┐    │        │    ┌──────────────┐    │
       │   INVOICE    │    │        │    │  INVENTORY   │    │
       ├──────────────┤    │        │    ├──────────────┤    │
       │ invoice_no   │    │        │    │ stock_code   │────┘
       │ invoice_date │    │        │    │ stock_level  │ (1:1)
       │ customer_id  │────┘        │    │ last_updated │
       │ country      │             │    └──────────────┘
       │ status       │             │
       └──────────────┘             │
              ▲                     │
              │ (1:N)               │ (1:N)
       ┌──────┴─────────────────────┴┐
       │        INVOICE_LINE         │
       ├─────────────────────────────┤
       │ line_id (PK)                │
       │ invoice_no (FK)             │
       │ stock_code (FK)             │
       │ quantity                    │
       │ unit_price_at_sale          │
       └─────────────────────────────┘
```

### Relational Schema Summary:
1. **`customer`** (`customer_id` PK, `customer_type`, `country`):
   * Master directory of unique purchasers.
   * Transitive lifetime metrics (e.g., total spend, first/last purchase dates) are intentionally excluded from the physical base table and calculated on-the-fly via views to prevent 3NF redundancy anomalies.
2. **`product`** (`stock_code` PK, `description`, `current_unit_price`):
   * Official SKU catalog. Isolates live catalog pricing from historical billed transaction amounts.
3. **`inventory`** (`stock_code` PK/FK, `stock_level`, `last_updated`):
   * Real-time warehouse ledger (1:1 with `product`) supporting automated event synchronization.
4. **`invoice`** (`invoice_no` PK, `invoice_date`, `customer_id` FK, `country`, `status`):
   * Transaction header capturing unified invoice timestamp, destination country, and lifecycle status (`Completed`, `Cancelled`, `Loss`).
5. **`invoice_line`** (`line_id` PK, `invoice_no` FK, `stock_code` FK, `quantity`, `unit_price_at_sale`):
   * Atomic purchase details preserving exact billed prices and item quantities.

### Foreign Key Actions & Constraints:
* `ON DELETE RESTRICT` on master tables (`customer`, `product`) preventing accidental orphan generation.
* `ON DELETE CASCADE` from `invoice` to `invoice_line` preserving relational atomicity.
* `ON UPDATE CASCADE` across all relational foreign keys.
* `CHECK` constraints on status domains (`'Completed'`, `'Cancelled'`, `'Loss'`) and customer types (`'Registered'`, `'Guest'`).

---

## 3. Data Cleansing & Alteration Audit Trail

All data transformations are segregated into strict **DELETION** (capped under a strict 10% budget constraint) and **CORRECTION** phases.

### 3.1 Deletion Budget Summary (Budget Limit: 10%)

| Step | Alteration Category | Rows Purged | % of Raw | Remaining Budget | Engineering Rationale |
|:---|:---|:---:|:---:|:---:|:---|
| **1** | Exact Duplicate Rows (Identical across all 8 columns) | 34,150 | 3.26% | 6.74% | Eliminates duplicate recorded line items. |
| **2–4** | Union of Admin SKUs + Blank Descriptions + Non-UK Blank Customers | 12,954 | 1.23% | 5.51% | Purges non-physical charges (`POST`, `DOT`, `M`, etc.) and unrecoverable records without double-counting 90 overlapping rows. |
| **TOTAL** | **Net Rows Purged** | **47,104** | **4.49%** | **5.51%** | **Strictly compliant (far below 10% ceiling).** |

> **Technical Note on Raw Record Counts:**  
> The raw single-sheet spreadsheet (`online_retail_data.xlsx`) contains exactly **1,048,575 records (+ 1 header = 1,048,576 rows)**, representing the physical maximum row ceiling ($2^{20}$) of a Microsoft Excel sheet. All deduplication, union pruning, and status partitions scale consistently with the complete dataset.

### 3.2 Correction & Imputation Pipeline

1. **Single Guest Account Architecture (`customer_id = 0`):**  
   All unauthenticated checkout records originating from the UK are assigned to a synthetic Guest Account (`customer_id = 0`, `customer_type = 'Guest'`, `country = 'United Kingdom'`). This guarantees that `INVOICE.customer_id` remains `NOT NULL` without losing £2.8M+ in authentic transaction volume.
2. **Catalog Price Imputation:**  
   953 lines with `Price = 0` for authentic retail items (`Quantity > 0`) are imputed using the arithmetic mean price of the corresponding `StockCode`.
3. **Multi-Timestamp Normalization:**  
   83 multi-timestamp invoices are resolved to a single authoritative canonical timestamp using $\min(\text{InvoiceDate})$.
4. **Description & Residence Uniformity:**  
   SKU descriptions and customer country assignments are standardized via statistical mode per identifier.
5. **Transaction Status Partitioning & Quantity Normalization:**  
   * `Invoice` with prefix `'C'` $\rightarrow$ Status `'Cancelled'`; quantities converted to absolute value (`Qty -> ABS`).
   * Non-C negative transactions $\rightarrow$ Status `'Loss'` (warehouse damages/write-offs).
   * Positive sales $\rightarrow$ Status `'Completed'`.
   * Assigned via invoice-level majority vote.

---

## 4. Analytical Queries & DML Scenarios (`sql/queries.sql`)

The repository includes standard solutions for 5 production DML and analytical reporting scenarios:

* **Scenario 1: Price Adjustment Campaign (`UPDATE`)**  
  Simulates and executes an 8% inflation price adjustment on catalog items currently priced under \$5.00.
* **Scenario 2: Order Cancellation Processing (`UPDATE`)**  
  Soft-cancels specified orders (`status = 'Cancelled'`) preserving line-item audit trails for accounting and stock reconciliation.
* **Scenario 3: Regional Sales Breakdown (`JOIN & GROUP BY`)**  
  Generates total completed revenue and invoice counts per destination country, strictly isolating `'Completed'` transactions.
* **Scenario 4: VIP High-Spender Identification (`Nested Subquery`)**  
  Identifies high-value registered customers whose lifetime spend strictly exceeds the global average customer spend, explicitly excluding the synthetic guest account from whale analysis.
* **Scenario 5: Cross-Border Product Performance (`Subquery & HAVING`)**  
  Identifies niche products never purchased by German customers, but purchased by customers from $\ge 2$ other countries.

---

## 5. Database Automation & Analytics Views (`sql/advanced.sql`)

### 5.1 Real-Time Inventory Synchronization Trigger
Automatically synchronizes `inventory.stock_level` on every `invoice_line` insert:
$$\text{stock\_level}_{\text{new}} = \text{stock\_level}_{\text{old}} - \text{NEW.quantity}$$
* Updates `last_updated` timestamp to `CURRENT_TIMESTAMP`.
* Native implementations provided for both **PostgreSQL** (`PL/pgSQL`) and **MySQL 8.0+** (`DELIMITER $$`).

### 5.2 Stored Procedure: `GetCustomerInvoiceHistory`
Accepts a `CustomerID` parameter and outputs all associated invoices, transaction dates, and total invoice monetary values.

### 5.3 Customer Analytics View (`view_customer_rfm`)
Computes customer Recency, Frequency, and Monetary (RFM) statistics on-the-fly, eliminating transitive derivation columns in `customer`:
```sql
CREATE OR REPLACE VIEW view_customer_rfm AS
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
    ON c.customer_id = i.customer_id AND i.status = 'Completed'
LEFT JOIN invoice_line l 
    ON i.invoice_no = l.invoice_no
GROUP BY c.customer_id, c.customer_type, c.country;
```

---

## 6. Directory Structure

```text
aol-kodes-retail/
├── data/
│   ├── raw/                      # Raw dataset (online_retail_data.xlsx)
│   ├── processed/                # 3NF normalized production CSVs (1,001,471 active rows)
│   │   ├── customers.csv         # 5,861 records (5,860 registered + 1 guest)
│   │   ├── products.csv          # 4,751 catalog SKUs
│   │   ├── inventory.csv         # 4,751 inventory ledger records
│   │   ├── invoices.csv          # 47,164 invoice headers
│   │   └── invoice_lines.csv     # 1,001,471 transaction line items
│   └── retail.db                 # Portable 3NF SQLite database for instant local inspection
├── docs/
│   ├── DATA_CLEANING_AND_ETL_LOG.md # Complete engineering audit trail & alteration log
│   ├── ERD.md                    # 3NF Crow's Foot ERD & normalization mathematical proof
│   ├── erd.png / erd.svg         # High-resolution architectural ERD diagrams
│   └── PROJECT_PLAN.md           # Implementation specifications & deliverable roadmap
├── scripts/
│   ├── build_retail_db.py        # End-to-end data cleansing, 3NF normalizer & SQLite builder
│   ├── sync_supabase.py          # Bi-directional cloud sync CLI for PostgreSQL (Supabase)
│   ├── query_local.py            # Interactive local SQL terminal console
│   ├── test_queries.py           # Automated analytical query validation suite
│   ├── verify_data.py            # Automated ACID referential integrity & zero-null test suite
│   └── profile_raw.py            # Raw dataset profiling & anomaly diagnosis
├── sql/
│   ├── schema.sql                # Phase 2: DDL statements, PK/FK, constraints & RFM view
│   ├── queries.sql               # Phase 3: 5 production DML scenarios & analytical queries
│   └── advanced.sql              # Phase 4: Inventory trigger & customer history stored procedure
├── imputer.py                    # High-throughput data cleansing CLI engine
├── run.bat / run.ps1             # Native 1-click launchers
└── README.md
```

---

## 7. Replication & Quickstart Guide

### 7.1 Prerequisites
* Python 3.11+
* [uv](https://docs.astral.sh/uv/) (Fast Python package manager)

### 7.2 Run Data Normalization Pipeline
To re-run the complete data cleansing and normalization pipeline from raw spreadsheet to 3NF CSVs and local database:
```powershell
uv run scripts/build_retail_db.py
```

### 7.3 Run Data Integrity Verification Suite
To certify that the dataset contains zero nulls and zero orphan foreign keys:
```powershell
uv run scripts/verify_data.py
```

### 7.4 Query the Local Database Interactively
To launch the interactive local SQL terminal console:
```powershell
uv run scripts/query_local.py
```

### 7.5 Synchronize with Supabase Cloud Database
To push the complete 3NF schema and stream all 1,001,471 records into Supabase PostgreSQL:
```powershell
uv run scripts/sync_supabase.py --push
```
To pull cloud updates back into local CSV files and SQLite:
```powershell
uv run scripts/sync_supabase.py --pull
```

---

## 8. Authors & Academic Integrity

* **Author:** Gerald Martadinata
* **Course:** Database Technology / Systems Architecture
* **Standard:** Relational Database 3NF Normalization
* **License:** MIT License
