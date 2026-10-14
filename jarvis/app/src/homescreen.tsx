// Website only (plan 2.5): a one-time hint to add Ananta to the Home Screen, where it opens full screen like an app.
// iPhone: Share, then "Add to Home Screen". Android: an Install button when Chrome offers it, else a Full screen button.
import { useEffect, useState } from "react";
import { Platform, Pressable, Text, View } from "react-native";
import { C } from "./theme";

const KEY = "ananta_homescreen_hint";
let installEvent: any = null;
if (Platform.OS === "web" && typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (e: any) => { e.preventDefault(); installEvent = e; });
}

const standalone = () => {
  try {
    return window.matchMedia("(display-mode: standalone)").matches || window.matchMedia("(display-mode: fullscreen)").matches
      || (navigator as any).standalone === true;
  } catch { return false; }
};
const seen = () => { try { return localStorage.getItem(KEY) === "1"; } catch { return true; } };
const markSeen = () => { try { localStorage.setItem(KEY, "1"); } catch {} };

export function HomeScreenHint() {
  const [show, setShow] = useState(false);
  const [canInstall, setCanInstall] = useState(false);
  useEffect(() => {
    if (Platform.OS !== "web" || standalone() || seen()) return;
    const t = setTimeout(() => { setShow(true); setCanInstall(!!installEvent); }, 4000);   // after the first screen has settled
    return () => clearTimeout(t);
  }, []);
  if (!show) return null;
  const ios = /iPhone|iPad|iPod/.test(navigator.userAgent);
  const close = () => { markSeen(); setShow(false); };
  const install = async () => { try { await installEvent?.prompt(); } catch {} close(); };
  const full = () => { try { document.documentElement.requestFullscreen?.(); } catch {} close(); };
  return (
    <View pointerEvents="box-none" style={{ position: "absolute", left: 12, right: 12, bottom: 84 }}>
      <View style={{ backgroundColor: C.ink, borderRadius: 16, padding: 14, gap: 10, shadowColor: "#000", shadowOpacity: 0.25, shadowRadius: 10 }}>
        <Text style={{ color: C.onInk, fontSize: 15, fontWeight: "700" }}>Use Ananta full screen</Text>
        <Text style={{ color: C.onInk, fontSize: 13, lineHeight: 19, opacity: 0.85 }}>
          {ios ? "Tap the Share button (the square with the arrow), then “Add to Home Screen”. Ananta then opens like an app, without the browser bars."
            : canInstall ? "Install Ananta on your Home Screen and it opens like an app, without the browser bars."
            : "Add Ananta to your Home Screen from the browser menu, or go full screen now."}
        </Text>
        <View style={{ flexDirection: "row", gap: 10 }}>
          {!ios ? (
            <Pressable onPress={canInstall ? install : full} style={{ flex: 1, backgroundColor: C.accent, borderRadius: 10, padding: 9, alignItems: "center" }}>
              <Text style={{ color: C.onInk, fontWeight: "700" }}>{canInstall ? "Install" : "Full screen"}</Text>
            </Pressable>
          ) : null}
          <Pressable onPress={close} style={{ flex: 1, backgroundColor: C.inkBtn, borderRadius: 10, padding: 9, alignItems: "center" }}>
            <Text style={{ color: C.onInk, fontWeight: "700" }}>{ios ? "Got it" : "Not now"}</Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}
