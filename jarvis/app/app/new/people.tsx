// People (the new look): who can talk to Ananta and what each may do; teach my voice; invite. Data: /india/v3/people (names and relations
// only). Only Madhav decides; everyone else can ask.
import { Text, View } from "react-native";
import { router } from "expo-router";
import { useData } from "../../src/useData";
import { NScreen } from "../../src/newscreen";
import { Body, Btn, Chev, LockIcon, Meta, NCard, TY } from "../../src/newui";
import { C } from "../../src/theme";
import { ScreenError } from "../../src/safe";

export const ErrorBoundary = ScreenError;

export default function People() {
  const { data: d, err, loading, reload } = useData<any>("/v3/people", 300000);
  return (
    <NScreen title="People" loading={loading} onRefresh={reload} err={err}>
      {d ? (
        <>
          <Body dim>{d.rule}</Body>
          <View style={{ backgroundColor: C.card, borderRadius: 16, paddingHorizontal: 16, paddingVertical: 4 }}>
            {(d.people || []).map((p: any, i: number) => (
              <View key={p.id} style={{ flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 12, borderTopWidth: i ? 1 : 0, borderTopColor: C.line }}>
                <View style={{ width: 40, height: 40, borderRadius: 999, backgroundColor: C.card2, alignItems: "center", justifyContent: "center" }}><Text style={{ color: C.text, fontWeight: "700" }}>{String(p.name || "?")[0]}</Text></View>
                <View style={{ flex: 1 }}>
                  <Text style={[TY.figure, { color: C.text }]}>{p.name} <Meta>{p.relation}</Meta></Text>
                  <Meta faint>{[p.voice, p.can].filter(Boolean).join(" · ")}</Meta>
                </View>
                <Chev />
              </View>
            ))}
          </View>
          <View style={{ flexDirection: "row", gap: 10 }}>
            <Btn label="Invite someone" kind="p" onPress={() => router.push("/people" as any)} />
            <Btn label="Teach my voice" kind="s" onPress={() => router.push("/voiceid" as any)} />
          </View>
          <NCard pad={14}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}><LockIcon color={C.dim} /><Body dim style={{ flex: 1 }}>{d.invite}</Body></View>
          </NCard>
        </>
      ) : null}
    </NScreen>
  );
}
