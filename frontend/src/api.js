const KEY = "set_token";
export const getToken = () => localStorage.getItem(KEY);
export const setToken = (t) => (t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY));

export async function api(path, { method = "GET", body, form, blob } = {}) {
  const headers = {};
  if (getToken()) headers.Authorization = `Bearer ${getToken()}`;
  if (body) headers["Content-Type"] = "application/json";
  const res = await fetch(`/api${path}`, { method, headers, body: form || (body ? JSON.stringify(body) : undefined) });
  if (res.status === 401 && getToken()) { setToken(null); location.reload(); }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : j.detail?.map((d) => `${d.loc.slice(-1)}: ${d.msg}`).join("; ") || msg;
    } catch {}
    throw new Error(msg);
  }
  if (res.status === 204) return null;
  return blob ? res.blob() : res.json();
}

export async function download(path, filename) {
  const b = await api(path, { blob: true });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(b);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

export const money = (n, cur = "BDT") => `${Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 })} ${cur}`;
export const thisMonth = () => new Date().toISOString().slice(0, 7);
