# KoDes Retail Data Cleaning and ETL Log

This log describes the pipeline and processed dataset using the ZIP documentation as the data baseline. It also records the lecturer's implementation directions: stock attributes are stored in `product`, and `invoice_line` has no primary key or `line_id` column.

## 1. Source and Retained Data

The complete source export contains 1,067,371 rows from 1 December 2009 through 9 December 2011. An earlier single-sheet Excel export stopped at 1,048,575 rows because of the worksheet limit. The repository input `data/raw/online_retail_data_dedup.csv` contains 1,033,036 rows after exact duplicate removal.

All anonymous customer records are retained, including transactions outside the United Kingdom. Their customer IDs map to Guest ID `0`; each invoice keeps its actual transaction country in `invoice.country`.

## 2. Deletion Budget

| Stage | Rows | Basis |
|:---|---:|:---|
| Complete source | 1,067,371 | ZIP source analysis |
| Exact duplicates removed before current ETL input | 34,335 | 1,067,371 − 1,033,036 |
| Deduplicated ETL input | 1,033,036 | Current raw CSV |
| Admin SKU and blank-description union | 10,061 | Current pipeline output; 37 rows overlap both rules |
| Processed invoice lines | 1,022,975 | 1,033,036 − 10,061 |
| Total removed | 44,396 (4.16%) | Within the 10% ceiling |

The pipeline uses exact administrative-code matching plus the `GIFT_0001_` prefix. `DCGS*` codes are retained as products. The current exclusion union does not remove non-UK anonymous transactions.

## 3. Cleaning and Derived Fields

- Invoice dates use the earliest timestamp for each invoice.
- Product descriptions are trimmed, uppercased, and standardized to the most frequent eligible product description. SKUs without a genuine priced description use `UNLISTED RETAIL ITEM`.
- Of the zero-price lines, 709 eligible product lines receive the mean positive price for the same SKU; 254 unrecoverable staff-note lines remain at zero and are classified as `Loss`.
- C-prefixed lines classify as `Cancelled`; non-C negative-quantity lines and unrecoverable zero-price lines classify as `Loss`; other positive-quantity lines classify as `Completed`. Invoice header status is selected by the modal line status. Quantities are exported as absolute values.
- A single Guest customer ID `0` groups anonymous transactions from 15 countries (4,036 invoices and 228,752 rows per the ZIP reference). The profile country value is a label; transaction country stays in `invoice.country`.
- Customer name, email, phone, address, city, and invoice payment method are generated. They are not source data or verified personal/payment details.
- `product.category` is assigned by description rules. `product.current_unit_price` is the median positive historical price proxy.
- `product.stock_level` starts at an assumed 1,000 per SKU. `reorder_level` is derived from approximately two weeks of observed demand and bounded between 20 and 500. `last_updated` is the processing timestamp. These are not reconstructed historical warehouse balances.

## 4. Current Relational Output

The lecturer-directed model has four tables. The prior standalone `inventory` entity is removed; its attributes are columns in `product`.

| Table | Key design | Processed rows |
|:---|:---|---:|
| `customer` | `customer_id` primary key | 5,877 |
| `product` | `stock_code` primary key; includes stock fields | 4,755 |
| `invoice` | `invoice_no` primary key | 47,915 |
| `invoice_line` | No primary key; two foreign keys | 1,022,975 |

Invoice header statuses in the ZIP reference: 39,544 `Completed`, 7,405 `Cancelled`, 966 `Loss`. Since the associative table has no key, duplicate detail rows may be stored but cannot be uniquely selected by a key.

## 5. Query 2: Cancellation

The order is cancelled by updating the invoice header's `status`. The invoice and its detail rows are retained. The optional cancellation trigger restores stock in `product.stock_level` when a `Completed` invoice changes to `Cancelled`. This preserves transaction rows, but the previous status value is not separately historized.

```sql
UPDATE invoice
SET status = 'Cancelled'
WHERE invoice_no = '536365'
  AND status = 'Completed';
```

## 6. Reproduction

```powershell
python imputer.py --input data/raw/online_retail_data_dedup.csv --output data/processed --clean
```

This writes the four CSVs: `customers.csv`, `products.csv`, `invoices.csv`, and `invoice_lines.csv`. The obsolete `inventory.csv` is not part of the current schema.
