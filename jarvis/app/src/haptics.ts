// Small taps you can feel (so you know Ananta heard you, without looking). Never breaks the app if unavailable.
import * as ExpoHaptics from "expo-haptics";
import { Vibration } from "react-native";

export const tap = () => {
  try { ExpoHaptics.impactAsync(ExpoHaptics.ImpactFeedbackStyle.Light).catch(() => {}); } catch { try { Vibration.vibrate(8); } catch { /* */ } }
};
export const soft = () => {
  try { ExpoHaptics.selectionAsync().catch(() => {}); } catch { /* */ }
};
