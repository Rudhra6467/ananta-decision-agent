import { useCallback, useEffect, useState } from "react";
import { router } from "expo-router";
import { api, ApiError, logout } from "./api";

export function useData<T = any>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api<T>(path));
      setErr(null);
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 401) {
        await logout();
        router.replace("/login");
        return;
      }
      setErr(e?.message ?? String(e));
    } finally {
      setLoading(false);
    }
  }, [path]);
  useEffect(() => { load(); }, [load]);
  return { data, err, loading, reload: load };
}
