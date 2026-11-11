import { useEffect, useState } from "react";
import { Download, FileSpreadsheet, FileText } from "lucide-react";
import { api } from "../api/client";
import { RevenueVsExpenseChart } from "../components/ChartsGrid";
import { useGlobalFilter } from "../context/FilterContext";
import { formatCurrency, formatNumber, formatPercent } from "../utils/formatters";

export default function ReportsPage() {
  const { settings, refreshVersion } = useGlobalFilter();
  const [reportType, setReportType] = useState("monthly");
  const [periodKey, setPeriodKey] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api
      .getReports({
        report_type: reportType,
        period_key: periodKey || undefined,
      })
      .then((res) => {
        if (!active) return;
        setReport(res);
        // Ensure periodKey aligns with available options on reportType switch
        const avail = res.available_periods || {};
        const list =
          reportType === "monthly"
            ? avail.months
            : reportType === "quarterly"
            ? avail.quarters
            : avail.years;
        if (list?.length && (!periodKey || !list.some((x) => x.value === periodKey))) {
          setPeriodKey(list[0].value);
        }
      })
      .catch((err) => {
        if (active) setError(err.message || "Failed to generate report.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reportType, periodKey, refreshVersion]);

  const handleReportTypeChange = (nextType) => {
    setPeriodKey("");
    setReportType(nextType);
  };

  const currency = report?.settings?.currency || settings.currency || "INR";
  const avail = report?.available_periods || {};
  const periodOptions =
    reportType === "monthly"
      ? avail.months || []
      : reportType === "quarterly"
      ? avail.quarters || []
      : avail.years || [];

  const summary = report?.summary || {};
  const meta = report?.report_meta || {};

  const csvDownloadUrl = api.getCsvExportUrl({
    report_type: reportType,
    period_key: periodKey || undefined,
  });
  const pdfDownloadUrl = api.getPdfExportUrl({
    report_type: reportType,
    period_key: periodKey || undefined,
  });

  return (
    <div className="space-y-6">
      {/* Report Configuration Toolbar */}
      <div className="flex flex-wrap items-end justify-between gap-4 rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-700">
              Report Frequency
            </label>
            <div className="inline-flex rounded-md border border-slate-200 bg-slate-50 p-1">
              {[
                { value: "monthly", label: "Monthly" },
                { value: "quarterly", label: "Quarterly" },
                { value: "annual", label: "Annual" },
              ].map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => handleReportTypeChange(opt.value)}
                  className={`rounded px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                    reportType === opt.value
                      ? "bg-slate-900 text-white"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-700">
              Select Period
            </label>
            <select
              value={periodKey}
              onChange={(e) => setPeriodKey(e.target.value)}
              className="min-w-[200px] rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-900"
            >
              {periodOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <a
            href={csvDownloadUrl}
            download
            className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50"
          >
            <FileSpreadsheet className="h-4 w-4 text-emerald-700" />
            Export CSV
          </a>
          <a
            href={pdfDownloadUrl}
            download
            className="inline-flex items-center gap-1.5 rounded-md bg-blue-900 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-800"
          >
            <Download className="h-4 w-4" />
            Download PDF Summary
          </a>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-xs text-red-700">
          {error}
        </div>
      )}

      {loading && !report ? (
        <div className="h-72 animate-pulse rounded-lg border border-slate-200 bg-white" />
      ) : (
        report && (
          <div className="space-y-6">
            {/* Report Header Card */}
            <div className="rounded-lg border border-slate-200 bg-white p-6">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <FileText className="h-5 w-5 text-blue-900" />
                    <h2 className="text-base font-bold text-slate-900">{meta.title}</h2>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    Entity: <strong className="text-slate-700">{report.settings?.business_name}</strong>{" "}
                    • Window: {meta.start_date} to {meta.end_date} • Generated {meta.generated_at}
                  </p>
                </div>
                {report.settings?.is_demo_data && (
                  <span className="rounded border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-semibold text-amber-800">
                    DEMONSTRATION DATA
                  </span>
                )}
              </div>

              {/* Financial Summary Grid */}
              <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
                <div>
                  <div className="text-[11px] font-medium text-slate-500">Revenue Summary</div>
                  <div className="mt-1 text-lg font-bold text-emerald-700 tabular-nums">
                    {formatCurrency(summary.total_revenue, currency)}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-medium text-slate-500">Expense Summary</div>
                  <div className="mt-1 text-lg font-bold text-amber-700 tabular-nums">
                    {formatCurrency(summary.total_expenses, currency)}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-medium text-slate-500">Net Profit</div>
                  <div
                    className={`mt-1 text-lg font-bold tabular-nums ${
                      summary.net_profit >= 0 ? "text-slate-900" : "text-red-700"
                    }`}
                  >
                    {formatCurrency(summary.net_profit, currency)}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-medium text-slate-500">Profit Margin</div>
                  <div className="mt-1 text-lg font-bold text-slate-900 tabular-nums">
                    {formatPercent(summary.profit_margin, 2)}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-medium text-slate-500">Net Cash Flow</div>
                  <div
                    className={`mt-1 text-lg font-bold tabular-nums ${
                      summary.cash_flow >= 0 ? "text-emerald-700" : "text-red-700"
                    }`}
                  >
                    {formatCurrency(summary.cash_flow, currency)}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] font-medium text-slate-500">Sales Volume</div>
                  <div className="mt-1 text-lg font-bold text-slate-900 tabular-nums">
                    {formatNumber(summary.total_sales_transactions)} txns
                  </div>
                </div>
              </div>
            </div>

            {/* Chart & Observations */}
            <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
              <RevenueVsExpenseChart
                data={report.chart_series}
                currency={currency}
                granularity={report.granularity}
              />

              <div className="rounded-lg border border-slate-200 bg-white p-5">
                <h3 className="text-sm font-semibold text-slate-900">
                  Business Performance Observations
                </h3>
                <p className="mb-4 text-xs text-slate-500">
                  Executive findings included in PDF export
                </p>
                <ul className="space-y-2.5 text-xs text-slate-700">
                  {(report.observations || []).map((obs, idx) => (
                    <li
                      key={idx}
                      className="flex items-start gap-2.5 rounded-md border border-slate-100 bg-slate-50 px-3.5 py-2.5 leading-relaxed"
                    >
                      <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-blue-900 text-[10px] font-bold text-white">
                        {idx + 1}
                      </span>
                      <span>{obs}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Category Breakdown Tables */}
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              <div className="rounded-lg border border-slate-200 bg-white p-5">
                <h3 className="mb-3 text-sm font-semibold text-slate-900">
                  Revenue Summary by Category
                </h3>
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-200 bg-slate-50 text-[11px] uppercase text-slate-500">
                    <tr>
                      <th className="px-3 py-2">Category</th>
                      <th className="px-3 py-2 text-right">Count</th>
                      <th className="px-3 py-2 text-right">Amount</th>
                      <th className="px-3 py-2 text-right">Share</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 tabular-nums">
                    {(report.revenue_by_category || []).map((r) => (
                      <tr key={r.category}>
                        <td className="px-3 py-2 font-medium text-slate-800">{r.category}</td>
                        <td className="px-3 py-2 text-right text-slate-600">{r.count}</td>
                        <td className="px-3 py-2 text-right font-semibold text-emerald-700">
                          {formatCurrency(r.amount, currency)}
                        </td>
                        <td className="px-3 py-2 text-right text-slate-600">
                          {r.percentage.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-5">
                <h3 className="mb-3 text-sm font-semibold text-slate-900">
                  Expense Summary by Category
                </h3>
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-200 bg-slate-50 text-[11px] uppercase text-slate-500">
                    <tr>
                      <th className="px-3 py-2">Category</th>
                      <th className="px-3 py-2 text-right">Count</th>
                      <th className="px-3 py-2 text-right">Amount</th>
                      <th className="px-3 py-2 text-right">Share</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 tabular-nums">
                    {(report.expense_by_category || []).map((r) => (
                      <tr key={r.category}>
                        <td className="px-3 py-2 font-medium text-slate-800">{r.category}</td>
                        <td className="px-3 py-2 text-right text-slate-600">{r.count}</td>
                        <td className="px-3 py-2 text-right font-semibold text-slate-900">
                          {formatCurrency(r.amount, currency)}
                        </td>
                        <td className="px-3 py-2 text-right text-slate-600">
                          {r.percentage.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )
      )}
    </div>
  );
}
