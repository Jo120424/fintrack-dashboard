import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  BarChart3,
  Calendar,
  FileSpreadsheet,
  LayoutDashboard,
  Lightbulb,
  Menu,
  RefreshCw,
  ReceiptText,
  Settings,
  X,
} from "lucide-react";
import { DATE_FILTER_OPTIONS, useGlobalFilter } from "../context/FilterContext";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/transactions", label: "Transactions", icon: ReceiptText },
  { to: "/analytics", label: "Financial Analytics", icon: BarChart3 },
  { to: "/insights", label: "Business Insights", icon: Lightbulb },
  { to: "/reports", label: "Reports", icon: FileSpreadsheet },
  { to: "/settings", label: "Settings", icon: Settings },
];

const PAGE_TITLES = {
  "/": {
    title: "Executive Financial Overview",
    subtitle: "Real-time revenue, expense, profitability, and cash liquidity metrics",
  },
  "/transactions": {
    title: "Financial Data Management",
    subtitle: "Ledger entries, multi-criteria filtering, and validated CSV batch imports",
  },
  "/analytics": {
    title: "Business Performance & Forecasting",
    subtitle: "Descriptive, diagnostic, comparative ratios, and 3-month revenue projections",
  },
  "/insights": {
    title: "Intelligent Business Insights",
    subtitle: "Automated findings derived directly from historical and current database records",
  },
  "/reports": {
    title: "Financial Reports & Exports",
    subtitle: "Generate monthly, quarterly, and annual statements in CSV or PDF format",
  },
  "/settings": {
    title: "Workspace & Dataset Settings",
    subtitle: "Manage business profile, reporting currency, and demonstration dataset state",
  },
};

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const {
    period,
    setPeriod,
    customStart,
    setCustomStart,
    customEnd,
    setCustomEnd,
    applyCustomRange,
    settings,
    triggerRefresh,
  } = useGlobalFilter();

  const [draftStart, setDraftStart] = useState(customStart || "2026-01-01");
  const [draftEnd, setDraftEnd] = useState(customEnd || new Date().toISOString().slice(0, 10));
  const [dateError, setDateError] = useState("");

  const pageMeta = PAGE_TITLES[location.pathname] || PAGE_TITLES["/"];
  const hideGlobalDateBar = location.pathname === "/reports" || location.pathname === "/settings";

  const handlePeriodChange = (val) => {
    setDateError("");
    if (val === "custom") {
      setPeriod("custom");
      if (draftStart && draftEnd && draftStart <= draftEnd) {
        applyCustomRange(draftStart, draftEnd);
      }
    } else {
      setPeriod(val);
    }
  };

  const handleApplyCustom = (e) => {
    e.preventDefault();
    if (!draftStart || !draftEnd) {
      setDateError("Select both start and end dates.");
      return;
    }
    if (draftStart > draftEnd) {
      setDateError("Start date cannot be after end date.");
      return;
    }
    setDateError("");
    applyCustomRange(draftStart, draftEnd);
  };

  const SidebarContent = (
    <div className="flex h-full flex-col bg-slate-900 text-slate-100">
      <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-emerald-600 text-sm font-bold text-white">
            FT
          </div>
          <div>
            <div className="text-sm font-bold tracking-wide text-white">FINTRACK</div>
            <div className="text-[11px] text-slate-400">Small Business BI</div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setSidebarOpen(false)}
          className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white lg:hidden"
          aria-label="Close navigation menu"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            onClick={() => setSidebarOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-blue-900/70 text-white border-l-2 border-emerald-400"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              }`
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-800 p-4 text-xs">
        <div className="rounded-md bg-slate-800/80 p-3">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Active Business Entity
          </div>
          <div className="mt-1 font-semibold text-white leading-snug">
            {settings.business_name}
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px] text-slate-300">
            <span>Currency: {settings.currency}</span>
            {settings.is_demo_data ? (
              <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-amber-300">
                DEMO DATA
              </span>
            ) : (
              <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-300">
                CUSTOM DATA
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 lg:flex">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-30 lg:block lg:w-64">
        {SidebarContent}
      </aside>

      {/* Mobile Drawer */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <div
            className="fixed inset-0 bg-slate-900/50"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="relative z-50 w-64 max-w-xs">{SidebarContent}</aside>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white">
          <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3.5 sm:px-6">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setSidebarOpen(true)}
                className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-100 lg:hidden"
                aria-label="Open navigation menu"
              >
                <Menu className="h-5 w-5" />
              </button>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-base font-semibold text-slate-900 sm:text-lg">
                    {pageMeta.title}
                  </h1>
                  {settings.is_demo_data && (
                    <span className="inline-flex items-center rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-800">
                      DEMONSTRATION DATA
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500">{pageMeta.subtitle}</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="hidden rounded border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700 sm:inline-block">
                {settings.business_name}
              </span>
              <button
                type="button"
                onClick={triggerRefresh}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                title="Refresh metrics from database"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Refresh</span>
              </button>
            </div>
          </div>

          {!hideGlobalDateBar && (
            <div className="border-t border-slate-100 bg-slate-50/70 px-4 py-2.5 sm:px-6">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="mr-1 inline-flex items-center gap-1 text-xs font-medium text-slate-500">
                    <Calendar className="h-3.5 w-3.5" />
                    Period:
                  </span>
                  {DATE_FILTER_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => handlePeriodChange(opt.value)}
                      className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                        period === opt.value
                          ? "bg-slate-900 text-white"
                          : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-100"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>

                {period === "custom" && (
                  <form onSubmit={handleApplyCustom} className="flex flex-wrap items-center gap-2">
                    <input
                      type="date"
                      value={draftStart}
                      onChange={(e) => setDraftStart(e.target.value)}
                      className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800"
                    />
                    <span className="text-xs text-slate-500">to</span>
                    <input
                      type="date"
                      value={draftEnd}
                      onChange={(e) => setDraftEnd(e.target.value)}
                      className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800"
                    />
                    <button
                      type="submit"
                      className="rounded-md bg-blue-900 px-3 py-1 text-xs font-medium text-white hover:bg-blue-800"
                    >
                      Apply
                    </button>
                    {dateError && <span className="text-xs font-medium text-red-600">{dateError}</span>}
                  </form>
                )}
              </div>
            </div>
          )}
        </header>

        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">{children}</main>
      </div>
    </div>
  );
}
