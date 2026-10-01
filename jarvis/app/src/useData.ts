import { useCallback, useEffect, useRef, useState } from "react";
import { AppState } from "react-native";
import { router } from "expo-router";
import { api, ApiError, logout } from "./api";

// Loads a route, refreshes it quietly every minute while the app is open, and on pull-down.
export function useData<T = any>(path: string | null, refreshMs = 60000) {
  const [data, setData] = useState<T | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const busy = useRef(false);
  const load = useCallback(async (quiet = false) => {
    if (!path || busy.current) return;
    busy.current = true;
    if (!quiet) setLoading(true);
    try {
      setData(await api<T>(path));
      setErr(null);
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 401) {
        await logout();
        router.replace("/login");
        return;
      }
      if (!quiet) setErr(e?.message ?? String(e));
    } finally {
      busy.current = false;
      setLoading(false);
    }
  }, [path]);
  useEffect(() => {
    load();
    if (!refreshMs) return;
    const id = setInterval(() => { if (AppState.currentState === "active") load(true); }, refreshMs);
    const sub = AppState.addEventListener("change", (st) => { if (st === "active") load(true); });
    return () => { clearInterval(id); sub.remove(); };
  }, [load, refreshMs]);
  return { data, err, loading, reload: () => load(false) };
}
