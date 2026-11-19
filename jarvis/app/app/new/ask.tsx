// Ask in the new look: the conversation screen is the classic one for now (its voice loop, Spotlight and handovers are wired deep); the
// voice-first restyle (the spoken line lit sentence by sentence, the big orb) is the next stage. The orb on the bar lands here.
// 19 Nov 2026 (Madhav: "while in Ananta voice tab, we should be able to swipe left to markets tab and swipe right to activity tab"): Ask sits off
// the pager's swipe path (app/new/_layout.tsx), so its own swipe does it: a finger moving right goes to Markets (the tab on its left), a
// finger moving left goes to Activity (the tab on its right). Sideways scrollers inside (the suggested questions) keep their own swipe.
import { useRef } from "react";
import { PanResponder, View } from "react-native";
import { useNavigation } from "expo-router";
import AskScreen, { ErrorBoundary } from "../(tabs)/ask";

export { ErrorBoundary };

export default function AskSwipe() {
  const nav = useNavigation<any>();
  const pr = useRef(PanResponder.create({
    onMoveShouldSetPanResponder: (_e, g) => Math.abs(g.dx) > 22 && Math.abs(g.dx) > Math.abs(g.dy) * 2.2,
    onPanResponderRelease: (_e, g) => {
      if (g.dx > 70 || g.vx > 0.4) nav.navigate("markets");
      else if (g.dx < -70 || g.vx < -0.4) nav.navigate("activity");
    },
    onPanResponderTerminationRequest: () => true,
  })).current;
  return <View style={{ flex: 1 }} {...pr.panHandlers}><AskScreen /></View>;
}
