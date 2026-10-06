// Face ID (or the phone passcode) before anything that changes money, mode or the kill switch.
import * as LocalAuthentication from "expo-local-authentication";
import { Alert, Platform } from "react-native";

export async function confirmWithFaceId(title: string, message: string): Promise<boolean> {
  if (Platform.OS === "web") return window.confirm(`${title}\n\n${message}`);   // the website: the browser's own OK / Cancel
  const ok = await new Promise<boolean>((res) =>
    Alert.alert(title, message, [
      { text: "Cancel", style: "cancel", onPress: () => res(false) },
      { text: "Continue", style: "destructive", onPress: () => res(true) },
    ]),
  );
  if (!ok) return false;
  const has = await LocalAuthentication.hasHardwareAsync();
  if (!has) return true; // simulator / no biometrics: the confirmation dialog is the guard
  const r = await LocalAuthentication.authenticateAsync({ promptMessage: title, fallbackLabel: "Use passcode" });
  return r.success;
}
