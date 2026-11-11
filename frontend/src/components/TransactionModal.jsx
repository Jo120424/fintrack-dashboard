import { useEffect, useState } from "react";
import { X } from "lucide-react";

const REVENUE_CATEGORIES = [
  "Groceries & Staples",
  "Beverages & Snacks",
  "Personal Care & Home",
  "Electronics & Accessories",
  "Bulk & Wholesale Orders",
  "Home Delivery & Services",
];

const EXPENSE_CATEGORIES = [
  "Rent",
  "Salaries",
  "Marketing",
  "Inventory",
  "Utilities",
  "Transportation",
  "Miscellaneous",
];

const PAYMENT_METHODS = [
  "Cash",
  "UPI",
  "Debit Card",
  "Bank Transfer",
  "Cheque",
  "Credit (Receivable)",
  "Credit (Payable)",
];

export default function TransactionModal({
  isOpen,
  onClose,
  onSave,
  initialData = null,
}) {
  const isEdit = Boolean(initialData?.id);
  const [form, setForm] = useState({
    transaction_date: new Date().toISOString().slice(0, 10),
    description: "",
    transaction_type: "Revenue",
    category: REVENUE_CATEGORIES[0],
    amount: "",
    payment_method: "UPI",
    notes: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setError("");
    if (initialData) {
      setForm({
        transaction_date: initialData.transaction_date || new Date().toISOString().slice(0, 10),
        description: initialData.description || "",
        transaction_type: initialData.transaction_type || "Revenue",
        category: initialData.category || REVENUE_CATEGORIES[0],
        amount: String(initialData.amount ?? ""),
        payment_method: initialData.payment_method || "UPI",
        notes: initialData.notes || "",
      });
    } else {
      setForm({
        transaction_date: new Date().toISOString().slice(0, 10),
        description: "",
        transaction_type: "Revenue",
        category: REVENUE_CATEGORIES[0],
        amount: "",
        payment_method: "UPI",
        notes: "",
      });
    }
  }, [isOpen, initialData]);

  if (!isOpen) return null;

  const categories =
    form.transaction_type === "Revenue" ? REVENUE_CATEGORIES : EXPENSE_CATEGORIES;
  const categoryOptions = categories.includes(form.category)
    ? categories
    : [form.category, ...categories].filter(Boolean);

  const handleTypeChange = (nextType) => {
    const nextCats = nextType === "Revenue" ? REVENUE_CATEGORIES : EXPENSE_CATEGORIES;
    setForm((prev) => ({
      ...prev,
      transaction_type: nextType,
      category: nextCats.includes(prev.category) ? prev.category : nextCats[0],
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.transaction_date) {
      setError("Transaction date is required.");
      return;
    }
    if (!form.description.trim()) {
      setError("Description is required.");
      return;
    }
    const amt = Number(form.amount);
    if (!Number.isFinite(amt) || amt <= 0) {
      setError("Amount must be a number greater than 0.");
      return;
    }

    setSubmitting(true);
    try {
      await onSave({
        ...form,
        description: form.description.trim(),
        amount: amt,
        notes: form.notes.trim(),
      });
      onClose();
    } catch (err) {
      setError(err.message || "Failed to save transaction.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
      <div className="w-full max-w-lg rounded-lg border border-slate-200 bg-white shadow-lg">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3.5">
          <h2 className="text-base font-semibold text-slate-900">
            {isEdit ? `Edit Transaction #${initialData.id}` : "Add New Transaction"}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-5">
          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700">
                Transaction Type
              </label>
              <div className="grid grid-cols-2 gap-1.5 rounded-md border border-slate-200 bg-slate-50 p-1">
                {["Revenue", "Expense"].map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => handleTypeChange(t)}
                    className={`rounded py-1.5 text-xs font-semibold transition-colors ${
                      form.transaction_type === t
                        ? t === "Revenue"
                          ? "bg-emerald-600 text-white"
                          : "bg-amber-600 text-white"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700">
                Date
              </label>
              <input
                type="date"
                required
                value={form.transaction_date}
                onChange={(e) => setForm({ ...form, transaction_date: e.target.value })}
                className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-900 focus:border-blue-800 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Description
            </label>
            <input
              type="text"
              required
              maxLength={200}
              placeholder="e.g., Retail grocery sales counter or Wholesale rice stock"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-blue-800 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700">
                Category
              </label>
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-blue-800 focus:outline-none"
              >
                {categoryOptions.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700">
                Amount
              </label>
              <input
                type="number"
                required
                min="0.01"
                step="0.01"
                placeholder="0.00"
                value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 tabular-nums focus:border-blue-800 focus:outline-none"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-700">
                Payment Method
              </label>
              <select
                value={form.payment_method}
                onChange={(e) => setForm({ ...form, payment_method: e.target.value })}
                className="w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-blue-800 focus:outline-none"
              >
                {PAYMENT_METHODS.map((pm) => (
                  <option key={pm} value={pm}>
                    {pm}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-700">
              Notes (Optional)
            </label>
            <textarea
              rows={2}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              placeholder="Invoice reference, supplier name, or remarks"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-blue-800 focus:outline-none"
            />
          </div>

          <div className="flex items-center justify-end gap-2 border-t border-slate-100 pt-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {submitting ? "Saving..." : isEdit ? "Update Transaction" : "Add Transaction"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
