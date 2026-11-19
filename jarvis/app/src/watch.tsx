// Markets' search and watchlists (Madhav, 19 Nov 2026: "The search bar in markets is not responding. How to make it fully functional. Like how
// we can view a stock in zerodha or trading view or money control" and "we will add one more option here watchlist ... We can even rename the
// watchlist"). The search filters the nightly list of NSE stocks as he types and opens a stock's page; the lists live with the India service
// (POST /v3/watch, jarvis/india/watch.py). Nothing here trades.
import { useMemo, useState } from "react";
import { Platform, Pressable, Text, TextInput, View } from "react-native";
import { C } from "./theme";
import { api } from "./api";
import { useData } from "./useData";
import { showToast } from "./visitor";
import { tap } from "./haptics";
import { Icon, T, card, go, refreshPlaces } from "./place";

type Stock = { s: string; n: string };

function match(rows: Stock[], q: string): Stock[] {
  const u = q.trim().toUpperCase();
  if (!u) return [];
  const exact = rows.filter((r) => r.s === u);
  const sym = rows.filter((r) => r.s !== u && r.s.startsWith(u));
  const name = rows.filter((r) => !r.s.startsWith(u) && r.n.toUpperCase().includes(u));
  return [...exact, ...sym, ...name].slice(0, 8);
}

export function useStockList() {
  return useData<any>("/v3/stocklist", 3600_000);
}

export function StockSearch({ s, onPick, autoFocus }: { s?: any; onPick?: (sym: string) => void; autoFocus?: boolean }) {
  const [q, setQ] = useState("");
  const list = useStockList();
  const rows: Stock[] = list.data?.rows || [];
  const hits = useMemo(() => match(rows, q), [rows, q]);
  const open = (sym: string) => {
    tap();
    setQ("");
    if (onPick) onPick(sym);
    else go({ place: `stock:${sym}` });
  };
  const submit = () => { const h = hits[0]; if (h) open(h.s); else if (q.trim()) showToast(`No NSE stock matches "${q.trim()}".`, 2600); };
  return (
    <View style={{ gap: 6, zIndex: 5 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 10, height: 48, paddingHorizontal: 14, borderRadius: 16, backgroundColor: C.card, borderWidth: 1, borderColor: C.line }}>
        <Icon name="search" size={20} />
        <TextInput value={q} onChangeText={setQ} onSubmitEditing={submit} placeholder={s?.hint || "Search a stock or company"} placeholderTextColor={C.dim}
          autoCorrect={false} autoCapitalize="none" autoFocus={autoFocus} returnKeyType="search" accessibilityLabel={s?.hint || "Search a stock"}
          style={{ flex: 1, height: 44, color: C.text, fontSize: 15, ...(Platform.OS === "web" ? ({ outlineStyle: "none" } as any) : {}) }} />
        {q ? <Pressable onPress={() => setQ("")} hitSlop={10} accessibilityLabel="Clear"><Icon name="close" size={18} /></Pressable> : null}
      </View>
      {q.trim() ? (
        <View style={[card(), { paddingHorizontal: 14, paddingVertical: 4 }]}>
          {list.loading && !rows.length ? <Text style={[T.meta, { color: C.dim, paddingVertical: 12 }]}>Loading the stock list…</Text> : null}
          {!list.loading && !hits.length ? <Text style={[T.meta, { color: C.dim, paddingVertical: 12 }]}>No NSE stock matches that.</Text> : null}
          {hits.map((h, i) => (
            <Pressable key={h.s} onPress={() => open(h.s)} accessibilityRole="button" accessibilityLabel={`${h.n}, ${h.s}`}
              style={{ flexDirection: "row", alignItems: "center", gap: 12, minHeight: 52, borderBottomWidth: i === hits.length - 1 ? 0 : 1, borderBottomColor: C.line2 }}>
              <View style={{ flex: 1, minWidth: 0 }}>
                <Text style={[T.row, { color: C.text }]} numberOfLines={1}>{h.s}</Text>
                <Text style={[T.meta, { color: C.dim, fontWeight: "500" }]} numberOfLines={1}>{h.n}</Text>
              </View>
              <Icon name={onPick ? "plus" : "chev"} size={18} />
            </Pressable>
          ))}
        </View>
      ) : null}
    </View>
  );
}

async function watch(body: object, okWords?: string) {
  try {
    const r: any = await api("/v3/watch", body);
    tap();
    refreshPlaces();
    showToast(okWords || r?.words || "Saved.", 2400);
    return r;
  } catch (e: any) {
    showToast(e?.message || "That did not save. Try again.", 3000);
    return null;
  }
}

const Btn = ({ label, onPress, quiet, danger }: { label: string; onPress: () => void; quiet?: boolean; danger?: boolean }) => (
  <Pressable onPress={onPress} accessibilityRole="button"
    style={({ pressed }) => ({ minHeight: 44, paddingHorizontal: 16, borderRadius: 14, justifyContent: "center", alignItems: "center", opacity: pressed ? 0.8 : 1,
      backgroundColor: quiet || danger ? C.card2 : C.gold, borderWidth: quiet || danger ? 1 : 0, borderColor: C.line })}>
    <Text style={{ color: danger ? C.bad : quiet ? C.text : C.onInk, fontWeight: "700", fontSize: 15 }}>{label}</Text>
  </Pressable>
);

// Markets, under the Watchlist chip: start a list
export function WatchNew({ p }: { p: any }) {
  return (
    <View style={[card(), { padding: 16, gap: 10 }]}>
      {p.title ? <Text style={[T.section, { color: C.text }]}>{p.title}</Text> : null}
      {p.words ? <Text style={[T.body, { color: C.dim }]}>{p.words}</Text> : null}
      <Btn label="New watchlist" quiet={!p.words} onPress={async () => { const r = await watch({ action: "create" }); if (r?.id) go({ place: `watchlist:${r.id}` }); }} />
    </View>
  );
}

// the full watchlist screen: rename, add by search, remove, delete
export function WatchManage({ p }: { p: any }) {
  const [name, setName] = useState<string>(p.name);
  const [editing, setEditing] = useState(false);
  const [sure, setSure] = useState(false);
  return (
    <View style={{ gap: 12 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
        {editing ? (
          <TextInput value={name} onChangeText={setName} autoFocus maxLength={30} accessibilityLabel="Watchlist name" returnKeyType="done"
            onSubmitEditing={async () => { setEditing(false); if (name.trim() && name !== p.name) await watch({ action: "rename", id: p.id, name }); }}
            style={{ flex: 1, height: 44, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: C.line, color: C.text, fontSize: 17, fontWeight: "700",
              ...(Platform.OS === "web" ? ({ outlineStyle: "none" } as any) : {}) }} />
        ) : (
          <Text style={[T.title, { color: C.text, flex: 1 }]} numberOfLines={1}>{p.name}</Text>
        )}
        <Pressable onPress={async () => { if (editing) { setEditing(false); if (name.trim() && name !== p.name) await watch({ action: "rename", id: p.id, name }); } else setEditing(true); }}
          accessibilityRole="button" accessibilityLabel={editing ? "Save the name" : "Rename"} style={{ width: 44, height: 44, alignItems: "center", justifyContent: "center" }}>
          <Icon name={editing ? "check" : "pencil"} size={20} color={C.text} />
        </Pressable>
      </View>
      <StockSearch s={{ hint: "Add a stock to this list" }} onPick={(sym) => watch({ action: "add", id: p.id, sym })} />
      {(p.symbols || []).length ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {(p.symbols || []).map((s: string) => (
            <Pressable key={s} onPress={() => watch({ action: "remove", id: p.id, sym: s })} accessibilityRole="button" accessibilityLabel={`Remove ${s}`}
              style={{ flexDirection: "row", alignItems: "center", gap: 6, height: 32, paddingHorizontal: 12, borderRadius: 999, borderWidth: 1, borderColor: C.line, backgroundColor: C.card }}>
              <Text style={{ color: C.text, fontSize: 13, fontWeight: "600" }}>{s}</Text>
              <Icon name="close" size={14} />
            </Pressable>
          ))}
        </View>
      ) : null}
      {sure ? (
        <View style={{ flexDirection: "row", gap: 10 }}>
          <View style={{ flex: 1 }}><Btn label="Delete it" danger onPress={async () => { await watch({ action: "delete", id: p.id }); go({ tab: "markets" }); }} /></View>
          <View style={{ flex: 1 }}><Btn label="Keep it" quiet onPress={() => setSure(false)} /></View>
        </View>
      ) : (
        <Pressable onPress={() => setSure(true)} accessibilityRole="button" style={{ alignSelf: "flex-start", minHeight: 36, justifyContent: "center" }}>
          <Text style={{ color: C.dim, fontSize: 13, fontWeight: "600" }}>Delete this watchlist</Text>
        </Pressable>
      )}
    </View>
  );
}

// a stock's page: add it to a watchlist (or make the first one)
export function WatchAdd({ p }: { p: any }) {
  const lists = useData<any>("/v3/place/markets?m=india", 0);
  const [open, setOpen] = useState(false);
  const all: { id: string; label: string }[] = [];
  for (const part of lists.data?.parts || []) {
    if (part.t === "rows" && (part.tags || []).includes("watchlist") && part.more?.place?.startsWith("watchlist:"))
      all.push({ id: part.more.place.split(":")[1], label: part.title });
  }
  const inList: string[] = p.in || [];
  return (
    <View style={{ gap: 8 }}>
      {inList.length ? <Text style={[T.meta, { color: C.dim, fontWeight: "500" }]}>In {inList.join(", ")}</Text> : null}
      {!open ? (
        <Btn label="Add to watchlist" onPress={() => (all.length ? setOpen(true) : watch({ action: "create", sym: p.sym }))} />
      ) : (
        <View style={[card(), { paddingHorizontal: 14, paddingVertical: 4 }]}>
          {all.map((w, i) => (
            <Pressable key={w.id} onPress={async () => { setOpen(false); await watch({ action: "add", id: w.id, sym: p.sym }); }} accessibilityRole="button"
              style={{ flexDirection: "row", alignItems: "center", minHeight: 50, borderBottomWidth: 1, borderBottomColor: C.line2 }}>
              <Text style={[T.row, { color: C.text, flex: 1 }]}>{w.label}</Text>
              <Icon name="plus" size={18} />
            </Pressable>
          ))}
          <Pressable onPress={async () => { setOpen(false); await watch({ action: "create", sym: p.sym }); }} accessibilityRole="button" style={{ minHeight: 50, justifyContent: "center" }}>
            <Text style={[T.row, { color: C.gold }]}>New watchlist with {p.sym}</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}
