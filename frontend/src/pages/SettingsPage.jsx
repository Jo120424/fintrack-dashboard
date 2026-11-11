import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Database, RotateCcw, Save, Trash2 } from "lucide-react";
import { api } from "../api/client";
import { useGlobalFilter } from "../context/FilterContext";
import { formatNumber, formatShortDate } from "../utils/formatters";

export default function SettingsPage() {
  const { setSettings, triggerRefresh, refreshVersion } = useGlobalFilter();
  const [businessName, setBusinessName] = useState("SMART MART RETAIL STORE");
  const [currency, setCurrency] = useState("INR");
  const [currencies, setCurrencies] = useState([]);
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [isDemoData, setIsDemoData] = useState(true);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [confirmAction, setConfirmAction] = useState(null); // "reset" | "clear"

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .getSettings()
      .then((res) => {
        if (!active) return;
        setBusinessName(res.settings.business_name);
        setCurrency(res.settings.currency);
        setIsDemoData(Boolean(res.settings.is_demo_data));
        setCurrencies(res.supported_currencies || []);
        setDatasetInfo(res.dataset_info || {});
      })
      .catch((err) => {
        if (active) setError(err.message || "Failed to load settings.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [refreshVersion]);

  const handleSave = async (e) => {
    e.preventDefault();
    setMessage("");
    setError("");
    if (!businessName.trim()) {
      setError("Business name cannot be empty.");
      return;
    }
    setSaving(true);
    try {
      const res = await api.updateSettings({
        business_name: businessName.trim(),
        currency,
      });
      setSettings(res.settings);
      setMessage(res.message);
      triggerRefresh();
    } catch (err) {
      setError(err.message || "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  };

  const handleDatasetAction = async () => {
    setMessage("");
    setError("");
    setSaving(true);
    try {
      const res =
        confirmAction === "reset" ? await api.resetDemoData() : await api.clearAllData();
      setMessage(res.message);
      setConfirmAction(null);
      triggerRefresh();
    } catch (err) {
      setError(err.message || "Dataset operation failed.");
    } finally {
      setSaving(false);
    }
  };

  if (loading && !datasetInfo) {
    return <div className="h-56 animate-pulse rounded-lg border border-slate-200 bg-white" />;
  }

  return (
    <div className="max-w-4xl space-y-6">
      {message && (
        <div className="flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs font-medium text-emerald-800">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{message}</span>
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-xs font-medium text-red-700">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Business Profile Settings */}
      <form
        onSubmit={handleSave}
        className="rounded-lg border border-slate-200 bg-white p-6 space-y-4"
      >
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Business Profile & Currency</h2>
          <p className="text-xs text-slate-500">
            Configure organization display name and default reporting currency
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-700">
              Business Name
            </label>
            <input
              type="text"
              required
              maxLength={120}
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-blue-800 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-700">
              Reporting Currency
            </label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-800 focus:outline-none"
            >
              {currencies.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.name} ({c.symbol})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex justify-end border-t border-slate-100 pt-3">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            <Save className="h-3.5 w-3.5" />
            Save Settings
          </button>
        </div>
      </form>

      {/* Dataset Information & Reset */}
      <div className="rounded-lg border border-slate-200 bg-white p-6 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-blue-900" />
            <h2 className="text-sm font-semibold text-slate-900">SQLite Dataset Information</h2>
          </div>
          <span
            className={`rounded px-2.5 py-0.5 text-[11px] font-semibold ${
              isDemoData
                ? "border border-amber-200 bg-amber-50 text-amber-800"
                : "border border-emerald-200 bg-emerald-50 text-emerald-800"
            }`}
          >
            {isDemoData ? "DEMONSTRATION DATA ACTIVE" : "USER / CUSTOM DATASET"}
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3.5">
            <div className="text-[11px] font-medium text-slate-500">Total Stored Transactions</div>
            <div className="mt-1 text-xl font-bold text-slate-900 tabular-nums">
              {formatNumber(datasetInfo?.total_transactions || 0)}
            </div>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3.5">
            <div className="text-[11px] font-medium text-slate-500">Date Span</div>
            <div className="mt-1 text-sm font-semibold text-slate-900 tabular-nums">
              {datasetInfo?.earliest_date
                ? `${formatShortDate(datasetInfo.earliest_date)} – ${formatShortDate(
                    datasetInfo.latest_date
                  )}`
                : "Empty Dataset"}
            </div>
          </div>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3.5">
            <div className="text-[11px] font-medium text-slate-500">Calendar Months Covered</div>
            <div className="mt-1 text-xl font-bold text-slate-900 tabular-nums">
              {datasetInfo?.months_covered || 0} months
            </div>
          </div>
        </div>

        <div className="rounded-md border border-slate-200 bg-slate-50 px-3.5 py-2 text-[11px] text-slate-600">
          SQLite Storage Path:{" "}
          <code className="font-mono text-slate-800">{datasetInfo?.database_path}</code>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
          <div className="text-xs text-slate-600">
            Restore the 12-month synthetic dataset for <strong>SMART MART RETAIL STORE</strong> or
            clear records to import your own CSV.
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setConfirmAction("clear")}
              className="inline-flex items-center gap-1.5 rounded-md border border-red-200 bg-white px-3.5 py-2 text-xs font-semibold text-red-700 hover:bg-red-50"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Clear All Transactions
            </button>
            <button
              type="button"
              onClick={() => setConfirmAction("reset")}
              className="inline-flex items-center gap-1.5 rounded-md bg-blue-900 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-800"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset Demonstration Data
            </button>
          </div>
        </div>
      </div>

      {confirmAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-5 shadow-lg">
            <h3 className="text-sm font-semibold text-slate-900">
              {confirmAction === "reset"
                ? "Reset Demonstration Dataset?"
                : "Clear All Transactions?"}
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-slate-600">
              {confirmAction === "reset"
                ? "This will replace current database transactions with the fresh 12-month SMART MART RETAIL STORE demonstration dataset and restore default settings."
                : "This will delete all stored transactions from SQLite so you can test empty-dataset resilience or upload a fresh CSV."}
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmAction(null)}
                className="rounded-md border border-slate-200 px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={saving}
                onClick={handleDatasetAction}
                className={`rounded-md px-3.5 py-1.5 text-xs font-semibold text-white ${
                  confirmAction === "reset"
                    ? "bg-blue-900 hover:bg-blue-800"
                    : "bg-red-600 hover:bg-red-700"
                }`}
              >
                {saving ? "Processing..." : confirmAction === "reset" ? "Confirm Reset" : "Clear Data"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
