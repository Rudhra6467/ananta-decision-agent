// Registers this phone for Jarvis push alerts. Needs an Expo project id (set once with `eas init`);
// until then it quietly reports why it could not register.
import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import Constants from "expo-constants";
import { api } from "./api";

export async function registerPush(): Promise<string> {
  if (!Device.isDevice) return "push needs a real phone";
  const projectId = (Constants.expoConfig as any)?.extra?.eas?.projectId ?? (Constants as any).easConfig?.projectId;
  if (!projectId) return "push not set up yet (needs an Expo project id)";
  const perm = await Notifications.requestPermissionsAsync();
  if (perm.status !== "granted") return "notifications not allowed";
  const t = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
  await api("/push/register", { token: t, device: Device.modelName ?? "phone" });
  return "push registered";
}
