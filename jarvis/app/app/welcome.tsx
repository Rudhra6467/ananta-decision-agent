// The Oct 6 welcome screens are retired (plan 5.8): a new visitor meets Ananta in the first conversation, inside Ask Ananta.
// Old links to /welcome land there.
import { useEffect } from "react";
import { View } from "react-native";
import { router } from "expo-router";
import { C } from "../src/theme";

export default function Welcome() {
  useEffect(() => { router.replace("/(tabs)/ask"); }, []);
  return <View style={{ flex: 1, backgroundColor: C.bg }} />;
}
