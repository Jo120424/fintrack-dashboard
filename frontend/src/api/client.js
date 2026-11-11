const API_BASE = "/api";

function buildQuery(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      qs.set(key, String(value));
    }
  });
  const str = qs.toString();
  return str ? `?${str}` : "";
}

async function requestJson(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
    ...options,
  });

  const text = await res.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { error: text || "Unexpected non-JSON server response" };
  }

  if (!res.ok) {
    const err = new Error(data.error || `Request failed (${res.status})`);
    err.status = res.status;
    err.payload = data;
    throw err;
  }
  return data;
}

export const api = {
  getDashboard: (filter) => requestJson(`/dashboard${buildQuery(filter)}`),
  getTransactions: (params) => requestJson(`/transactions${buildQuery(params)}`),
  createTransaction: (payload) =>
    requestJson("/transactions", { method: "POST", body: JSON.stringify(payload) }),
  updateTransaction: (id, payload) =>
    requestJson(`/transactions/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteTransaction: (id) => requestJson(`/transactions/${id}`, { method: "DELETE" }),

  uploadCsvFile: (file, action = "preview", replaceExisting = false) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("action", action);
    fd.append("replace_existing", String(replaceExisting));
    return requestJson("/upload", { method: "POST", body: fd });
  },

  getAnalytics: (filter) => requestJson(`/analytics${buildQuery(filter)}`),
  getInsights: (filter) => requestJson(`/insights${buildQuery(filter)}`),
  getReports: (params) => requestJson(`/reports${buildQuery(params)}`),

  getSettings: () => requestJson("/settings"),
  updateSettings: (payload) =>
    requestJson("/settings", { method: "PUT", body: JSON.stringify(payload) }),
  resetDemoData: () => requestJson("/settings/reset-demo", { method: "POST" }),
  clearAllData: () => requestJson("/settings/clear-data", { method: "POST" }),

  getCsvTemplateUrl: () => `${API_BASE}/upload/template`,
  getCsvExportUrl: (params) => `${API_BASE}/export/csv${buildQuery(params)}`,
  getPdfExportUrl: (params) => `${API_BASE}/export/pdf${buildQuery(params)}`,
};
