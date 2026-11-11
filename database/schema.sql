-- FINTRACK – Small Business Financial Intelligence
-- SQLite Database Schema

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date TEXT NOT NULL,
    description TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('Revenue', 'Expense')),
    category TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount > 0),
    payment_method TEXT NOT NULL,
    notes TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);

CREATE TABLE IF NOT EXISTS business_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_name TEXT NOT NULL DEFAULT 'SMART MART RETAIL STORE',
    currency TEXT NOT NULL DEFAULT 'INR',
    is_demo_data INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
