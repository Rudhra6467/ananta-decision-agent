// The Oct 6 welcome screens are retired (plan 5.8): a new visitor meets Ananta in the first conversation, inside Ask Ananta.
// Old links to /welcome land there, after the three hello steps (app/hello.tsx, 1 Nov).
import { useEffect } from "react";
import { View } from "react-native";
import { router } from "expo-router";
import { C } from "../src/theme";

export default function Welcome() {
  useEffect(() => { router.replace("/hello" as any); }, []);   // 1 Nov: hello first (app/hello.tsx), then the first conversation
  return <View style={{ flex: 1, backgroundColor: C.bg }} />;
}
