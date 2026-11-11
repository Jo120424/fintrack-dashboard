# FINTRACK – Small Business Financial Intelligence

A full-stack financial performance dashboard and business analytics web application built for small businesses (demonstrated with **SMART MART RETAIL STORE**).

---

## 1. Project Overview

**FINTRACK – Small Business Financial Intelligence** is an end-to-end Business Analytics web platform demonstrating how operational transaction logs are collected, validated, stored in a relational database, analyzed with statistical libraries, visualized interactively, and transformed into actionable financial intelligence and formal reports.

---

## 2. Problem Statement

Small retail and service businesses frequently track sales, supplier purchases, rent, payroll, and cash disbursements in disconnected spreadsheets or manual notebooks. Without consolidated analytics:
- Owners cannot track real-time profitability or profit margin erosion across months.
- Accrual net profit is often confused with actual cash flow liquidity when credit sales or bulk upfront inventory purchases occur.
- Recurring expense drivers (e.g., inventory overstocking or marketing spend spikes) go unnoticed until cash reserves run low.
- Forecasting upcoming revenue relies on guesswork instead of historical trend analysis.

---

## 3. Objectives

1. Centralize revenue and expense transactions inside a structured **SQLite** database with full CRUD and validated **CSV** batch import.
2. Compute dynamic financial KPIs (Total Revenue, Total Expenses, Net Profit, Profit Margin %, Sales Volume, Cash Flow) with current-month vs. previous-month comparisons.
3. Demonstrate five core Business Analytics dimensions:
   - **Descriptive Analytics** (historical revenue, expenses, category distributions)
   - **Diagnostic Analytics** (loss-making period drivers, expense shares, profit-vs-cash-flow variance)
   - **Trend Analysis** (multi-month profitability, cash liquidity, daily/weekly/monthly sales velocity)
   - **Comparative Analysis** (period-over-period growth rates & MoM comparisons)
   - **Predictive Analytics** (deterministic OLS linear regression + moving-average smoothing 3-month revenue forecast)
4. Automatically generate dynamic, data-backed **Business Insights** strictly from database calculations.
5. Export executive-ready **Monthly, Quarterly, and Annual** reports in **CSV** and **PDF** (with embedded charts).

---

## 4. Technologies Used

| Layer | Technologies |
| --- | --- |
| **Frontend** | React 18, Vite, JavaScript, Tailwind CSS, Recharts, Lucide React, React Router |
| **Backend** | Python 3.12, Flask REST API, Flask-CORS, ReportLab (PDF generation) |
| **Data Processing** | Pandas (aggregations, filtering, time-series), NumPy (descriptive statistics, OLS linear trend forecasting) |
| **Database** | SQLite 3 (`database/fintrack.db`) |
| **Testing** | Pytest (API, analytics, CSV validation, reports, edge-case testing) |

---

## 5. System Architecture

```text
+---------------------------+        REST / JSON / Binary        +-------------------------------+
|   React + Vite Frontend   |  <==============================>  |     Flask REST API Backend    |
|  - Tailwind CSS SaaS UI   |      Vite Proxy (/api -> :5000)    |  - Pandas & NumPy Engine      |
|  - Recharts Visuals       |                                    |  - Dynamic Insights Generator |
|  - Global Date Filters    |                                    |  - CSV Validator & Deduper    |
+---------------------------+                                    |  - ReportLab PDF Builder      |
                                                                 +---------------+---------------+
                                                                                 |
                                                                                 v
                                                                 +-------------------------------+
                                                                 |       SQLite Database         |
                                                                 |  - transactions               |
                                                                 |  - business_settings          |
                                                                 +-------------------------------+
```

### Project Directory Structure

```text
fintrack-dashboard/
├── frontend/               # React + Vite + Tailwind + Recharts client
├── backend/                # Flask REST API, Pandas/NumPy services, Pytest suite
├── database/               # SQLite schema, initialization script, deterministic demo seeder
├── sample_data/            # 12-month SMART MART CSV dataset & CSV import template
├── reports/                # Generated PDF summary reports
└── README.md
```

---

## 6. Features

- **Executive Dashboard**: 6 dynamic KPI cards with period-over-period and current-vs-previous month deltas, Indian Rupee (`₹`) numbering (`en-IN`), and 6 interactive Recharts visualizations (`Revenue vs Expenses`, `Profit Trend`, `Revenue Distribution`, `Expense Breakdown`, `Cash Flow Analysis`, `Sales Performance` across Daily/Weekly/Monthly views).
- **Global Date Filtering**: `Today`, `This Week`, `This Month`, `Last Month`, `Last 3 Months`, `Last 6 Months`, `This Year`, `All 12M+`, and `Custom Date Range` updating KPIs, charts, tables, and insights synchronously.
- **Transactions Management**: Full Create, Read, Update, Delete (CRUD), search, multi-filter (date, type, category, payment method), column sorting, pagination, and CSV export.
- **Validated CSV Import**: Column header verification, date & positive-number checks, missing-value detection, row-by-row error preview, duplicate prevention (in-file and against SQLite), and downloadable CSV template.
- **Business Performance & Predictive Analytics**: 10 core financial ratios/metrics, cash-settled vs. accrual profit reconciliation, and a deterministic 3-month revenue forecasting chart with confidence bounds and statistical disclaimer.
- **Dynamic Business Insights**: Automated positive signals, warning flags, optimization opportunities, and margin recommendations generated strictly from database figures.
- **Reports & Exports**: Monthly, Quarterly, and Annual report generator with CSV export and downloadable ReportLab PDF summaries containing embedded Revenue vs. Expense charts.
- **Settings & Demonstration Mode**: Editable business name, currency switcher (`INR ₹`, `USD $`, `EUR €`, `GBP £`), dataset stats, and one-click `Reset Demonstration Data`.

---

## 7. Database Structure

Defined in `database/schema.sql`:

1. **`transactions`**:
   - `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
   - `transaction_date` (TEXT NOT NULL, `YYYY-MM-DD`)
   - `description` (TEXT NOT NULL)
   - `transaction_type` (TEXT NOT NULL: `'Revenue'` or `'Expense'`)
   - `category` (TEXT NOT NULL)
   - `amount` (REAL NOT NULL > 0)
   - `payment_method` (TEXT NOT NULL)
   - `notes` (TEXT)
2. **`business_settings`**:
   - `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
   - `business_name` (TEXT NOT NULL, default `'SMART MART RETAIL STORE'`)
   - `currency` (TEXT NOT NULL, default `'INR'`)
   - `is_demo_data` (INTEGER NOT NULL, default `1`)
   - `created_at` (TEXT NOT NULL)

---

## 8. How to Install Dependencies

### Backend (Python)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Initialize / Reset SQLite Database & Sample CSVs

```powershell
cd ..
.\backend\.venv\Scripts\python.exe -m database.init_db
```

### Frontend (Node.js)

```powershell
cd frontend
npm.cmd install
```

*(Note: On Windows PowerShell where script execution policy restricts `npm.ps1`, use `npm.cmd`.)*

---

## 9. How to Start Frontend and Backend

**Option A — Single Launcher Script (PowerShell):**

```powershell
powershell -ExecutionPolicy Bypass -File .\start_fintrack.ps1
```

**Option B — Manual Terminals:**

Start the **Flask Backend** (Terminal 1, from project root):

```powershell
.\backend\.venv\Scripts\python.exe backend\app.py
```
Backend runs at `http://127.0.0.1:5000`.

Start the **React + Vite Frontend** (Terminal 2, from `frontend/`):

```powershell
cd frontend
npm.cmd run dev
```
Open **`http://localhost:5173`** in your browser. Vite automatically proxies `/api/*` requests to `http://127.0.0.1:5000`.

### Running Automated Tests

```powershell
.\backend\.venv\Scripts\pytest.exe backend\tests\test_api.py -v
```

---

## 10. Expected Outputs

- **Dashboard**: Displays **SMART MART RETAIL STORE** (`DEMONSTRATION DATA` badge), 6 Indian Rupee formatted KPIs, seasonal peaks (e.g., Diwali October peak, Year-End peak), two loss-making months (off-season/monsoon repairs), negative cash-flow periods, and daily/weekly/monthly sales trends.
- **Analytics**: Shows all 10 calculated financial ratios, cash-flow vs. accrual net-profit variance, and a 3-month OLS regression revenue forecast chart with lower/upper confidence range.
- **Reports**: Produces live Monthly/Quarterly/Annual summaries and downloads formatted `.csv` transaction ledgers and multi-section `.pdf` executive reports saved in `reports/`.
