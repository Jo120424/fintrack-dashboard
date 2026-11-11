import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Banknote,
  CreditCard,
  IndianRupee,
  Percent,
  ShoppingBag,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { api } from "../api/client";
import {
  CashFlowChart,
  CategoryDonutChart,
  ProfitTrendChart,
  RevenueVsExpenseChart,
  SalesPerformanceChart,
} from "../components/ChartsGrid";
import KpiCard from "../components/KpiCard";
import { useGlobalFilter } from "../context/FilterContext";
import { formatCurrency, formatNumber, formatPercent, formatShortDate } from "../utils/formatters";

export default function DashboardPage() {
  const { filterParams, settings, refreshVersion } = useGlobalFilter();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api
      .getDashboard(filterParams)
      .then((res) => {
        if (active) setData(res);
      })
      .catch((err) => {
        if (active) setError(err.message || "Failed to load dashboard data.");
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
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-36 animate-pulse rounded-lg border border-slate-200 bg-white p-5" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-5 text-sm text-red-700">
        <div className="font-semibold">Unable to load dashboard metrics</div>
        <p className="mt-1 text-xs">{error}</p>
      </div>
    );
  }

  const kpis = data?.kpis || {};
  const cards = data?.kpi_cards || {};
  const mc = data?.month_comparison || {};
  const curMo = mc.current_month || {};
  const prevMo = mc.previous_month || {};
  const moCards = mc.cards || {};
  const charts = data?.charts || {};
  const recent = data?.recent_transactions || [];

  const fmtDelta = (cardObj, formatter) => {
    if (!cardObj) return null;
    const curLabel = data?.filter?.current_month_label || "This Month";
    const prevLabel = data?.filter?.previous_month_label || "Prev Month";
    const pct = cardObj.change_pct;
    const pctText = pct === null || pct === undefined ? "N/A" : `${pct > 0 ? "+" : ""}${pct.toFixed(1)}%`;
    return `${curLabel}: ${formatter(cardObj.value)} (${pctText} vs ${prevLabel}: ${formatter(cardObj.previous_value)})`;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <div>
          Active Window:{" "}
          <span className="font-semibold text-slate-800">{data?.filter?.label}</span>
          {data?.filter?.start_date && (
            <span className="ml-2">
              ({formatShortDate(data.filter.start_date)} – {formatShortDate(data.filter.end_date)})
            </span>
          )}
        </div>
        {data?.is_empty && (
          <span className="rounded border border-amber-200 bg-amber-50 px-2.5 py-1 font-medium text-amber-800">
            No transactions match this filter. Add data in Transactions or adjust period.
          </span>
        )}
      </div>

      {/* 6 Core Dynamic KPI Cards */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <KpiCard
          title="Total Revenue"
          value={formatCurrency(kpis.total_revenue, currency)}
          icon={IndianRupee}
          accentClass="bg-emerald-50 text-emerald-700"
          comparison={cards.total_revenue}
          monthSnapshot={fmtDelta(moCards.total_revenue, (v) => formatCurrency(v, currency))}
        />
        <KpiCard
          title="Total Expenses"
          value={formatCurrency(kpis.total_expenses, currency)}
          icon={CreditCard}
          accentClass="bg-amber-50 text-amber-700"
          comparison={cards.total_expenses}
          monthSnapshot={fmtDelta(moCards.total_expenses, (v) => formatCurrency(v, currency))}
        />
        <KpiCard
          title="Net Profit"
          value={formatCurrency(kpis.net_profit, currency)}
          icon={TrendingUp}
          accentClass={kpis.net_profit >= 0 ? "bg-blue-50 text-blue-800" : "bg-red-50 text-red-700"}
          comparison={cards.net_profit}
          monthSnapshot={fmtDelta(moCards.net_profit, (v) => formatCurrency(v, currency))}
        />
        <KpiCard
          title="Profit Margin (%)"
          value={formatPercent(kpis.profit_margin, 1)}
          icon={Percent}
          accentClass="bg-slate-100 text-slate-700"
          comparison={cards.profit_margin}
          monthSnapshot={fmtDelta(moCards.profit_margin, (v) => formatPercent(v, 1))}
        />
        <KpiCard
          title="Total Sales Transactions"
          value={formatNumber(kpis.total_sales_transactions)}
          icon={ShoppingBag}
          accentClass="bg-indigo-50 text-indigo-700"
          comparison={cards.total_sales_transactions}
          monthSnapshot={fmtDelta(moCards.total_sales_transactions, (v) => formatNumber(v))}
        />
        <KpiCard
          title="Cash Flow (Net Cash)"
          value={formatCurrency(kpis.cash_flow, currency)}
          icon={Wallet}
          accentClass={kpis.cash_flow >= 0 ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}
          comparison={cards.cash_flow}
          monthSnapshot={fmtDelta(moCards.cash_flow, (v) => formatCurrency(v, currency))}
        />
      </section>

      {/* Primary Charts Row */}
      <section className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <RevenueVsExpenseChart
          data={charts.revenue_vs_expenses}
          currency={currency}
          granularity={charts.granularity}
        />
        <ProfitTrendChart
          data={charts.revenue_vs_expenses}
          currency={currency}
          granularity={charts.granularity}
        />
      </section>

      {/* Distribution Donuts */}
      <section className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <CategoryDonutChart
          title="Revenue Distribution"
          subtitle="Revenue contribution by product and service category"
          data={charts.revenue_distribution}
          currency={currency}
        />
        <CategoryDonutChart
          title="Expense Breakdown"
          subtitle="Operating costs across Rent, Salaries, Marketing, Inventory & overheads"
          data={charts.expense_breakdown}
          currency={currency}
        />
      </section>

      {/* Cash Flow & Sales Performance */}
      <section className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <CashFlowChart
          data={charts.cash_flow_series}
          currency={currency}
          granularity={charts.granularity}
        />
        <SalesPerformanceChart
          salesPerformance={charts.sales_performance}
          currency={currency}
        />
      </section>

      {/* Recent Transactions Preview */}
      <section className="rounded-lg border border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3.5">
          <div className="flex items-center gap-2">
            <Banknote className="h-4 w-4 text-slate-500" />
            <h3 className="text-sm font-semibold text-slate-900">
              Recent Transactions in Selected Period
            </h3>
          </div>
          <Link
            to="/transactions"
            className="inline-flex items-center gap-1 text-xs font-semibold text-blue-800 hover:underline"
          >
            Manage All
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase text-slate-500">
              <tr>
                <th className="px-5 py-2.5">Date</th>
                <th className="px-4 py-2.5">Description</th>
                <th className="px-4 py-2.5">Category</th>
                <th className="px-4 py-2.5">Type</th>
                <th className="px-4 py-2.5">Method</th>
                <th className="px-5 py-2.5 text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {recent.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-slate-500">
                    No transactions available for this date range.
                  </td>
                </tr>
              ) : (
                recent.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-50/70">
                    <td className="px-5 py-2.5 text-slate-600 tabular-nums">
                      {formatShortDate(tx.transaction_date)}
                    </td>
                    <td className="px-4 py-2.5 font-medium text-slate-900">{tx.description}</td>
                    <td className="px-4 py-2.5 text-slate-600">{tx.category}</td>
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
                    <td className="px-4 py-2.5 text-slate-600">{tx.payment_method}</td>
                    <td
                      className={`px-5 py-2.5 text-right font-semibold tabular-nums ${
                        tx.transaction_type === "Revenue" ? "text-emerald-700" : "text-slate-900"
                      }`}
                    >
                      {tx.transaction_type === "Revenue" ? "+" : "-"}
                      {formatCurrency(tx.amount, currency)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
