// 14 Nov 2026: More is the last page a finger reaches (Ask sits after it, off the swipe path, app/new/_layout.tsx), so the pager's own swipe
// is off there; a swipe right on More still goes back to Activity, a swipe left goes nowhere.
import { useNavigation } from "expo-router";
import { useRef } from "react";
import { PanResponder, View } from "react-native";

export function MoreSwipe({ children }: { children: React.ReactNode }) {
  const nav = useNavigation<any>();
  const pr = useRef(PanResponder.create({
    onMoveShouldSetPanResponderCapture: (_e, g) => g.dx > 18 && Math.abs(g.dx) > Math.abs(g.dy) * 2,
    onPanResponderRelease: (_e, g) => { if (g.dx > 60 || g.vx > 0.3) nav.navigate("activity"); },
    onPanResponderTerminationRequest: () => true,
  })).current;
  return <View style={{ flex: 1 }} {...pr.panHandlers}>{children}</View>;
}
