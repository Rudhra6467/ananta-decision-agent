// "Reach me when the app is closed" (plan 1.7): notifications on this device (the website, and on iPhone the Home Screen app),
// and optional email when the service has email set up.
import { useState } from "react";
import { Platform, Switch, Text, View } from "react-native";
import { api } from "./api";
import { showToast } from "./blocks";
import { C } from "./theme";
import { Btn, Card, Divider, T } from "./ui";
import { useData } from "./useData";

const toBytes = (b64: string) => {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
};

const standalone = () => {
  try { return window.matchMedia("(display-mode: standalone)").matches || (navigator as any).standalone === true; } catch { return false; }
};

export function NotificationsCard() {
  const { data: d, reload } = useData("/v3/push/web", 0);
  const [busy, setBusy] = useState(false);
  const web = Platform.OS === "web" && typeof window !== "undefined";
  const ios = web && /iPhone|iPad|iPod/.test(navigator.userAgent);
  const supported = web && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
  const on = web && supported && (window as any).Notification?.permission === "granted" && (d?.devices ?? 0) > 0;

  const turnOn = async () => {
    if (!supported || !d?.key) return;
    setBusy(true);
    try {
      const perm = await Notification.requestPermission();
      if (perm !== "granted") { showToast("Notifications were not allowed"); return; }
      const reg = await navigator.serviceWorker.register("/sw.js");
      await navigator.serviceWorker.ready;
      const sub = (await reg.pushManager.getSubscription()) ?? (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: toBytes(d.key) }));
      await api("/v3/push/web/subscribe", { sub: sub.toJSON(), device: navigator.userAgent.slice(0, 80) });
      showToast("Notifications on ✓");
      reload();
    } catch (e: any) {
      showToast(e?.message ?? "Could not turn notifications on");
    } finally {
      setBusy(false);
    }
  };
  const email = async (v: boolean) => {
    try { await api("/v3/push/web/email", { on: v }); reload(); } catch (e: any) { showToast(e?.message ?? "Not changed"); }
  };

  return (
    <Card title="Reach me when the app is closed" sub={d ? `${d.devices} device${d.devices === 1 ? "" : "s"} with notifications on` : undefined}>
      {Platform.OS !== "web" ? <T dim>On the phone app, notifications arrive once the App Store build is installed.</T>
        : ios && !standalone() ? <T dim>On iPhone, add Ananta to your Home Screen first (Share, then “Add to Home Screen”), open it from there, then turn notifications on here.</T>
        : !supported ? <T dim>This browser can't show notifications.</T>
        : on ? <T>Notifications are on for this device. A fired watch, a request waiting for your yes, or a warning about your trade shows up here.</T>
        : <Btn label={busy ? "Turning on…" : "Turn on notifications"} onPress={turnOn} />}
      <Divider />
      <View style={{ flexDirection: "row", alignItems: "center", gap: 12, paddingTop: 6 }}>
        <View style={{ flex: 1 }}>
          <Text style={{ color: d?.email_ready ? C.text : C.faint, fontSize: 15, fontWeight: "600" }}>Email me as well</Text>
          <T small>{d?.email_ready ? "The same notes by email, to the address you signed in with." : "Email is not set up on the service yet."}</T>
        </View>
        <Switch value={!!d?.email_alerts} disabled={!d?.email_ready} onValueChange={email} trackColor={{ true: C.accent, false: C.line }} />
      </View>
    </Card>
  );
}
