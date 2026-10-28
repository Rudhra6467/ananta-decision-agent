// Talks to the Ananta service (owner only). The token and server address live in the phone's secure storage.
import * as SecureStore from "expo-secure-store";
import Constants from "expo-constants";
import { getMarket, loadMarket } from "./market";

const DEFAULT_SERVER: string = (Constants.expoConfig?.extra as any)?.defaultServer ?? "https://api.livetrading247.com";

export async function server(): Promise<string> {
  const saved = await SecureStore.getItemAsync("jarvis_server");
  // Old addresses give way to the fixed one (https://api.livetrading247.com): temporary *.trycloudflare.com links change on
  // every restart, and the laptop's home-wifi address (192.168.x.x) only works at home.
  if (saved && /trycloudflare\.com|192\.168\./.test(saved)) return DEFAULT_SERVER;
  return saved || DEFAULT_SERVER;
}
export async function setServer(url: string) {
  await SecureStore.setItemAsync("jarvis_server", url.replace(/\/+$/, ""));
}
export async function token(): Promise<string | null> {
  return SecureStore.getItemAsync("jarvis_token");
}
export async function logout() {
  try { await api("/v3/onboard/demo/clear", {}, 5000); } catch { /* signed out anyway */ }   // a visitor's DEMO trade ends at the first sign-out
  try { await api("/auth/logout", {}, 5000); } catch { /* the server session ends by itself after 3 idle hours */ }
  await SecureStore.deleteItemAsync("jarvis_token");
}

// Oct 12: a visitor whose 3 practice days are over gets this from sign-in instead of a token; the feedback screen reads it.
export type ExpiredForm = { expired: true; name: string; answered: boolean; form_token: string | null; questions: any[]; message: string };
let expiredForm: ExpiredForm | null = null;
export const getExpiredForm = () => expiredForm;

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

// Every call gives up after timeoutMs (default 60 s), so a dropped connection can never leave a screen waiting forever.
// quiet = a background refresh the person did not ask for: it does not keep the sign-in alive (3 hours without use signs out).
// One app, two backends (23 Oct): with the Indian market loaded, the screens' own routes (/v3/..., /history) go to /india on the same
// server, where the India service answers the same contract with Indian data. Account-level routes (sign-in, who I am, practice,
// onboarding, spend, settings, push) always stay on the sign-in service: one login, one account.
const SHARED = ["/auth/", "/v3/me", "/v3/practice", "/v3/onboard", "/v3/spend", "/v3/settings", "/v3/push", "/v3/feedback", "/v3/people", "/v3/join", "/v3/flags", "/v3/waiting"];
export function routeFor(path: string): string {
  if (getMarket() !== "india") return path;
  if (SHARED.some((s) => path === s || path.startsWith(s))) return path;
  return (path.startsWith("/v3/") || path.startsWith("/history")) ? "/india" + path : path;
}

export async function api<T = any>(path: string, body?: object, timeoutMs = 60000, quiet = false): Promise<T> {
  await loadMarket();                                   // the market choice is read once from this device before any route is picked
  const [base, tok] = [await server(), await token()];
  path = routeFor(path);
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  let r: Response;
  try {
    r = await fetch(base + path, {
      method: body ? "POST" : "GET",
      headers: { "Content-Type": "application/json", ...(tok ? { Authorization: `Bearer ${tok}` } : {}), ...(quiet ? { "X-Ananta-Quiet": "1" } : {}) },
      body: body ? JSON.stringify(body) : undefined,
      signal: ctl.signal,
    });
  } catch (e: any) {
    clearTimeout(timer);
    if (e?.name === "AbortError") throw new ApiError(0, "No answer from Ananta in time. Check the connection and try again.");
    throw new ApiError(0, "Can't reach Ananta right now. Check the connection and try again.");
  }
  clearTimeout(timer);
  const txt = await r.text();
  let data: any = {};
  try { data = txt ? JSON.parse(txt) : {}; } catch { data = { detail: r.ok ? "Ananta sent an unreadable reply." : `Ananta is not reachable right now (HTTP ${r.status}).` }; }
  if (r.ok && data?.detail && !txt.trim().startsWith("{")) throw new ApiError(r.status, data.detail);
  if (!r.ok) throw new ApiError(r.status, data?.detail || `HTTP ${r.status}`);
  return data as T;
}

// Returns "expired" when a visitor's practice days are over (the feedback form follows), else "ok".
export async function login(email: string, password: string): Promise<"ok" | "expired"> {
  const r = await api<any>("/auth/login", { email, password });
  if (r?.expired) { expiredForm = r as ExpiredForm; await SecureStore.deleteItemAsync("jarvis_token"); return "expired"; }
  expiredForm = null;
  await SecureStore.setItemAsync("jarvis_token", r.token);
  return "ok";
}
