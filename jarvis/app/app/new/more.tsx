// More, one of the five places of the redesign (10 Nov 2026). Its parts come from /v3/place/more (jarvis/service/places.py, jarvis/india/places.py).
// 14 Nov 2026: Ask sits after More off the swipe path, so More's own swipe right takes him back to Activity (src/moreswipe.tsx).
import { PlaceScreen } from "../../src/placescreen";
import { ScreenError } from "../../src/safe";
import { MoreSwipe } from "../../src/moreswipe";

export const ErrorBoundary = ScreenError;
export default function More() {
  return <MoreSwipe><PlaceScreen name="more" title="More" /></MoreSwipe>;
}
