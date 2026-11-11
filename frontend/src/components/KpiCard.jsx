import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

export default function KpiCard({
  title,
  value,
  icon: Icon,
  accentClass = "text-slate-700 bg-slate-100",
  comparison,
  monthSnapshot,
  subtitle,
}) {
  const pct = comparison?.change_pct;
  const trend = comparison?.trend || "flat";
  const isFavorable = comparison?.is_favorable ?? true;

  let badgeClass = "bg-slate-100 text-slate-600 border-slate-200";
  let TrendIcon = Minus;
  if (trend === "up") {
    TrendIcon = ArrowUpRight;
    badgeClass = isFavorable
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : "bg-red-50 text-red-700 border-red-200";
  } else if (trend === "down") {
    TrendIcon = ArrowDownRight;
    badgeClass = isFavorable
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : "bg-red-50 text-red-700 border-red-200";
  }

  return (
    <div className="flex flex-col justify-between rounded-lg border border-slate-200 bg-white p-5">
      <div>
        <div className="flex items-start justify-between gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {title}
          </span>
          {Icon && (
            <span className={`rounded-md p-1.5 ${accentClass}`}>
              <Icon className="h-4 w-4" />
            </span>
          )}
        </div>

        <div className="mt-2.5 text-2xl font-bold tracking-tight text-slate-900 tabular-nums">
          {value}
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-2">
          {comparison && (
            <span
              className={`inline-flex items-center gap-0.5 rounded border px-1.5 py-0.5 text-[11px] font-semibold tabular-nums ${badgeClass}`}
            >
              <TrendIcon className="h-3 w-3" />
              {pct === null || pct === undefined
                ? "N/A"
                : `${pct > 0 ? "+" : ""}${pct.toFixed(1)}%`}
            </span>
          )}
          <span className="text-xs text-slate-500">
            {comparison?.comparison_label ? `vs ${comparison.comparison_label}` : subtitle}
          </span>
        </div>
      </div>

      {monthSnapshot && (
        <div className="mt-3 border-t border-slate-100 pt-2.5 text-[11px] text-slate-500 tabular-nums">
          {monthSnapshot}
        </div>
      )}
    </div>
  );
}
