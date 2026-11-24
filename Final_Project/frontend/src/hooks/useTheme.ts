import { useSyncExternalStore } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "theme";
const listeners = new Set<() => void>();

function readTheme(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

/** Saved choice first, otherwise the operating system preference. */
export function initTheme() {
  let theme: Theme = "light";
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    theme =
      saved === "dark" || saved === "light"
        ? saved
        : window.matchMedia?.("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light";
  } catch {
    /* storage unavailable: keep the default */
  }
  document.documentElement.dataset.theme = theme;
}

function setTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    /* the choice just will not persist */
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useTheme() {
  const theme = useSyncExternalStore(subscribe, readTheme, () => "light" as Theme);
  return {
    theme,
    toggle: () => setTheme(theme === "dark" ? "light" : "dark"),
  };
}
