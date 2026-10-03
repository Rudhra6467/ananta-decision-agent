// Talks to the Jarvis service (owner only). The token and server address live in the phone's secure storage.
import * as SecureStore from "expo-secure-store";
import Constants from "expo-constants";

const DEFAULT_SERVER: string = (Constants.expoConfig?.extra as any)?.defaultServer ?? "http://192.168.2.68:8100";

export async function server(): Promise<string> {
  const saved = await SecureStore.getItemAsync("jarvis_server");
  // Temporary public links (*.trycloudflare.com) change when they restart: a saved old one is replaced by the app's current one.
  if (saved && /trycloudflare\.com/.test(saved)) return DEFAULT_SERVER;        // an old temporary link: use the current one (or the fixed address)
  return saved || DEFAULT_SERVER;
}
export async function setServer(url: string) {
  await SecureStore.setItemAsync("jarvis_server", url.replace(/\/+$/, ""));
}
export async function token(): Promise<string | null> {
  return SecureStore.getItemAsync("jarvis_token");
}
export async function logout() {
  await SecureStore.deleteItemAsync("jarvis_token");
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

// Every call gives up after timeoutMs (default 60 s), so a dropped connection can never leave a screen waiting forever.
export async function api<T = any>(path: string, body?: object, timeoutMs = 60000): Promise<T> {
  const [base, tok] = [await server(), await token()];
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  let r: Response;
  try {
    r = await fetch(base + path, {
      method: body ? "POST" : "GET",
      headers: { "Content-Type": "application/json", ...(tok ? { Authorization: `Bearer ${tok}` } : {}) },
      body: body ? JSON.stringify(body) : undefined,
      signal: ctl.signal,
    });
  } catch (e: any) {
    clearTimeout(timer);
    if (e?.name === "AbortError") throw new ApiError(0, "No answer from Jarvis in time. Check the connection and try again.");
    throw new ApiError(0, "Can't reach Jarvis right now. Check the connection and try again.");
  }
  clearTimeout(timer);
  const txt = await r.text();
  let data: any = {};
  try { data = txt ? JSON.parse(txt) : {}; } catch { data = { detail: r.ok ? "Jarvis sent an unreadable reply." : `Jarvis is not reachable right now (HTTP ${r.status}).` }; }
  if (r.ok && data?.detail && !txt.trim().startsWith("{")) throw new ApiError(r.status, data.detail);
  if (!r.ok) throw new ApiError(r.status, data?.detail || `HTTP ${r.status}`);
  return data as T;
}

export async function login(email: string, password: string) {
  const r = await api<{ token: string }>("/auth/login", { email, password });
  await SecureStore.setItemAsync("jarvis_token", r.token);
}
