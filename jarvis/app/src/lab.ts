// The Lab switch (Madhav, 2026-10-04): off = the app shows findings and books; on = the research views come back
// (the Lab page with the evidence pipeline, scoreboard and repair shop; the activity feed and engine rows on Home).
// Kept on the phone; every screen that reads it updates at once.
import { useSyncExternalStore } from "react";
import * as SecureStore from "expo-secure-store";

let on = false;
const subs = new Set<() => void>();
SecureStore.getItemAsync("lab_mode").then((v) => { on = v === "1"; subs.forEach((f) => f()); }).catch(() => {});

export function setLab(v: boolean) {
  on = v;
  subs.forEach((f) => f());
  SecureStore.setItemAsync("lab_mode", v ? "1" : "0").catch(() => {});
}

export function useLab(): [boolean, (v: boolean) => void] {
  const v = useSyncExternalStore((f) => { subs.add(f); return () => { subs.delete(f); }; }, () => on);
  return [v, setLab];
}
