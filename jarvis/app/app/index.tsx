// The root: the chosen market's home, or the Market screen when the owner has not chosen yet (22 Oct). Guests and visitors
// go straight to the crypto home as before (their practice accounts are crypto); the choice only ever applies to the owner.
import { useEffect, useState } from "react";
import { Redirect } from "expo-router";
import { homeOf, loadMarket } from "../src/market";
import { loadMe } from "../src/visitor";

export default function Index() {
  const [to, setTo] = useState<string | null>(null);
  useEffect(() => {
    (async () => {
      try {
        const me = await loadMe();
        if (me?.guest) { setTo("/(tabs)/today"); return; }
        const m = await loadMarket();
        setTo(m ? homeOf(m) : "/market");
      } catch { setTo("/(tabs)/today"); }
    })();
  }, []);
  return to ? <Redirect href={to as any} /> : null;
}
