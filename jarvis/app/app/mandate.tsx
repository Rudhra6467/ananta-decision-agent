import { setScreen } from "../src/context";
import { useFocusEffect } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Alert, Pressable, Text, TextInput, View } from "react-native";
import { Stack } from "expo-router";
import { api } from "../src/api";
import { confirmWithFaceId } from "../src/guard";
import { Btn, Busy, Card, Divider, ErrorBox, Screen, Section, T } from "../src/ui";
import { useData } from "../src/useData";
import { C } from "../src/theme";

// The owner's standing brief for Ananta. Ananta reads it before every answer; only the owner changes it.
export default function MandateScreen() {
  useFocusEffect(useCallback(() => { setScreen({ screen: "mandate", label: "Your mandate (goals and limits)" }); }, []));
  const { data: d, err, loading, reload } = useData("/v3/mandate", 0);
  const [edit, setEdit] = useState<Record<string, string[]> | null>(null);
  useEffect(() => { if (d && !edit) setEdit(JSON.parse(JSON.stringify(d.sections))); }, [d]);
  const head = <Stack.Screen options={{ headerShown: true, title: "Your mandate", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false, headerTintColor: C.text, headerBackTitle: "Back" }} />;
  if (!d && loading) return <>{head}<Busy /></>;
  if (!d || !edit) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen></>;
  const changed = JSON.stringify(edit) !== JSON.stringify(d.sections);
  const save = async () => {
    if (!(await confirmWithFaceId("Save mandate", "Ananta will follow the new version from the next answer."))) return;
    try {
      await api("/v3/mandate", { sections: edit, why: "edited in the app" });
      setEdit(null);
      reload();
    } catch (e: any) {
      Alert.alert("Not saved", e?.message ?? String(e));
    }
  };
  const setLine = (k: string, i: number, v: string) => setEdit({ ...edit, [k]: edit[k].map((x, j) => (j === i ? v : x)) });
  const delLine = (k: string, i: number) => setEdit({ ...edit, [k]: edit[k].filter((_, j) => j !== i) });
  const addLine = (k: string) => setEdit({ ...edit, [k]: [...edit[k], ""] });
  return (
    <>
      {head}
      <Screen loading={loading} onRefresh={() => { setEdit(null); reload(); }}>
        <T dim>Ananta reads this before every answer: your goals, markets, styles and limits. Edit a line, or ask Ananta to change it (you confirm).</T>
        <T small>Version {d.version}{d.version ? ` · saved by ${d.by}` : " · default"}</T>
        {Object.keys(d.names).map((k) => (
          <View key={k} style={{ gap: 8 }}>
            <Section title={d.names[k]} />
            <Card>
              {(edit[k] ?? []).map((line, i) => (
                <View key={i}>
                  {i ? <Divider /> : null}
                  <View style={{ flexDirection: "row", gap: 8, alignItems: "flex-start", paddingVertical: 4 }}>
                    <TextInput value={line} onChangeText={(v) => setLine(k, i, v)} multiline placeholder="New line…" placeholderTextColor={C.faint}
                      style={{ flex: 1, color: C.text, fontSize: 14, lineHeight: 20, paddingVertical: 4 }} />
                    <Text onPress={() => delLine(k, i)} style={{ color: C.faint, fontSize: 16, paddingTop: 4 }}>✕</Text>
                  </View>
                </View>
              ))}
              <Pressable onPress={() => addLine(k)}><Text style={{ color: C.accent, fontWeight: "600", paddingTop: 4 }}>+ Add line</Text></Pressable>
            </Card>
          </View>
        ))}
        {changed ? <Btn label="Save changes" onPress={save} /> : null}
        {d.history?.length ? (
          <Card title="History">
            {d.history.map((h: any) => <T key={h.version} small>v{h.version} · {new Date(h.t * 1000).toLocaleString()} · {h.why}</T>)}
          </Card>
        ) : null}
      </Screen>
    </>
  );
}
