import { useEffect, useState } from "react";
import { AlertCircle, Info, TrendingUp } from "lucide-react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import {
  CashFlowChart,
  SalesPerformanceChart,
} from "../components/ChartsGrid";
import { useGlobalFilter } from "../context/FilterContext";
import { formatCompactCurrency, formatCurrency, formatPercent } from "../utils/formatters";

export default function AnalyticsPage() {
  const { filterParams, settings, refreshVersion } = useGlobalFilter();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api
      .getAnalytics(filterParams)
      .then((res) => {
        if (active) setData(res);
      })
      .catch((err) => {
        if (active) setError(err.message || "Failed to load analytics.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [filterParams.period, filterParams.start_date, filterParams.end_date, refreshVersion]);

  const currency = data?.settings?.currency || settings.currency || "INR";

  if (loading && !data) {
    return <div className="h-64 animate-pulse rounded-lg border border-slate-200 bg-white" />;
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-5 text-xs text-red-700">
        {error}
      </div>
    );
  }

  const m = data?.performance_metrics || {};
  const forecast = data?.forecast || {};
  const charts = data?.charts || {};

  const ratioCards = [
    {
      label: "1. Gross Revenue",
      value: formatCurrency(m.gross_revenue, currency),
      formula: "Sum of all Revenue transactions",
      note: "Top-line sales before operating deductions",
    },
    {
      label: "2. Total Expenses",
      value: formatCurrency(m.total_expenses, currency),
      formula: "Sum of all Expense transactions",
      note: "Combined fixed overheads & variable costs",
    },
    {
      label: "3. Net Profit",
      value: formatCurrency(m.net_profit, currency),
      formula: "Gross Revenue − Total Expenses",
      note: m.net_profit >= 0 ? "Positive accounting earnings" : "Operating deficit in period",
    },
    {
      label: "4. Profit Margin",
      value: formatPercent(m.profit_margin, 2),
      formula: "(Net Profit / Gross Revenue) × 100",
      note: "Share of each rupee retained as profit",
    },
    {
      label: "5. Expense Ratio",
      value: formatPercent(m.expense_ratio, 2),
      formula: "(Total Expenses / Gross Revenue) × 100",
      note: "Operating cost burden per rupee earned",
    },
    {
      label: "6. Revenue Growth Rate",
      value: formatPercent(m.revenue_growth_rate, 1, true),
      formula: "Period-over-Period % Δ",
      note: `Compared vs ${data?.filter?.comparison_label || "prior period"}`,
    },
    {
      label: "7. Expense Growth Rate",
      value: formatPercent(m.expense_growth_rate, 1, true),
      formula: "Period-over-Period % Δ",
      note: `Compared vs ${data?.filter?.comparison_label || "prior period"}`,
    },
    {
      label: "8. Avg Transaction Value",
      value: formatCurrency(m.avg_transaction_value, currency),
      formula: `Median: ${formatCurrency(m.median_transaction_value, currency)} | σ: ${formatCurrency(m.std_transaction_value, currency)}`,
      note: "Mean, median & std dev via NumPy",
    },
  ];

  return (
    <div className="space-y-6">
      {/* 5 Business Analytics Pillars */}
      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {[
          { tag: "Descriptive", title: "What happened?", text: `Gross revenue ${formatCurrency(m.gross_revenue, currency)} & profit ${formatCurrency(m.net_profit, currency)}.` },
          { tag: "Diagnostic", title: "Why did it happen?", text: `Expense ratio at ${formatPercent(m.expense_ratio, 1)}; credit accruals explain profit-cash gaps.` },
          { tag: "Trend", title: "How is it changing?", text: "Monthly series track inflection points across seasons." },
          { tag: "Comparative", title: "Period comparison", text: `Revenue ${formatPercent(m.revenue_growth_rate, 1, true)} vs ${data?.filter?.comparison_label}.` },
          { tag: "Predictive", title: "What comes next?", text: "OLS regression forecasts the next 3 completed months." },
        ].map((item) => (
          <div key={item.tag} className="rounded-lg border border-slate-200 bg-white p-3.5">
            <span className="inline-block rounded bg-blue-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-blue-900">
              {item.tag} Analytics
            </span>
            <div className="mt-1.5 text-xs font-semibold text-slate-900">{item.title}</div>
            <p className="mt-1 text-[11px] leading-relaxed text-slate-600">{item.text}</p>
          </div>
        ))}
      </section>

      {/* Metrics 1..8 Grid */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-slate-900">
          Business Performance Metrics ({data?.filter?.label})
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {ratioCards.map((c) => (
            <div key={c.label} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="text-xs font-semibold text-slate-500">{c.label}</div>
              <div className="mt-1.5 text-xl font-bold text-slate-900 tabular-nums">{c.value}</div>
              <div className="mt-2 rounded bg-slate-50 px-2 py-1 font-mono text-[10px] text-slate-600">
                {c.formula}
              </div>
              <div className="mt-1.5 text-[11px] text-slate-500">{c.note}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Metric 9 & 10: Operating Expense Breakdown + Cash Flow vs Profit */}
      <section className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-slate-900">
            9. Operating Expense Breakdown
          </h3>
          <p className="mb-4 text-xs text-slate-500">
            Category allocation and share of total operating expenses
          </p>
          <div className="space-y-3">
            {(m.operating_expense_breakdown || []).map((item) => (
              <div key={item.category}>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-800">{item.category}</span>
                  <span className="tabular-nums text-slate-700">
                    <span className="font-semibold text-slate-900">
                      {formatCurrency(item.amount, currency)}
                    </span>{" "}
                    ({item.percentage.toFixed(1)}%)
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-blue-900"
                    style={{ width: `${Math.min(100, item.percentage)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-slate-900">
            10. Cash Flow vs. Accounting Profit Reconciliation
          </h3>
          <p className="mb-4 text-xs text-slate-500">
            Separates explicitly cash-settled transactions from deferred credit accruals
          </p>

          <div className="space-y-2.5 text-xs">
            <div className="flex justify-between rounded border border-slate-100 bg-slate-50 px-3.5 py-2.5">
              <span className="text-slate-600">Cash Inflows (Cash, UPI, Bank, Card, Cheque)</span>
              <span className="font-semibold text-emerald-700 tabular-nums">
                {formatCurrency(m.cash_inflow, currency)}
              </span>
            </div>
            <div className="flex justify-between rounded border border-slate-100 bg-slate-50 px-3.5 py-2.5">
              <span className="text-slate-600">Cash Outflows (Cash-Settled Expenses)</span>
              <span className="font-semibold text-amber-700 tabular-nums">
                {formatCurrency(m.cash_outflow, currency)}
              </span>
            </div>
            <div className="flex justify-between rounded border border-slate-200 bg-white px-3.5 py-2.5">
              <span className="font-semibold text-slate-900">Actual Net Cash Flow</span>
              <span
                className={`font-bold tabular-nums ${
                  m.net_cash_flow >= 0 ? "text-emerald-700" : "text-red-700"
                }`}
              >
                {formatCurrency(m.net_cash_flow, currency)}
              </span>
            </div>
            <div className="flex justify-between rounded border border-slate-100 bg-slate-50 px-3.5 py-2">
              <span className="text-slate-600">Uncollected Credit Receivables (Non-Cash Revenue)</span>
              <span className="font-medium text-slate-800 tabular-nums">
                {formatCurrency(m.accrual_receivables, currency)}
              </span>
            </div>
            <div className="flex justify-between rounded border border-slate-100 bg-slate-50 px-3.5 py-2">
              <span className="text-slate-600">Unpaid Credit Payables (Non-Cash Expense)</span>
              <span className="font-medium text-slate-800 tabular-nums">
                {formatCurrency(m.accrual_payables, currency)}
              </span>
            </div>
            <div className="flex items-start gap-2 rounded-md border border-blue-200 bg-blue-50/60 p-3 text-[11px] text-blue-950">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-800" />
              <span>
                <strong>Profit vs. Cash Flow Variance:</strong>{" "}
                {formatCurrency(m.profit_vs_cash_variance, currency)}. Positive accounting profit
                does not guarantee positive cash liquidity if sales sit in receivables or cash was
                pre-spent on bulk inventory.
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Predictive Analytics: 3-Month Revenue Forecast */}
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-blue-900" />
              <h3 className="text-sm font-semibold text-slate-900">
                Predictive Analytics — 3-Month Revenue Forecast
              </h3>
            </div>
            <p className="mt-0.5 text-xs text-slate-500">
              {forecast.method || "Historical linear regression time-series forecast"}
            </p>
          </div>
          {forecast.model_stats && (
            <div className="flex flex-wrap gap-2 text-[11px]">
              <span className="rounded border border-slate-200 bg-slate-50 px-2.5 py-1 text-slate-700 tabular-nums">
                Monthly Slope:{" "}
                <strong className={forecast.model_stats.monthly_slope >= 0 ? "text-emerald-700" : "text-red-700"}>
                  {forecast.model_stats.monthly_slope >= 0 ? "+" : ""}
                  {formatCurrency(forecast.model_stats.monthly_slope, currency)}/mo
                </strong>
              </span>
              <span className="rounded border border-slate-200 bg-slate-50 px-2.5 py-1 text-slate-700 tabular-nums">
                R² Fit: <strong>{forecast.model_stats.r_squared}</strong>
              </span>
            </div>
          )}
        </div>

        <div className="mb-4 flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50/70 px-3.5 py-2.5 text-xs text-amber-900">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
          <span>{forecast.disclaimer}</span>
        </div>

        {!forecast.can_forecast ? (
          <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 p-6 text-center text-xs text-slate-500">
            {forecast.reason}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
            <div className="h-72 lg:col-span-2">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={forecast.combined_series}
                  margin={{ top: 8, right: 12, left: 0, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#64748B" }} />
                  <YAxis
                    tick={{ fontSize: 11, fill: "#64748B" }}
                    tickFormatter={(v) => formatCompactCurrency(v, currency)}
                  />
                  <Tooltip
                    formatter={(val, name) => [
                      val !== null ? formatCurrency(val, currency) : "—",
                      name,
                    ]}
                    contentStyle={{ fontSize: "12px", borderRadius: "6px", borderColor: "#E2E8F0" }}
                  />
                  <Legend wrapperStyle={{ fontSize: "12px" }} />
                  <Area
                    type="monotone"
                    dataKey="upper_bound"
                    name="Upper Estimate"
                    stroke="none"
                    fill="#DBEAFE"
                    fillOpacity={0.55}
                  />
                  <Line
                    type="monotone"
                    dataKey="actual_revenue"
                    name="Historical Revenue"
                    stroke="#0F172A"
                    strokeWidth={2.25}
                    dot={{ r: 3.5 }}
                    connectNulls={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="trend_line"
                    name="OLS Regression Trend"
                    stroke="#64748B"
                    strokeDasharray="5 4"
                    strokeWidth={1.5}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="forecast_revenue"
                    name="Forecasted Revenue"
                    stroke="#059669"
                    strokeWidth={2.5}
                    strokeDasharray="4 2"
                    dot={{ r: 4.5, fill: "#059669" }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            <div className="space-y-2.5">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Next 3 Months Projected Estimates
              </div>
              {(forecast.forecast || []).map((fp) => (
                <div
                  key={fp.period}
                  className="rounded-md border border-slate-200 bg-slate-50/70 p-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-800">{fp.label}</span>
                    <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">
                      Estimate
                    </span>
                  </div>
                  <div className="mt-1 text-lg font-bold text-slate-900 tabular-nums">
                    {formatCurrency(fp.forecast_revenue, currency)}
                  </div>
                  <div className="mt-1 text-[11px] text-slate-500 tabular-nums">
                    Range: {formatCurrency(fp.lower_bound, currency)} –{" "}
                    {formatCurrency(fp.upper_bound, currency)}
                  </div>
                </div>
              ))}
              {forecast.partial_month_excluded && (
                <div className="text-[11px] text-slate-500">
                  Note: Partial month-to-date ({forecast.partial_month_excluded}) was excluded from
                  regression slope calculation to prevent downward bias.
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      {/* Supporting Charts */}
      <section className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <CashFlowChart
          data={charts.monthly_series}
          currency={currency}
          granularity="monthly"
        />
        <SalesPerformanceChart salesPerformance={charts.sales_performance} currency={currency} />
      </section>
    </div>
  );
}
