// Tiny wrapper so a missing haptics module never breaks the app.
import { Vibration } from "react-native";
export const tap = () => { try { Vibration.vibrate(8); } catch { /* ignore */ } };
