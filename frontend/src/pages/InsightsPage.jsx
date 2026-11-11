import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Lightbulb,
  SlidersHorizontal,
  TrendingUp,
} from "lucide-react";
import { api } from "../api/client";
import { useGlobalFilter } from "../context/FilterContext";

const CATEGORY_META = {
  positive: {
    label: "Positive Performance",
    icon: CheckCircle2,
    border: "border-emerald-200",
    bg: "bg-emerald-50/40",
    badge: "bg-emerald-100 text-emerald-800",
    iconColor: "text-emerald-700",
  },
  growth: {
    label: "Revenue Growth",
    icon: TrendingUp,
    border: "border-blue-200",
    bg: "bg-blue-50/40",
    badge: "bg-blue-100 text-blue-900",
    iconColor: "text-blue-800",
  },
  warning: {
    label: "Financial Warning",
    icon: AlertTriangle,
    border: "border-red-200",
    bg: "bg-red-50/40",
    badge: "bg-red-100 text-red-800",
    iconColor: "text-red-700",
  },
  optimization: {
    label: "Expense Optimization",
    icon: SlidersHorizontal,
    border: "border-amber-200",
    bg: "bg-amber-50/40",
    badge: "bg-amber-100 text-amber-800",
    iconColor: "text-amber-700",
  },
  recommendation: {
    label: "Profitability Recommendation",
    icon: Lightbulb,
    border: "border-slate-200",
    bg: "bg-white",
    badge: "bg-slate-100 text-slate-800",
    iconColor: "text-slate-700",
  },
};

export default function InsightsPage() {
  const { filterParams, refreshVersion } = useGlobalFilter();
  const [data, setData] = useState(null);
  const [activeGroup, setActiveGroup] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api
      .getInsights(filterParams)
      .then((res) => {
        if (active) setData(res);
      })
      .catch((err) => {
        if (active) setError(err.message || "Failed to generate insights.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [filterParams.period, filterParams.start_date, filterParams.end_date, refreshVersion]);

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

  const insights = data?.insights || [];
  const summary = data?.summary || {};

  const filtered = insights.filter((item) => {
    if (activeGroup === "all") return true;
    if (activeGroup === "positive") return item.category === "positive" || item.category === "growth";
    if (activeGroup === "warning") return item.category === "warning";
    if (activeGroup === "optimization")
      return item.category === "optimization" || item.category === "recommendation";
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Summary Counters */}
      <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="text-xs font-medium text-slate-500">Generated Insights</div>
          <div className="mt-1 text-2xl font-bold text-slate-900 tabular-nums">
            {summary.total_insights || 0}
          </div>
        </div>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-4">
          <div className="text-xs font-medium text-emerald-700">Positive & Growth</div>
          <div className="mt-1 text-2xl font-bold text-emerald-900 tabular-nums">
            {summary.positive_count || 0}
          </div>
        </div>
        <div className="rounded-lg border border-red-200 bg-red-50/50 p-4">
          <div className="text-xs font-medium text-red-700">Warning Indicators</div>
          <div className="mt-1 text-2xl font-bold text-red-900 tabular-nums">
            {summary.warning_count || 0}
          </div>
        </div>
        <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4">
          <div className="text-xs font-medium text-amber-800">Optimization & Actions</div>
          <div className="mt-1 text-2xl font-bold text-amber-900 tabular-nums">
            {summary.optimization_count || 0}
          </div>
        </div>
      </section>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1.5">
          {[
            { id: "all", label: "All Insights" },
            { id: "positive", label: "Positive & Growth" },
            { id: "warning", label: "Warnings" },
            { id: "optimization", label: "Optimization & Recommendations" },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveGroup(tab.id)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                activeGroup === tab.id
                  ? "bg-slate-900 text-white"
                  : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <span className="text-xs text-slate-500">
          Computed live from SQLite for <strong>{data?.filter?.label}</strong>
        </span>
      </div>

      {/* Insight Cards */}
      <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {filtered.length === 0 ? (
          <div className="col-span-full rounded-lg border border-dashed border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
            No insights match this category filter.
          </div>
        ) : (
          filtered.map((item, idx) => {
            const meta = CATEGORY_META[item.category] || CATEGORY_META.recommendation;
            const Icon = meta.icon;
            return (
              <div
                key={`${item.title}-${idx}`}
                className={`flex flex-col justify-between rounded-lg border p-5 ${meta.border} ${meta.bg}`}
              >
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <Icon className={`h-4 w-4 shrink-0 ${meta.iconColor}`} />
                      <span className={`rounded px-2 py-0.5 text-[10px] font-semibold ${meta.badge}`}>
                        {meta.label}
                      </span>
                      <span className="rounded border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-medium text-slate-600">
                        {item.analytics_type}
                      </span>
                    </div>
                    {item.metric_value && (
                      <span className="shrink-0 rounded bg-white px-2 py-0.5 text-xs font-bold text-slate-900 border border-slate-200 tabular-nums">
                        {item.metric_value}
                      </span>
                    )}
                  </div>
                  <h3 className="mt-3 text-sm font-semibold text-slate-900">{item.title}</h3>
                  <p className="mt-1.5 text-xs leading-relaxed text-slate-700">{item.message}</p>
                </div>
              </div>
            );
          })
        )}
      </section>
    </div>
  );
}
