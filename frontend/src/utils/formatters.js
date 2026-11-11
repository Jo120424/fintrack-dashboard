const CURRENCY_LOCALES = {
  INR: { locale: "en-IN", symbol: "₹" },
  USD: { locale: "en-US", symbol: "$" },
  EUR: { locale: "de-DE", symbol: "€" },
  GBP: { locale: "en-GB", symbol: "£" },
};

export function getCurrencySymbol(currency = "INR") {
  return (CURRENCY_LOCALES[currency] || CURRENCY_LOCALES.INR).symbol;
}

export function formatCurrency(amount, currency = "INR", decimals = 0) {
  const num = Number(amount || 0);
  const cfg = CURRENCY_LOCALES[currency] || CURRENCY_LOCALES.INR;
  const neg = num < 0;
  const formatted = Math.abs(num).toLocaleString(cfg.locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return `${neg ? "-" : ""}${cfg.symbol}${formatted}`;
}

export function formatCompactCurrency(amount, currency = "INR") {
  const num = Number(amount || 0);
  const sym = getCurrencySymbol(currency);
  const neg = num < 0 ? "-" : "";
  const abs = Math.abs(num);

  if (currency === "INR") {
    if (abs >= 10000000) return `${neg}${sym}${(abs / 10000000).toFixed(2)}Cr`;
    if (abs >= 100000) return `${neg}${sym}${(abs / 100000).toFixed(1)}L`;
    if (abs >= 1000) return `${neg}${sym}${(abs / 1000).toFixed(0)}K`;
    return `${neg}${sym}${Math.round(abs)}`;
  }

  if (abs >= 1000000) return `${neg}${sym}${(abs / 1000000).toFixed(1)}M`;
  if (abs >= 1000) return `${neg}${sym}${(abs / 1000).toFixed(0)}K`;
  return `${neg}${sym}${Math.round(abs)}`;
}

export function formatPercent(value, decimals = 1, showPlus = false) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  const num = Number(value);
  const prefix = showPlus && num > 0 ? "+" : "";
  return `${prefix}${num.toFixed(decimals)}%`;
}

export function formatNumber(value) {
  return Number(value || 0).toLocaleString("en-IN");
}

export function formatShortDate(isoDate) {
  if (!isoDate) return "—";
  const parts = isoDate.split("-");
  if (parts.length !== 3) return isoDate;
  const dt = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
  return dt.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}
