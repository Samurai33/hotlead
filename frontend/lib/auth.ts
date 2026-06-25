const KEY = "hotlead_api_key";

export function getApiKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(KEY) ?? "";
}

export function setApiKey(key: string): void {
  localStorage.setItem(KEY, key.trim());
}

export function clearApiKey(): void {
  localStorage.removeItem(KEY);
}

export function hasApiKey(): boolean {
  return getApiKey().length > 0;
}

export function redirectToLogin(): void {
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}
