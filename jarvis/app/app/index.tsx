// The root: the chosen market's home, or the Market screen when the owner has not chosen yet (22 Oct). Guests and visitors
// go straight to the crypto home as before (their practice accounts are crypto); the choice only ever applies to the owner.
import { useEffect, useState } from "react";
import { Redirect } from "expo-router";
import { homeOf, loadMarket } from "../src/market";
import { loadMe } from "../src/visitor";
import { loadLook, newHome } from "../src/look";
import { helloSeen, ownerNeedsFirstRun } from "../src/onboard";

export default function Index() {
  const [to, setTo] = useState<string | null>(null);
  useEffect(() => {
    (async () => {
      try {
        const me = await loadMe();
        if (me?.guest) { setTo(me.onboard && me.onboard !== "done" && !(await helloSeen()) ? "/hello" : "/(tabs)/today"); return; }   // 1 Nov: an invited person says hello first
        const m = await loadMarket();
        const look = await loadLook();                     // 31 Oct: the redesign, when this device chose it (both markets from 1 Nov)
        if (look === "new" && (await ownerNeedsFirstRun())) { setTo("/onboard"); return; }          // 1 Nov: the owner's first run, once
        setTo(m && look === "new" ? newHome : m ? homeOf(m) : "/market");
      } catch { setTo("/(tabs)/today"); }
    })();
  }, []);
  return to ? <Redirect href={to as any} /> : null;
}
