const tokenKey = "courselab_token";

export function getToken() {
  return localStorage.getItem(tokenKey);
}

export function setToken(token) {
  if (token) localStorage.setItem(tokenKey, token);
  else localStorage.removeItem(tokenKey);
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (getToken()) headers.set("Authorization", `Bearer ${getToken()}`);
  const response = await fetch(`${import.meta.env.VITE_API_URL || ""}${path}`, { ...options, headers });
  if (response.status === 204) return null;
  const payload = response.headers.get("content-type")?.includes("application/json")
    ? await response.json()
    : await response.text();
  if (!response.ok) {
    if (response.status === 401) setToken("");
    throw new Error(errorMessage(payload));
  }
  return payload;
}

function errorMessage(payload) {
  if (Array.isArray(payload?.detail)) {
    return payload.detail
      .map((item) => {
        const field = item.loc?.filter((part) => part !== "body").join(".");
        return `${field ? `${field}：` : ""}${item.msg || "格式不正确"}`;
      })
      .join("；");
  }
  if (typeof payload?.detail === "string") return payload.detail;
  return typeof payload === "string" ? payload : "请求失败，请稍后重试";
}

export const authApi = {
  register: (payload) => request("/api/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload) => request("/api/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request("/api/auth/me"),
};

export const planApi = {
  list: () => request("/api/plans"),
  create: (payload) => request("/api/plans", { method: "POST", body: JSON.stringify(payload) }),
  get: (id) => request(`/api/plans/${id}`),
  retry: (id) => request(`/api/plans/${id}/retry`, { method: "POST" }),
  stop: (id) => request(`/api/plans/${id}/stop`, { method: "POST" }),
  remove: (id) => request(`/api/plans/${id}`, { method: "DELETE" }),
};

export const credentialApi = {
  get: () => request("/api/settings/credentials"),
  save: (payload) => request("/api/settings/credentials", { method: "PUT", body: JSON.stringify(payload) }),
};

export async function downloadReport(planId, filename) {
  const response = await fetch(`${import.meta.env.VITE_API_URL || ""}/api/plans/${planId}/report`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!response.ok) throw new Error("报告尚不可下载");
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function demoApi() {
  return request("/api/demo");
}

