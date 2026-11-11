import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "../api/client";

export const DATE_FILTER_OPTIONS = [
  { value: "today", label: "Today" },
  { value: "this_week", label: "This Week" },
  { value: "this_month", label: "This Month" },
  { value: "last_month", label: "Last Month" },
  { value: "last_3_months", label: "Last 3 Months" },
  { value: "last_6_months", label: "Last 6 Months" },
  { value: "this_year", label: "This Year" },
  { value: "all", label: "All 12M+" },
  { value: "custom", label: "Custom Range" },
];

const FilterContext = createContext(null);

export function FilterProvider({ children }) {
  const [period, setPeriod] = useState("this_year");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [appliedCustom, setAppliedCustom] = useState({ start_date: "", end_date: "" });
  const [settings, setSettings] = useState({
    business_name: "SMART MART RETAIL STORE",
    currency: "INR",
    is_demo_data: true,
  });
  const [refreshVersion, setRefreshVersion] = useState(0);

  const loadSettings = useCallback(async () => {
    try {
      const res = await api.getSettings();
      if (res?.settings) {
        setSettings(res.settings);
      }
    } catch {
      // Initial fallback remains active until backend responds
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings, refreshVersion]);

  const triggerRefresh = useCallback(() => {
    setRefreshVersion((v) => v + 1);
  }, []);

  const applyCustomRange = useCallback((start, end) => {
    setCustomStart(start);
    setCustomEnd(end);
    setAppliedCustom({ start_date: start, end_date: end });
    setPeriod("custom");
  }, []);

  const filterParams =
    period === "custom"
      ? {
          period: "custom",
          start_date: appliedCustom.start_date,
          end_date: appliedCustom.end_date,
        }
      : { period };

  return (
    <FilterContext.Provider
      value={{
        period,
        setPeriod,
        customStart,
        setCustomStart,
        customEnd,
        setCustomEnd,
        appliedCustom,
        applyCustomRange,
        filterParams,
        settings,
        setSettings,
        refreshVersion,
        triggerRefresh,
      }}
    >
      {children}
    </FilterContext.Provider>
  );
}

export function useGlobalFilter() {
  const ctx = useContext(FilterContext);
  if (!ctx) {
    throw new Error("useGlobalFilter must be used within FilterProvider");
  }
  return ctx;
}
