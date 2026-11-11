import { useState } from "react";
import { AlertTriangle, CheckCircle2, Download, FileUp, Upload, X } from "lucide-react";
import { api } from "../api/client";
import { formatCurrency } from "../utils/formatters";

export default function CsvImportModal({ isOpen, onClose, onImported, currency = "INR" }) {
  const [file, setFile] = useState(null);
  const [replaceExisting, setReplaceExisting] = useState(false);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resultMsg, setResultMsg] = useState("");

  if (!isOpen) return null;

  const resetState = () => {
    setFile(null);
    setPreview(null);
    setError("");
    setResultMsg("");
    setReplaceExisting(false);
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  const handleFilePick = async (picked) => {
    if (!picked) return;
    setFile(picked);
    setError("");
    setResultMsg("");
    setPreview(null);
    setLoading(true);
    try {
      const res = await api.uploadCsvFile(picked, "preview", replaceExisting);
      setPreview(res);
    } catch (err) {
      setError(err.payload?.error || err.message || "Failed to validate CSV file.");
    } finally {
      setLoading(false);
    }
  };

  const handleCommit = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.uploadCsvFile(file, "import", replaceExisting);
      setResultMsg(res.message);
      onImported(res);
    } catch (err) {
      setError(err.message || "CSV import failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
      <div className="flex max-h-[90vh] w-full max-w-3xl flex-col rounded-lg border border-slate-200 bg-white shadow-lg">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3.5">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Import Financial Data (CSV)</h2>
            <p className="text-xs text-slate-500">
              Validates headers, dates, amounts, missing fields, and prevents duplicate entries
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs">
            <span className="text-slate-600">
              Required columns:{" "}
              <code className="font-mono text-slate-900">
                transaction_date, description, transaction_type, category, amount, payment_method
              </code>
            </span>
            <a
              href={api.getCsvTemplateUrl()}
              download="fintrack_import_template.csv"
              className="inline-flex items-center gap-1.5 font-semibold text-blue-800 hover:underline"
            >
              <Download className="h-3.5 w-3.5" />
              Download Sample Template
            </a>
          </div>

          <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50/50 px-6 py-7 text-center hover:border-blue-700 hover:bg-slate-50">
            <FileUp className="mb-2 h-7 w-7 text-slate-400" />
            <span className="text-sm font-medium text-slate-800">
              {file ? file.name : "Choose a CSV file to validate and preview"}
            </span>
            <span className="mt-1 text-xs text-slate-500">UTF-8 CSV files up to 10 MB</span>
            <input
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={(e) => handleFilePick(e.target.files?.[0])}
            />
          </label>

          <label className="flex items-center gap-2 text-xs text-slate-700">
            <input
              type="checkbox"
              checked={replaceExisting}
              onChange={(e) => setReplaceExisting(e.target.checked)}
              className="rounded border-slate-300"
            />
            Replace all existing database transactions on import (uncheck to append & deduplicate)
          </label>

          {loading && (
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
              Processing CSV validation...
            </div>
          )}

          {error && (
            <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-700">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {resultMsg && (
            <div className="flex items-start gap-2 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-xs font-medium text-emerald-800">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{resultMsg}</span>
            </div>
          )}

          {preview && !resultMsg && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded border border-slate-200 bg-slate-50 p-3">
                  <div className="text-[11px] text-slate-500">Total Rows</div>
                  <div className="text-lg font-bold text-slate-900 tabular-nums">{preview.total_rows}</div>
                </div>
                <div className="rounded border border-emerald-200 bg-emerald-50 p-3">
                  <div className="text-[11px] text-emerald-700">Valid to Import</div>
                  <div className="text-lg font-bold text-emerald-800 tabular-nums">{preview.valid_count}</div>
                </div>
                <div className="rounded border border-amber-200 bg-amber-50 p-3">
                  <div className="text-[11px] text-amber-700">Duplicates Skipped</div>
                  <div className="text-lg font-bold text-amber-800 tabular-nums">{preview.duplicate_count}</div>
                </div>
                <div className="rounded border border-red-200 bg-red-50 p-3">
                  <div className="text-[11px] text-red-700">Failed Validation</div>
                  <div className="text-lg font-bold text-red-800 tabular-nums">{preview.invalid_count}</div>
                </div>
              </div>

              {preview.errors.length > 0 && (
                <div>
                  <h4 className="mb-1.5 text-xs font-semibold text-red-700">
                    Validation Errors ({preview.errors.length})
                  </h4>
                  <div className="max-h-36 overflow-y-auto rounded border border-red-200 bg-red-50/40 text-xs">
                    {preview.errors.map((errItem) => (
                      <div
                        key={`${errItem.row_number}-${errItem.reason}`}
                        className="border-b border-red-100 px-3 py-1.5 last:border-b-0"
                      >
                        <span className="font-semibold text-red-800">Row {errItem.row_number}:</span>{" "}
                        <span className="text-red-700">{errItem.reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {preview.duplicates.length > 0 && (
                <div>
                  <h4 className="mb-1.5 text-xs font-semibold text-amber-800">
                    Duplicate Rows Blocked ({preview.duplicates.length})
                  </h4>
                  <div className="max-h-32 overflow-y-auto rounded border border-amber-200 bg-amber-50/40 text-xs">
                    {preview.duplicates.map((dup) => (
                      <div
                        key={`${dup.row_number}-${dup.record.description}`}
                        className="border-b border-amber-100 px-3 py-1.5 last:border-b-0"
                      >
                        <span className="font-semibold text-amber-900">Row {dup.row_number}:</span>{" "}
                        {dup.record.transaction_date} — {dup.record.description} ({dup.reason})
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {preview.valid_rows.length > 0 && (
                <div>
                  <h4 className="mb-1.5 text-xs font-semibold text-slate-700">
                    Preview of Valid Records (showing up to 25)
                  </h4>
                  <div className="max-h-52 overflow-auto rounded border border-slate-200">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 text-[11px] uppercase text-slate-500">
                        <tr>
                          <th className="px-3 py-2">Date</th>
                          <th className="px-3 py-2">Description</th>
                          <th className="px-3 py-2">Type</th>
                          <th className="px-3 py-2">Category</th>
                          <th className="px-3 py-2">Method</th>
                          <th className="px-3 py-2 text-right">Amount</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {preview.valid_rows.slice(0, 25).map((r) => (
                          <tr key={r.row_number}>
                            <td className="px-3 py-1.5 tabular-nums">{r.transaction_date}</td>
                            <td className="px-3 py-1.5 font-medium text-slate-800">{r.description}</td>
                            <td className="px-3 py-1.5">{r.transaction_type}</td>
                            <td className="px-3 py-1.5">{r.category}</td>
                            <td className="px-3 py-1.5">{r.payment_method}</td>
                            <td className="px-3 py-1.5 text-right font-semibold tabular-nums">
                              {formatCurrency(r.amount, currency)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-5 py-3.5">
          <button
            type="button"
            onClick={handleClose}
            className="rounded-md border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            {resultMsg ? "Done" : "Cancel"}
          </button>
          {!resultMsg && (
            <button
              type="button"
              disabled={loading || !preview || (preview.valid_count === 0 && !replaceExisting)}
              onClick={handleCommit}
              className="inline-flex items-center gap-1.5 rounded-md bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              <Upload className="h-3.5 w-3.5" />
              Import {preview?.valid_count || 0} Valid Records
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
