# AOL KoDes Retail — Relational Database Overhaul (3NF)

Project workspace for the Database Overhaul assignment of **KoDes Retail**.
Author: **Gerald Martadinata**

---

## 📁 Directory Structure

```text
aol-kodes-retail/
├── data/
│   ├── raw/                  # Source file: online_retail_data.xlsx (1,048,575 rows raw)
│   └── processed/            # 3NF normalized production-ready CSVs (1,014,425 active rows)
│       ├── customers.csv     # 5,939 unique customers (5,924 Registered + 15 Regional Guests)
│       ├── products.csv      # 5,130 unique product SKUs with standardized descriptions & catalog prices
│       ├── inventory.csv     # 5,130 stock ledger entries (prepared for Phase 4 trigger)
│       ├── invoices.csv      # 52,961 unified invoices (Completed, Cancelled, Loss)
│       └── invoice_lines.csv # 1,014,425 atomic line-item transaction records
├── docs/
│   ├── ERD.md                # Phase 1: 3NF Crow's Foot Diagram, Data Dictionary & Normalization Proof
│   └── PROJECT_PLAN.md       # Comprehensive Specification & Deliverable Checklist
├── scripts/
│   ├── verify_data.py        # Automated test suite (Zero-null, uniformity & FK checks)
│   └── run_verify.ps1        # 1-click PowerShell runner for automated tests
├── sql/                      # Official assignment deliverables
│   ├── schema.sql            # Phase 2: DDL (CREATE TABLE, PK/FK, ON UPDATE/DELETE, Check, RFM View)
│   ├── queries.sql           # Phase 3: DML (5 required business scenarios & analytics)
│   └── advanced.sql          # Phase 4: Automation (Inventory Trigger & GetCustomerInvoiceHistory SP)
├── imputer.py                # High-throughput data cleansing and 3NF normalizer engine CLI (v1.3.0)
├── run.bat                   # 1-click native launcher for imputer CLI
└── README.md
```

---

## 🧪 How to Verify & Test Data Quality

To execute the automated validation suite and verify that the processed dataset is 100% free of nulls, uniform, and satisfies all relational foreign key constraints:

```powershell
# Option A: Run automated test suite via uv
uv run scripts/verify_data.py

# Option B: Run 1-click PowerShell script
.\scripts\run_verify.ps1

# Option C: Run deep audit inside imputer CLI
uv run imputer.py --verify
```

The validation suite tests:
1. **File Ingestion Check**: Confirms all 5 production CSVs exist and parse cleanly.
2. **Completeness Audit**: Checks every single column for nulls, NaNs, and blank strings (Guaranteed 0 nulls).
3. **Data Uniformity**: Validates strict typing for customer types (`Registered`/`Guest`) and invoice statuses (`Completed`/`Cancelled`/`Loss`).
4. **Referential Integrity (Foreign Keys)**: Proves that zero orphan keys exist across all parent and child table relations.

