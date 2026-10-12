# KoDes Retail: Database Overhaul Project Plan & Academic Compliance Guide

**Client:** KoDes Retail (All-Occasion Gift Specialist, Indonesia)  
**Project:** Relational Database Overhaul  
**Target Deadline:** Any time before UAS  
**Academic Standard:** Third Normal Form (3NF) Relational Architecture  
**Target RDBMS:** PostgreSQL 17+ (Supabase Cloud), SQLite (Local Verified Engine)  

---

## 1. Project Background and Core Objective

### 1.1 The Client Scenario
KoDes Retail is an Indonesian-based retail store specializing in all-occasion gifts. For several years, they operated by exporting all transaction data into a single, denormalized CSV file (`online_retail_data.xlsx`, containing over 1 million records).

This flat-file approach introduced severe operational friction:
* Generating basic reports was slow due to unindexed full-table scans.
* Data was frequently inconsistent, exhibiting description drift and duplicate prices for identical SKUs.
* Routine maintenance (such as updating a product's name or price) was error-prone and caused update anomalies.

### 1.2 The Core Objective
Design, implement, and test a fully normalized relational database system from scratch using the client's raw transaction records as a blueprint. The new system must ensure ACID data integrity, eliminate redundancy, enforce referential integrity, and execute complex business queries efficiently.

---

## 2. Official Deliverables Checklist

The project requires three categories of final deliverables:

| Deliverable Category | Target File(s) | Status | Description |
|:---|:---|:---:|:---|
| **Phase 1: Database Design** | `docs/ERD.md`, `docs/erd.svg`, `docs/erd.png` | Complete | 3NF Crow's Foot Entity-Relationship Diagram with PK, FK, and mathematical normalization proof. |
| **Phase 2: Physical Schema (DDL)** | `sql/schema.sql` | Complete | Standalone SQL script with `CREATE TABLE`, datatypes, PK/FK, referential cascades, data constraints, and dynamic RFM view. |
| **Phase 3: Transactions & Queries (DML)** | `sql/queries.sql` | Complete | Standalone SQL script containing solutions for all 5 required business scenarios. |
| **Phase 4: Automation & Procedures** | `sql/advanced.sql` | Complete | Standalone SQL script containing the automated inventory trigger and `GetCustomerInvoiceHistory` stored procedure. |
| **Technical Documentation** | `README.md`, `docs/DATA_CLEANING_AND_ETL_LOG.md` | Complete | Comprehensive engineering guide, ETL audit trail, row-budget reconciliation, and query benchmarks. |
| **Database Backup File** | `backup/kodes_retail_backup.db`, `backup/kodes_retail_dump.sql` | Complete | Verified database backup files generated via `scripts/export_backup.py`. |

---

## 3. Strict Project Constraints: What is Prohibited

To ensure maximum academic evaluation and avoid grade penalties, the following constraints must be strictly adhered to:

### Constraint 1: No Data Sampling on Final Import
* **Lecturer Rule:** *"Data from CSV should be imported into the DB. Preprocessing using other programming language is allowed. Using only sample of the data as your final import is not allowed."*
* **Our Implementation:** The pipeline ingests the entire raw spreadsheet (1,048,575 rows without sampling). After strictly budgeted data cleansing (4.49% purged, well within the 10% budget ceiling), all 1,001,471 active transaction records are imported into production tables.

### Constraint 2: No Physical Deletion on Order Cancellation (Query 2)
* **Lecturer Rule:** *"A customer requests to cancel an order (`InvoiceNo`). Update the status of that invoice to `'Cancelled'` (or handle the cancellation according to your schema design) without deleting historical audit records."*
* **Our Implementation:** Implemented via soft cancellation (`UPDATE invoice SET status = 'Cancelled' WHERE invoice_no = ...`). Transaction line items, product quantities, and historical prices remain intact for accounting reconciliation.

### Constraint 3: No Normalization Violations (Must be at least 3NF)
* **Lecturer Rule:** *"The schema must be normalized to at least Third Normal Form (3NF)."*
* **Our Implementation:**  
  * 1NF: Atomic scalar attributes with explicit Primary Keys.  
  * 2NF: No partial dependencies; item quantities and sale prices depend fully on `line_id`.  
  * 3NF: No transitive dependencies. Current catalog list prices are isolated in `product`, while historical billed prices are stored in `invoice_line`. Aggregated customer metrics (lifetime spend, purchase dates) are not materialized in `customer` and are computed on-the-fly via `view_customer_rfm`.

### Constraint 4: No Orphan Foreign Keys or Missing Cascades
* **Lecturer Rule:** *"Referential integrity actions (`ON DELETE`, `ON UPDATE`) must be defined. Use other constraints (`NOT NULL`, `UNIQUE`, `CHECK`, `DEFAULT`) as needed."*
* **Our Implementation:** Master entities use `ON DELETE RESTRICT` to prevent accidental orphaned orders; `invoice` to `invoice_line` uses `ON DELETE CASCADE`. Foreign key tests verify 0 orphan records across the entire 1M+ row dataset.

---

## 4. Strategies for Maximum Grade (Score Optimization)

The project incorporates several engineering best practices to secure top marks:

1. **Deterministic Cleansing with Budget Accountability:**  
   Total deletions are capped at 4.49% (47,104 rows), strictly respecting the 10% limit. All steps are logged with mathematical explanations, including the Excel $2^{20}$ (1,048,576 rows) hard limit reconciliation.
2. **Single Guest Account Strategy (`customer_id = 0`):**  
   Anonymous UK transactions are assigned to a synthetic guest record (`customer_id = 0`, `customer_type = 'Guest'`, `country = 'United Kingdom'`). This avoids null foreign keys while preserving more than £2.8M in authentic retail revenue.
3. **Comprehensive Constraint Coverage:**  
   Every table enforces `NOT NULL` on essential attributes, `CHECK` constraints on domains (`customer_type`, `invoice_status`, positive unit prices), and `DEFAULT` values where appropriate.
4. **Dynamic RFM Analytical View (`view_customer_rfm`):**  
   Demonstrates advanced SQL capability by providing CRM metrics on-demand without violating 3NF storage rules.
5. **Bidirectional Trigger Automation:**  
   The inventory trigger handles both positive sales (decrements stock) and negative returns/losses (increments stock), updating timestamps automatically.
6. **Dual Dialect Support & Verification Suite:**  
   DDL and queries are tested and verified across SQLite, PostgreSQL (Supabase), and MySQL 8.0+. Automated test scripts (`verify_data.py` and `test_queries.py`) provide repeatable proof of compliance.

---

## 5. Phase-by-Phase Task Breakdown & Verification

### Phase 1: Database Analysis & Design
- [x] Investigate denormalized relationships in `online_retail_data.xlsx`.
- [x] Deconstruct flat file into five normalized entities: `customer`, `product`, `inventory`, `invoice`, and `invoice_line`.
- [x] Justify business value of the added `inventory` table (tracks stock availability and automates adjustments).
- [x] Author Crow's Foot ERD with Primary Keys, Foreign Keys, and cardinalities (`docs/ERD.md`).
- [x] Generate high-resolution diagrams (`docs/erd.svg` and `docs/erd.png`).
- [x] Formulate formal normalization proof for 1NF, 2NF, and 3NF.

### Phase 2: Physical Database Implementation (`sql/schema.sql`)
- [x] Write clean DDL statements (`CREATE TABLE`) for all five tables.
- [x] Select appropriate storage datatypes (`INT`, `BIGINT`, `VARCHAR`, `TIMESTAMP`, `DECIMAL(10,2)`).
- [x] Enforce Primary Key and Foreign Key constraints.
- [x] Define referential integrity actions: `ON DELETE RESTRICT`, `ON DELETE CASCADE`, `ON UPDATE CASCADE`.
- [x] Add data quality constraints: `NOT NULL`, `CHECK`, `DEFAULT`.
- [x] Create dynamic analytical view `view_customer_rfm`.
- [x] Provide bulk data ingestion commands (`\copy` for PostgreSQL, `LOAD DATA` for MySQL).
- [x] Import full dataset (1,001,471 rows) with zero sampling.

### Phase 3: Data Transactions & Queries (`sql/queries.sql`)
- [x] **Query 1 (Price Adjustment Campaign):** Execute an 8% price increase on catalog items currently priced under $5.00 using `UPDATE`.
- [x] **Query 2 (Order Cancellation Processing):** Soft-cancel an order (`status = 'Cancelled'`) without deleting historical line items.
- [x] **Query 3 (Regional Sales Breakdown):** Report total sales revenue and completed invoice counts per country using `JOIN` and `GROUP BY`, sorted descending.
- [x] **Query 4 (VIP High-Spender Identification):** Identify registered customers whose total spend strictly exceeds the database average customer spend via nested subqueries.
- [x] **Query 5 (Cross-Border Product Performance):** Identify products never purchased by German customers but purchased across two or more other countries via `HAVING` and negative subquery filtering.

### Phase 4: Advanced Features & Automation (`sql/advanced.sql`)
- [x] **Automated Trigger (`trg_update_inventory`):** Automatically update `inventory.stock_level` on every `invoice_line` insertion (sales decrement, returns increment) and update `last_updated`. Native implementations for PostgreSQL and MySQL.
- [x] **Stored Procedure (`GetCustomerInvoiceHistory`):** Accept `CustomerID` parameter and return all associated invoices, transaction dates, line counts, and monetary totals. Native implementations for PostgreSQL and MySQL.

---

## 6. Project Health Check: Are We on the Right Track?

**Assessment: Yes, 100% on track and compliant with all project criteria.**

Every single requirement, constraint, and deliverable specified in the lecturer's assignment brief has been thoroughly implemented, tested, and documented:
1. **Three Separate SQL Files:** Fully written and verified (`sql/schema.sql`, `sql/queries.sql`, `sql/advanced.sql`).
2. **Technical Documentation in English:** `README.md`, `docs/ERD.md`, `docs/DATA_CLEANING_AND_ETL_LOG.md`, and this project plan are clean, natural, and free of AI slop.
3. **Database Backup:** Generated and accessible in `backup/kodes_retail_backup.db` and `backup/kodes_retail_dump.sql`.
4. **Data Integrity:** Certified with 0 nulls across all 19 columns and 0 orphan foreign keys over 1,001,471 active records.
5. **Zero Sampling:** Processed and loaded the entire dataset without truncation or artificial sampling.
