# KoDes Retail — Data Cleansing, 3NF Normalization & Database Documentation

**Dokumen Acuan:** *Data Alteration Log (Revisi Final)*  
**Workspace:** `aol-kodes-retail`  
**Target RDBMS:** PostgreSQL / MySQL 8.0+ / SQLite (`data/retail.db`)  
**Status Pipeline:** ✅ 100% Selesai & Terverifikasi (Zero-Null & ACID Referential Integrity Valid)

---

## 1. Ringkasan Eksekutif & Arsitektur Data

Berdasarkan revisi final, perancangan skema data menerapkan pemisahan ketat antara **DELETION** (penghapusan baris dengan batas toleransi/budget maksimal 10%) dan **CORRECTION** (resolusi, pemulihan harga, standarisasi, dan labeling transaksi).

### 1.1 Entitas Relasional 3NF (Third Normal Form)

```text
[CUSTOMER] (1) <────── (N) [INVOICE] (1) <────── (N) [INVOICE_LINE]
customer_id (PK)          invoice_no (PK)          line_id (PK)
customer_type             invoice_date             invoice_no (FK)
country                   customer_id (FK)         stock_code (FK)
                          country                  quantity
                          status                   unit_price_at_sale
                                                           │
[INVENTORY] (1) <────── (1) [PRODUCT] (1) <────────────────┘
stock_code (PK/FK)        stock_code (PK)
stock_level               description
last_updated              current_unit_price
```

---

## 2. Catatan Khusus: Rekonsiliasi Jumlah Baris Mentah (Excel Ceiling vs CSV)

> [!IMPORTANT]
> **Temuan Teknis untuk Konsultasi Kelas DB:**
> * Dokumen teman mencatat data awal sebanyak **1.067.371 baris** (berasal dari dataset komplit Online Retail II yang biasanya terdiri dari 2 sheet: 2009–2010 dan 2010–2011).
> * File spreadsheet tunggal `data/raw/online_retail_data.xlsx` memiliki tepat **1.048.575 baris data (+ 1 baris header = 1.048.576 baris)**.
> * Angka **1.048.576** adalah batas maksimal fisik (*hard row limit*) satu lembar kerja Microsoft Excel ($2^{20}$). Baris selisih (~18.796 baris) terpotong saat dataset digabung/diekspor ke satu sheet Excel `.xlsx`.
> * Seluruh rasio persentase penghapusan (4,49% vs 4,44%), jumlah unik admin StockCode, dan distribusi status terbukti konsisten dan proporsional.

---

## 3. Log Alterasi Data (Deletion & Correction Audit)

### 3.1 Ringkasan Deletion Budget (Maksimal 10%)

| Tahap | Kategori Penghapusan | Baris Dihapus | % Terhadap Raw | Sisa Budget | Justifikasi |
|:---|:---|:---:|:---:|:---:|:---|
| **Step 1** | Exact Duplicate Rows (8 kolom identik) | 34.150 | 3,26% | 6,74% | Redundansi murni / tidak ada informasi baru |
| **Step 2–4** | Union Non-Produk + Deskripsi Kosong + Customer Non-UK Kosong | 12.954 | 1,23% | 5,51% | Bukan transaksi retail fisik atau data tidak dapat diselamatkan |
| **TOTAL** | **Akumulasi Terhapus (Union tanpa double-count)** | **47.104** | **4,49%** | **5,51%** | **Budget aman (jauh di bawah batas 10%)** |

*Rincian Gross Step 2–4 sebelum reduksi overlap (90 baris irisan):*
* *StockCode Admin (`POST`, `DOT`, `M`, `C2`, `D`, `BANK CHARGES`, dll.):* 5.834 baris.
* *Description Kosong Total:* 4.265 baris.
* *Customer ID Kosong Non-UK:* 2.945 baris.

---

### 3.2 Langkah Pemulihan & Koreksi Data (Correction Steps)

1. **Resolusi Multi-Timestamp:**  
   83 invoice yang memiliki lebih dari satu timestamp diseragamkan dengan mengambil nilai `MIN(InvoiceDate)` per invoice.
2. **Standarisasi Deskripsi Produk:**  
   Deskripsi resmi tiap `StockCode` diseragamkan menggunakan nilai modus (nama yang paling sering muncul).
3. **Pemulihan Harga `Price = 0`:**  
   Pada transaksi barang asli (`Quantity > 0`) dengan `Price = 0` (953 baris), nilai harga dipulihkan menggunakan rata-rata harga `StockCode` terkait.
4. **Single Guest Account Strategy:**  
   Seluruh transaksi anonim UK dipertahankan dan ditugaskan ke satu akun sintetis:  
   * `customer_id = 0`, `customer_type = 'Guest'`, `country = 'United Kingdom'`.  
   * Integritas referensial terjaga sehingga kolom `INVOICE.customer_id` berstatus `NOT NULL`.
5. **Klasifikasi Status Transaksi & Penyesuaian Kuantitas:**  
   * Invoice berawalan huruf `'C'` $\rightarrow$ `status = 'Cancelled'`, kuantitas diubah menjadi absolut positif (`Qty -> ABS`).  
   * Transaksi kuantitas negatif non-C $\rightarrow$ `status = 'Loss'` (write-off inventaris/kerusakan gudang).  
   * Transaksi normal $\rightarrow$ `status = 'Completed'`.  
   * Status per invoice ditetapkan menggunakan aturan mayoritas (*majority mode*).

---

## 4. Statistik Akhir Tabel Produksi

| Tabel | Primary Key | Jumlah Baris (Record) | Keterangan |
|:---|:---|:---:|:---|
| `customer` | `customer_id` | **5.861** | 5.860 Registered + 1 Guest (`id=0`) |
| `product` | `stock_code` | **4.751** | Master katalog produk terdaftar |
| `inventory` | `stock_code` | **4.751** | Ledger pelacak stok fisik |
| `invoice` | `invoice_no` | **47.164** | Header transaksi resmi |
| `invoice_line` | `line_id` | **1.001.471** | Baris detail transaksi aktif |

### Distribusi Status Invoice:
* **Completed:** 39.117 invoice (82,9%)
* **Cancelled:** 7.308 invoice (15,5%)
* **Loss:** 739 invoice (1,6%)

---

## 5. Cuplikan Kode Penting (Python ETL Pipeline)

### 5.1 Logika Deletion Budget & Union (Vectorized Pandas)

```python
# 1. Exact duplicates
df = df_raw.drop_duplicates().copy()

# 2. Identifikasi baris admin, blank deskripsi, dan non-UK blank customer
admin_stockcodes = {'POST', 'DOT', 'M', 'C2', 'D', 'S', 'BANK CHARGES', 'ADJUST', 'AMAZONFEE', ...}
is_admin = df['StockCode'].isin(admin_stockcodes) | df['StockCode'].str.startswith('GIFT_0001_')
is_missing_desc = df['Description'].isna() | (df['Description'].astype(str).str.strip() == '')
is_non_uk_missing_cust = df['Customer ID'].isna() & (df['Country'] != 'United Kingdom')

# Union tanpa double count
union_delete_mask = is_admin | is_missing_desc | is_non_uk_missing_cust
df_clean = df[~union_delete_mask].copy()
```

### 5.2 Single Guest Account & Imputasi Harga

```python
# Single Guest Account (customer_id = 0)
df_clean['Customer_ID_Clean'] = df_clean['Customer ID'].fillna(0).astype(int)

# Imputasi Price=0 untuk barang asli (Quantity > 0)
valid_prices = df_clean[df_clean['Price'] > 0]
stock_avg_price = valid_prices.groupby('StockCode')['Price'].mean().to_dict()
price_zero_mask = (df_clean['Price'] == 0) & (df_clean['Quantity'] > 0)
df_clean.loc[price_zero_mask, 'Price'] = df_clean.loc[price_zero_mask, 'StockCode'].map(stock_avg_price).fillna(0.00).round(2)
```

---

## 6. Cuplikan Query SQL & Skema Database

### 6.1 DDL Skema 3NF (`sql/schema.sql`)

```sql
CREATE TABLE customer (
    customer_id     INT             NOT NULL,
    customer_type   VARCHAR(20)     NOT NULL,
    country         VARCHAR(60)     NOT NULL,
    CONSTRAINT pk_customer PRIMARY KEY (customer_id),
    CONSTRAINT chk_customer_type CHECK (customer_type IN ('Registered', 'Guest'))
);

CREATE TABLE product (
    stock_code          VARCHAR(30)     NOT NULL,
    description         VARCHAR(255)    NOT NULL,
    current_unit_price  DECIMAL(10, 2)  NOT NULL DEFAULT 0.00,
    CONSTRAINT pk_product PRIMARY KEY (stock_code),
    CONSTRAINT chk_product_price CHECK (current_unit_price >= 0.00)
);

CREATE TABLE invoice (
    invoice_no      VARCHAR(20)     NOT NULL,
    invoice_date    TIMESTAMP       NOT NULL,
    customer_id     INT             NOT NULL,
    country         VARCHAR(60)     NOT NULL,
    status          VARCHAR(20)     NOT NULL,
    CONSTRAINT pk_invoice PRIMARY KEY (invoice_no),
    CONSTRAINT fk_invoice_customer FOREIGN KEY (customer_id)
        REFERENCES customer (customer_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_invoice_status CHECK (status IN ('Completed', 'Cancelled', 'Loss'))
);

CREATE TABLE invoice_line (
    line_id             BIGINT          NOT NULL,
    invoice_no          VARCHAR(20)     NOT NULL,
    stock_code          VARCHAR(30)     NOT NULL,
    quantity            INT             NOT NULL,
    unit_price_at_sale  DECIMAL(10, 2)  NOT NULL DEFAULT 0.00,
    CONSTRAINT pk_invoice_line PRIMARY KEY (line_id),
    CONSTRAINT fk_line_invoice FOREIGN KEY (invoice_no)
        REFERENCES invoice (invoice_no) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_line_product FOREIGN KEY (stock_code)
        REFERENCES product (stock_code) ON UPDATE CASCADE ON DELETE RESTRICT
);
```

### 6.2 View Analitik RFM Dinamis (`view_customer_rfm`)

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
    ON c.customer_id = i.customer_id 
   AND i.status = 'Completed'
LEFT JOIN invoice_line l 
    ON i.invoice_no = l.invoice_no
GROUP BY 
    c.customer_id, 
    c.customer_type, 
    c.country;
```

---

## 7. Hasil Uji Coba Query Analitis pada Database Aktif (`data/retail.db`)

Database SQLite aktif di `data/retail.db` (68,14 MB) telah diuji dan menghasilkan metrik:

### Query 3: Top 5 Regional Sales Breakdown (Completed Only)
| Negara | Completed Invoices | Total Revenue | Avg Line Value |
|:---|---:|---:|---:|
| **United Kingdom** | 35.938 | **$17.352.685,15** | $19,12 |
| **EIRE** | 521 | **$581.078,21** | $38,57 |
| **Netherlands** | 214 | **$539.077,55** | $110,02 |
| **Germany** | 739 | **$377.027,70** | $24,28 |
| **France** | 578 | **$305.158,88** | $23,81 |

### Query 4: Top 5 VIP High-Spenders (Registered Only)
| Customer ID | Tipe | Negara | Total Spend |
|:---|:---|:---|---:|
| **18102** | Registered | United Kingdom | **$569.501,50** |
| **14646** | Registered | Netherlands | **$516.055,66** |
| **14156** | Registered | EIRE | **$303.069,88** |
| **14911** | Registered | EIRE | **$266.704,92** |
| **17450** | Registered | United Kingdom | **$245.788,65** |

---

## 8. Panduan Akses Database Langsung

1. **Akses SQLite Instan:**  
   Buka file `data/retail.db` langsung di DBeaver, DataGrip, DB Browser for SQLite, atau VSCode SQLite Viewer.
2. **Ingesti ke PostgreSQL Lokal/Server Kampus:**  
   Gunakan perintah `\copy` dari `sql/schema.sql` untuk mengimpor file CSV di folder `data/processed/` ke PostgreSQL.
