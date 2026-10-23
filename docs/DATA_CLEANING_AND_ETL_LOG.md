# KoDes Retail Data Cleansing and ETL Pipeline Documentation

This log describes the current `imputer.py` pipeline and the CSV files in `data/processed`. Counts below are measured from those files as of the current workspace snapshot. They replace older figures that described an earlier pipeline run.

## 1. Source and Processing Scope

The Phase 1 source analysis records 1,067,371 rows in the complete retail export. The old single-sheet Excel export contained 1,048,575 data rows because it hit Excel's worksheet limit. The current repository contains `data/raw/online_retail_data_dedup.csv`, with 1,033,036 rows: the exact duplicates have already been removed before this file is passed to `imputer.py`.

The ETL pipeline then removes non-merchandise/admin records, rows with blank descriptions, and non-UK records with missing customer IDs. It does not sample the remaining transactions. Because the supplied input is already deduplicated, the pipeline's duplicate-removal step finds no additional duplicates when run on this file.

## 2. Deletion Budget

The complete-source figures below reconcile the pre-deduplicated source with the current processed output. Percentages use the 1,067,371-row complete source as the denominator.

| Stage | Rows | Notes |
|:---|---:|:---|
| Complete source export | 1,067,371 | Count recorded in the Phase 1 source analysis |
| Exact duplicates removed before the current input file | 34,335 | Current input is already deduplicated |
| Current deduplicated input | 1,033,036 | Verified row count in `data/raw/online_retail_data_dedup.csv` |
| Union of current ETL exclusion rules | 12,953 | Admin SKU, blank description, or non-UK blank customer ID |
| Current processed invoice lines | 1,020,083 | No sampling |
| Total removed from complete source | 47,288 (4.43%) | Within the 10% ceiling |

The current code's admin filter uses exact stock-code matches plus the `GIFT_0001_` prefix. `DCGS*` merchandise is retained as genuine product stock. The three exclusion conditions are combined into one union mask, so overlapping rows are only removed once.

## 3. Corrections and Derived Values

1. **Invoice dates:** every invoice receives its earliest observed timestamp (`MIN(InvoiceDate)`).
2. **Product descriptions:** descriptions are uppercased and standardized to the most frequent description among eligible priced product rows. SKUs without such a description receive `UNLISTED RETAIL ITEM`.
3. **Prices:** zero-priced positive-quantity lines are imputed from the mean positive price for the same SKU only when the line description matches the catalog description. Other such lines remain at zero and are marked as loss notes. `product.current_unit_price` is the median positive transaction price per SKU; it is a derived proxy, not a source catalog price.
4. **Customer country:** registered customers are assigned their most frequent transaction country. Anonymous UK rows use customer ID `0` and country `United Kingdom`; missing non-UK customer rows are excluded.
5. **Synthetic customer fields:** customer name, email, phone, street address, and city are generated deterministically by the script. They are placeholders, not source data or verified contact details.
6. **Payment method:** generated deterministically from the invoice number; `Loss` invoices receive `N/A`. The source has no payment-method field, so these values must not be used for financial reconciliation.
7. **Inventory:** every SKU starts with an assumed stock level of 1,000. The reorder level is derived from approximately two weeks of observed positive demand, rounded to tens and bounded from 20 to 500. `last_updated` is the processing timestamp. These fields do not reconstruct historical warehouse balances.
8. **Quantities and statuses:** quantities are written as positive absolute values. C-prefixed invoices classify their lines as `Cancelled`; non-C negative-quantity lines and unrecoverable zero-price positive-quantity lines classify as `Loss`; other positive lines classify as `Completed`. The schema stores one status per invoice, selected by the modal line status. Therefore minority `Loss` lines can be included in a `Completed` invoice header.

## 4. Current Processed Table Counts

| Table | Primary key | Rows | Audit result |
|:---|:---|---:|:---|
| `customer` | `customer_id` | 5,877 | 5,876 Registered and 1 Guest |
| `product` | `stock_code` | 4,755 | One row per SKU |
| `inventory` | `stock_code` | 4,755 | One row per product |
| `invoice` | `invoice_no` | 47,796 | Unique invoice headers |
| `invoice_line` | `line_id` | 1,020,083 | Atomic transaction lines |

Invoice header statuses are 39,445 `Completed`, 7,385 `Cancelled`, and 966 `Loss`. The processed line file contains 1,014 zero-price rows: 974 belong to `Loss` invoices and 40 to `Completed` invoices, reflecting the invoice-level modal status rule.

A structural audit of the current CSVs found no duplicate primary keys, blank fields, or broken customer, product, or invoice references. All 4,755 processed inventory rows have `stock_level = 1,000`.

## 5. Recomputed Query Benchmarks

These figures were recomputed from the current processed CSV files using the analytical filters in `sql/queries.sql`; they are not a claim that a live Supabase instance was queried.

- **Query 3, regional completed sales:** United Kingdom — 36,211 completed invoices and £17,716,743.43; EIRE — 528 and £587,332.78; Netherlands — 217 and £550,803.81.
- **Query 4, registered VIP customers:** 1,163 customers exceed the mean spend among registered customers with completed purchases. Highest spenders include customer `18102` (£580,987.04) and `14646` (£527,781.92).
- **Query 5, cross-market products:** 1,487 products meet the Germany exclusion and two-country minimum. `21888` (BINGO SET) appears in 18 other countries; `21912` (VINTAGE SNAKES & LADDERS) appears in 17.

## 6. Reproduction

Run the pipeline against the same deduplicated input to recreate the processed tables:

```powershell
python imputer.py --input data/raw/online_retail_data_dedup.csv --output data/processed --all
```

The script's `--guest-id` option currently does not change the guest key: missing customer IDs are hard-coded to `0` in the cleaning function. Use `0` when describing the current output unless that implementation is changed.
