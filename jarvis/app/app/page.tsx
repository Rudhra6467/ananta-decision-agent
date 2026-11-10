// A page one tap under a place (Madhav, 10 Nov 2026, the redesign): the account, an information page, a receipt, a holding, Proof, the bell,
// the open list. Either it rode in with the place's payload (?id=, src/place.tsx) or it is a place of its own on the server (?place=).
import { useLocalSearchParams } from "expo-router";
import { PageScreen } from "../src/placescreen";
import { pageOf } from "../src/place";
import { ScreenError } from "../src/safe";

export const ErrorBoundary = ScreenError;

export default function Page() {
  const { id, place } = useLocalSearchParams<{ id?: string; place?: string }>();
  const page = id ? pageOf(String(id)) : undefined;
  return <PageScreen page={page} place={!page ? (place ? String(place) : "home") : undefined} />;
}
