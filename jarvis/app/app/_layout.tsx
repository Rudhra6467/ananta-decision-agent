import { Stack, router } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { Pressable, Text, View } from "react-native";
import { token } from "../src/api";
import { useHere, useVoiceLive } from "../src/context";
import { C } from "../src/theme";

export default function Root() {
  useEffect(() => {
    token().then((t) => { if (!t) router.replace("/login"); });
  }, []);
  return (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: C.bg } }} />
      <VoicePill />
    </>
  );
}

// While voice mode is on and Ananta has moved you to another screen, this pill shows it is still listening.
function VoicePill() {
  const live = useVoiceLive();
  const here = useHere();
  if (!live || here?.screen === "ananta") return null;
  return (
    <View pointerEvents="box-none" style={{ position: "absolute", top: 56, left: 0, right: 0, alignItems: "center" }}>
      <Pressable onPress={() => router.navigate("/(tabs)/ask")} style={{ flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: C.text,
        borderRadius: 999, paddingHorizontal: 14, paddingVertical: 7, shadowColor: "#000", shadowOpacity: 0.2, shadowRadius: 6 }}>
        <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: C.bad }} />
        <Text style={{ color: "#FFF", fontWeight: "600", fontSize: 13 }}>Ananta is listening · tap to return</Text>
      </Pressable>
    </View>
  );
}
