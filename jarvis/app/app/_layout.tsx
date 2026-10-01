import { Stack, router } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { token } from "../src/api";
import { C } from "../src/theme";

export default function Root() {
  useEffect(() => {
    token().then((t) => { if (!t) router.replace("/login"); });
  }, []);
  return (
    <>
      <StatusBar style="light" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: C.bg } }} />
    </>
  );
}
