import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCompactCurrency, formatCurrency } from "../utils/formatters";

const PALETTE = [
  "#1E3A8A",
  "#059669",
  "#D97706",
  "#0284C7",
  "#64748B",
  "#DC2626",
  "#0D9488",
  "#7C3AED",
];

function EmptyChart({ message = "No data available for selected filter." }) {
  return (
    <div className="flex h-64 items-center justify-center rounded-md border border-dashed border-slate-200 bg-slate-50/50 text-xs text-slate-500">
      {message}
    </div>
  );
}

export function RevenueVsExpenseChart({ data = [], currency = "INR", granularity = "monthly" }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Revenue vs. Expenses</h3>
          <p className="text-xs text-slate-500">
            Grouped {granularity} comparison highlighting profitable & loss periods
          </p>
        </div>
      </div>
      {data.length === 0 ? (
        <EmptyChart />
      ) : (
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748B" }} />
              <YAxis
                tick={{ fontSize: 11, fill: "#64748B" }}
                tickFormatter={(v) => formatCompactCurrency(v, currency)}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (!active || !payload?.length) return null;
                  const row = payload[0].payload;
                  return (
                    <div className="rounded-md border border-slate-200 bg-white p-3 text-xs shadow-sm">
                      <div className="mb-1.5 flex items-center justify-between gap-4 font-semibold text-slate-900">
                        <span>{label}</span>
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                            row.net_profit >= 0
                              ? "bg-emerald-50 text-emerald-700"
                              : "bg-red-50 text-red-700"
                          }`}
                        >
                          {row.net_profit >= 0 ? "Profitable" : "Loss"}
                        </span>
                      </div>
                      <div className="space-y-1 tabular-nums">
                        <div className="flex justify-between gap-4 text-emerald-700">
                          <span>Revenue:</span>
                          <span className="font-semibold">{formatCurrency(row.revenue, currency)}</span>
                        </div>
                        <div className="flex justify-between gap-4 text-amber-700">
                          <span>Expenses:</span>
                          <span className="font-semibold">{formatCurrency(row.expenses, currency)}</span>
                        </div>
                        <div className="flex justify-between gap-4 border-t border-slate-100 pt-1 text-slate-800">
                          <span>Net Profit:</span>
                          <span className="font-bold">{formatCurrency(row.net_profit, currency)}</span>
                        </div>
                      </div>
                    </div>
                  );
                }}
              />
              <Legend wrapperStyle={{ fontSize: "12px" }} />
              <Bar dataKey="revenue" name="Revenue" fill="#059669" radius={[3, 3, 0, 0]} />
              <Bar dataKey="expenses" name="Expenses" fill="#D97706" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export function ProfitTrendChart({ data = [], currency = "INR", granularity = "monthly" }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-slate-900">Profit Trend Analysis</h3>
        <p className="text-xs text-slate-500">
          Net profit trajectory ({granularity}) — red markers indicate operating losses
        </p>
      </div>
      {data.length === 0 ? (
        <EmptyChart />
      ) : (
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748B" }} />
              <YAxis
                tick={{ fontSize: 11, fill: "#64748B" }}
                tickFormatter={(v) => formatCompactCurrency(v, currency)}
              />
              <ReferenceLine y={0} stroke="#DC2626" strokeDasharray="4 4" />
              <Tooltip
                formatter={(val) => [formatCurrency(val, currency), "Net Profit"]}
                labelStyle={{ fontWeight: 600, color: "#0F172A" }}
                contentStyle={{ fontSize: "12px", borderRadius: "6px", borderColor: "#E2E8F0" }}
              />
              <Legend wrapperStyle={{ fontSize: "12px" }} />
              <Line
                type="monotone"
                dataKey="net_profit"
                name="Net Profit"
                stroke="#1E3A8A"
                strokeWidth={2.25}
                dot={(props) => {
                  const { cx, cy, payload } = props;
                  if (cx === undefined || cy === undefined) return null;
                  const fill = payload.net_profit >= 0 ? "#059669" : "#DC2626";
                  return <circle key={payload.period} cx={cx} cy={cy} r={4} fill={fill} stroke="#fff" strokeWidth={1.5} />;
                }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export function CategoryDonutChart({ title, subtitle, data = [], currency = "INR" }) {
  const nonZero = data.filter((d) => Number(d.amount) > 0);
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        <p className="text-xs text-slate-500">{subtitle}</p>
      </div>
      {nonZero.length === 0 ? (
        <EmptyChart />
      ) : (
        <div className="grid grid-cols-1 items-center gap-4 md:grid-cols-2">
          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={nonZero}
                  dataKey="amount"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  innerRadius={52}
                  outerRadius={84}
                  paddingAngle={2}
                >
                  {nonZero.map((entry, idx) => (
                    <Cell key={entry.category} fill={PALETTE[idx % PALETTE.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value, name) => [formatCurrency(value, currency), name]}
                  contentStyle={{ fontSize: "12px", borderRadius: "6px", borderColor: "#E2E8F0" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="max-h-60 space-y-2 overflow-y-auto pr-1">
            {nonZero.map((item, idx) => (
              <div key={item.category} className="flex items-center justify-between gap-2 text-xs">
                <div className="flex min-w-0 items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-sm"
                    style={{ backgroundColor: PALETTE[idx % PALETTE.length] }}
                  />
                  <span className="truncate font-medium text-slate-700">{item.category}</span>
                </div>
                <div className="shrink-0 text-right tabular-nums">
                  <span className="font-semibold text-slate-900">
                    {formatCurrency(item.amount, currency)}
                  </span>
                  <span className="ml-1.5 text-slate-500">({item.percentage.toFixed(1)}%)</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function CashFlowChart({ data = [], currency = "INR", granularity = "monthly" }) {
  const negCount = data.filter((d) => d.net_cash_flow < 0).length;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Cash Flow Analysis</h3>
          <p className="text-xs text-slate-500">
            Explicit cash-settled inflows vs. outflows ({granularity}) — excludes unsettled credit accruals
          </p>
        </div>
        {negCount > 0 && (
          <span className="rounded border border-red-200 bg-red-50 px-2 py-0.5 text-[11px] font-semibold text-red-700">
            {negCount} Negative Cash Flow Period(s)
          </span>
        )}
      </div>
      {data.length === 0 ? (
        <EmptyChart />
      ) : (
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748B" }} />
              <YAxis
                tick={{ fontSize: 11, fill: "#64748B" }}
                tickFormatter={(v) => formatCompactCurrency(v, currency)}
              />
              <ReferenceLine y={0} stroke="#DC2626" strokeDasharray="4 4" />
              <Tooltip
                formatter={(val, name) => [formatCurrency(val, currency), name]}
                contentStyle={{ fontSize: "12px", borderRadius: "6px", borderColor: "#E2E8F0" }}
              />
              <Legend wrapperStyle={{ fontSize: "12px" }} />
              <Bar dataKey="cash_inflow" name="Cash Inflow" fill="#059669" radius={[3, 3, 0, 0]} />
              <Bar dataKey="cash_outflow" name="Cash Outflow" fill="#EA580C" radius={[3, 3, 0, 0]} />
              <Line
                type="monotone"
                dataKey="net_cash_flow"
                name="Net Cash Flow"
                stroke="#0F172A"
                strokeWidth={2}
                dot={{ r: 3.5 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export function SalesPerformanceChart({ salesPerformance, currency = "INR" }) {
  const [granularity, setGranularity] = useState("monthly");
  const series = salesPerformance?.[granularity] || [];
  const highlight = salesPerformance?.highlights?.[granularity];

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Sales Performance</h3>
          <p className="text-xs text-slate-500">
            Granular sales velocity identifying peak & low-performing periods
          </p>
        </div>
        <div className="inline-flex rounded-md border border-slate-200 bg-slate-50 p-0.5">
          {["daily", "weekly", "monthly"].map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setGranularity(tab)}
              className={`rounded px-2.5 py-1 text-xs font-medium capitalize transition-colors ${
                granularity === tab
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {highlight && (
        <div className="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
          <div className="rounded border border-emerald-200 bg-emerald-50/70 px-3 py-1.5 text-xs">
            <span className="text-emerald-700 font-medium">Peak ({highlight.best.label}): </span>
            <span className="font-bold text-emerald-900 tabular-nums">
              {formatCurrency(highlight.best.sales, currency)}
            </span>
          </div>
          <div className="rounded border border-amber-200 bg-amber-50/70 px-3 py-1.5 text-xs">
            <span className="text-amber-700 font-medium">Lowest ({highlight.worst.label}): </span>
            <span className="font-bold text-amber-900 tabular-nums">
              {formatCurrency(highlight.worst.sales, currency)}
            </span>
          </div>
          <div className="rounded border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs">
            <span className="text-slate-600 font-medium">
              Avg / {{ daily: "Day", weekly: "Week", monthly: "Month" }[granularity]}:{" "}
            </span>
            <span className="font-bold text-slate-900 tabular-nums">
              {formatCurrency(highlight.average, currency)}
            </span>
          </div>
        </div>
      )}

      {series.length === 0 ? (
        <EmptyChart message="No sales transactions recorded in this date window." />
      ) : (
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={series} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748B" }} />
              <YAxis
                tick={{ fontSize: 11, fill: "#64748B" }}
                tickFormatter={(v) => formatCompactCurrency(v, currency)}
              />
              <Tooltip
                formatter={(val, name) => [
                  name === "Sales" ? formatCurrency(val, currency) : val,
                  name,
                ]}
                contentStyle={{ fontSize: "12px", borderRadius: "6px", borderColor: "#E2E8F0" }}
              />
              <Bar dataKey="sales" name="Sales" fill="#1E3A8A" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
