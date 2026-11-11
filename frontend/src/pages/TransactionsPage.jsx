import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  Download,
  Pencil,
  Plus,
  Search,
  Trash2,
  Upload,
} from "lucide-react";
import { api } from "../api/client";
import CsvImportModal from "../components/CsvImportModal";
import TransactionModal from "../components/TransactionModal";
import { useGlobalFilter } from "../context/FilterContext";
import { formatCurrency, formatNumber, formatShortDate } from "../utils/formatters";

export default function TransactionsPage() {
  const { filterParams, settings, refreshVersion, triggerRefresh } = useGlobalFilter();
  const [rows, setRows] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, total_pages: 1, total_count: 0 });
  const [totals, setTotals] = useState({ revenue: 0, expenses: 0, net: 0 });
  const [metadata, setMetadata] = useState({ all_categories: [], payment_methods: [] });

  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [txType, setTxType] = useState("all");
  const [category, setCategory] = useState("all");
  const [paymentMethod, setPaymentMethod] = useState("all");
  const [sortBy, setSortBy] = useState("transaction_date");
  const [sortOrder, setSortOrder] = useState("desc");
  const [page, setPage] = useState(1);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [banner, setBanner] = useState("");

  const [txModalOpen, setTxModalOpen] = useState(false);
  const [editingTx, setEditingTx] = useState(null);
  const [csvModalOpen, setCsvModalOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 250);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [filterParams.period, filterParams.start_date, filterParams.end_date, txType, category, paymentMethod]);

  const fetchTransactions = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.getTransactions({
        ...filterParams,
        search: debouncedSearch,
        transaction_type: txType,
        category,
        payment_method: paymentMethod,
        sort_by: sortBy,
        sort_order: sortOrder,
        page,
        per_page: 20,
      });
      setRows(res.transactions || []);
      setPagination(res.pagination || { page: 1, total_pages: 1, total_count: 0 });
      setTotals(res.totals || { revenue: 0, expenses: 0, net: 0 });
      setMetadata(res.metadata || { all_categories: [], payment_methods: [] });
    } catch (err) {
      setError(err.message || "Failed to load transactions.");
    } finally {
      setLoading(false);
    }
  }, [
    filterParams.period,
    filterParams.start_date,
    filterParams.end_date,
    debouncedSearch,
    txType,
    category,
    paymentMethod,
    sortBy,
    sortOrder,
    page,
    refreshVersion,
  ]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  const currency = settings.currency || "INR";

  const handleSaveTx = async (payload) => {
    if (editingTx) {
      const res = await api.updateTransaction(editingTx.id, payload);
      setBanner(res.message);
    } else {
      const res = await api.createTransaction(payload);
      setBanner(res.message);
    }
    setEditingTx(null);
    triggerRefresh();
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      const res = await api.deleteTransaction(deleteTarget.id);
      setBanner(res.message);
      setDeleteTarget(null);
      triggerRefresh();
    } catch (err) {
      setError(err.message || "Failed to delete transaction.");
    }
  };

  const handleSort = (col) => {
    if (sortBy === col) {
      setSortOrder((prev) => (prev === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(col);
      setSortOrder("desc");
    }
  };

  const exportUrl = api.getCsvExportUrl({
    ...filterParams,
    search: debouncedSearch,
    transaction_type: txType,
    category,
  });

  return (
    <div className="space-y-5">
      {banner && (
        <div className="flex items-center justify-between rounded-md border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-xs font-medium text-emerald-800">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{banner}</span>
          </div>
          <button
            type="button"
            onClick={() => setBanner("")}
            className="text-emerald-700 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Action & Filter Toolbar */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="relative min-w-[240px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search description, category, notes, payment method, or ID..."
              className="w-full rounded-md border border-slate-300 py-2 pl-9 pr-3 text-xs text-slate-900 focus:border-blue-800 focus:outline-none"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setEditingTx(null);
                setTxModalOpen(true);
              }}
              className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Transaction
            </button>
            <button
              type="button"
              onClick={() => setCsvModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-md border border-blue-900 bg-blue-50 px-3.5 py-2 text-xs font-semibold text-blue-900 hover:bg-blue-100"
            >
              <Upload className="h-3.5 w-3.5" />
              Import CSV
            </button>
            <a
              href={exportUrl}
              download="fintrack_transactions_export.csv"
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              <Download className="h-3.5 w-3.5" />
              Export CSV
            </a>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label className="mb-1 block text-[11px] font-semibold uppercase text-slate-500">
              Transaction Type
            </label>
            <select
              value={txType}
              onChange={(e) => setTxType(e.target.value)}
              className="w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-800"
            >
              <option value="all">All Types</option>
              <option value="Revenue">Revenue Only</option>
              <option value="Expense">Expense Only</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-semibold uppercase text-slate-500">
              Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-800"
            >
              <option value="all">All Categories</option>
              {metadata.all_categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-semibold uppercase text-slate-500">
              Payment Method
            </label>
            <select
              value={paymentMethod}
              onChange={(e) => setPaymentMethod(e.target.value)}
              className="w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-800"
            >
              <option value="all">All Methods</option>
              {metadata.payment_methods.map((pm) => (
                <option key={pm} value={pm}>
                  {pm}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Filtered Summary Bar */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-[11px] font-medium text-slate-500">Matching Entries</div>
          <div className="mt-0.5 text-lg font-bold text-slate-900 tabular-nums">
            {formatNumber(pagination.total_count)}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-[11px] font-medium text-slate-500">Filtered Revenue</div>
          <div className="mt-0.5 text-lg font-bold text-emerald-700 tabular-nums">
            {formatCurrency(totals.revenue, currency)}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-[11px] font-medium text-slate-500">Filtered Expenses</div>
          <div className="mt-0.5 text-lg font-bold text-amber-700 tabular-nums">
            {formatCurrency(totals.expenses, currency)}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <div className="text-[11px] font-medium text-slate-500">Net Balance</div>
          <div
            className={`mt-0.5 text-lg font-bold tabular-nums ${
              totals.net >= 0 ? "text-slate-900" : "text-red-700"
            }`}
          >
            {formatCurrency(totals.net, currency)}
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Transactions Table */}
      <div className="rounded-lg border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-200 bg-slate-50 text-[11px] uppercase text-slate-500">
              <tr>
                <th className="cursor-pointer px-4 py-3" onClick={() => handleSort("id")}>
                  ID {sortBy === "id" ? (sortOrder === "asc" ? "↑" : "↓") : ""}
                </th>
                <th
                  className="cursor-pointer px-4 py-3"
                  onClick={() => handleSort("transaction_date")}
                >
                  Date {sortBy === "transaction_date" ? (sortOrder === "asc" ? "↑" : "↓") : ""}
                </th>
                <th className="px-4 py-3">Description & Notes</th>
                <th
                  className="cursor-pointer px-4 py-3"
                  onClick={() => handleSort("transaction_type")}
                >
                  Type {sortBy === "transaction_type" ? (sortOrder === "asc" ? "↑" : "↓") : ""}
                </th>
                <th className="cursor-pointer px-4 py-3" onClick={() => handleSort("category")}>
                  Category {sortBy === "category" ? (sortOrder === "asc" ? "↑" : "↓") : ""}
                </th>
                <th className="px-4 py-3">Payment Method</th>
                <th
                  className="cursor-pointer px-4 py-3 text-right"
                  onClick={() => handleSort("amount")}
                >
                  Amount {sortBy === "amount" ? (sortOrder === "asc" ? "↑" : "↓") : ""}
                </th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                    Loading transactions...
                  </td>
                </tr>
              ) : rows.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-slate-500">
                    No matching transactions found. Try clearing filters or adding a new entry.
                  </td>
                </tr>
              ) : (
                rows.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-2.5 font-mono text-[11px] text-slate-500">#{tx.id}</td>
                    <td className="px-4 py-2.5 text-slate-700 tabular-nums whitespace-nowrap">
                      {formatShortDate(tx.transaction_date)}
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="font-medium text-slate-900">{tx.description}</div>
                      {tx.notes && <div className="text-[11px] text-slate-500">{tx.notes}</div>}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-flex rounded px-2 py-0.5 text-[11px] font-semibold ${
                          tx.transaction_type === "Revenue"
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-amber-50 text-amber-800"
                        }`}
                      >
                        {tx.transaction_type}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-slate-700">{tx.category}</td>
                    <td className="px-4 py-2.5 text-slate-600">
                      <span>{tx.payment_method}</span>
                      {tx.payment_method.toLowerCase().includes("credit") && (
                        <span className="ml-1.5 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
                          Accrual
                        </span>
                      )}
                    </td>
                    <td
                      className={`px-4 py-2.5 text-right font-semibold tabular-nums whitespace-nowrap ${
                        tx.transaction_type === "Revenue" ? "text-emerald-700" : "text-slate-900"
                      }`}
                    >
                      {tx.transaction_type === "Revenue" ? "+" : "-"}
                      {formatCurrency(tx.amount, currency)}
                    </td>
                    <td className="px-4 py-2.5 text-right whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => {
                          setEditingTx(tx);
                          setTxModalOpen(true);
                        }}
                        className="mr-1.5 rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-blue-800"
                        title="Edit transaction"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleteTarget(tx)}
                        className="rounded p-1 text-slate-500 hover:bg-red-50 hover:text-red-700"
                        title="Delete transaction"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-xs text-slate-600">
          <span>
            Page {pagination.page} of {pagination.total_pages} ({pagination.total_count} records)
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="rounded border border-slate-200 px-3 py-1 font-medium hover:bg-slate-50 disabled:opacity-40"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={page >= pagination.total_pages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded border border-slate-200 px-3 py-1 font-medium hover:bg-slate-50 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Modals */}
      <TransactionModal
        isOpen={txModalOpen}
        onClose={() => {
          setTxModalOpen(false);
          setEditingTx(null);
        }}
        onSave={handleSaveTx}
        initialData={editingTx}
      />

      <CsvImportModal
        isOpen={csvModalOpen}
        onClose={() => setCsvModalOpen(false)}
        onImported={(res) => {
          setBanner(res.message);
          triggerRefresh();
        }}
        currency={currency}
      />

      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-5 shadow-lg">
            <h3 className="text-sm font-semibold text-slate-900">Confirm Deletion</h3>
            <p className="mt-2 text-xs text-slate-600">
              Delete transaction <span className="font-semibold">#{deleteTarget.id}</span> (
              {deleteTarget.description} — {formatCurrency(deleteTarget.amount, currency)})? This
              action cannot be undone.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                className="rounded-md border border-slate-200 px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                className="rounded-md bg-red-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
