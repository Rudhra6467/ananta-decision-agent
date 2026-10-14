// expo-secure-store has no web version; on the web build (livetrading247.com) the same calls use the browser's storage.
// metro.config.js points 'expo-secure-store' here for web only; phones keep the real keychain.
function box(): Storage | null {
  try {
    return typeof window !== "undefined" ? window.localStorage : null;
  } catch {
    return null;
  }
}

export async function getItemAsync(key: string): Promise<string | null> {
  return box()?.getItem(key) ?? null;
}

export async function setItemAsync(key: string, value: string): Promise<void> {
  box()?.setItem(key, value);
}

export async function deleteItemAsync(key: string): Promise<void> {
  box()?.removeItem(key);
}

export function getItem(key: string): string | null {
  return box()?.getItem(key) ?? null;
}

export function setItem(key: string, value: string): void {
  box()?.setItem(key, value);
}

export async function isAvailableAsync(): Promise<boolean> {
  return !!box();
}

export const AFTER_FIRST_UNLOCK = 0;
export const WHEN_UNLOCKED = 1;
