// Activity, one of the five places of the redesign (10 Nov 2026). Its parts come from /v3/place/activity (jarvis/service/places.py, jarvis/india/places.py).
import { PlaceScreen } from "../../src/placescreen";
import { ScreenError } from "../../src/safe";

export const ErrorBoundary = ScreenError;
export default function Activity() {
  return <PlaceScreen name="activity" title="Activity" />;
}
