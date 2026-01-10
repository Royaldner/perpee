/**
 * React hook for managing theme (light/dark mode).
 */

import { useState, useEffect, useCallback } from "react"

type Theme = "light" | "dark" | "system"

const THEME_KEY = "perpee-theme"

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light"
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light"
}

function getStoredTheme(): Theme {
  if (typeof window === "undefined") return "system"
  const stored = localStorage.getItem(THEME_KEY)
  if (stored === "light" || stored === "dark" || stored === "system") {
    return stored
  }
  return "system"
}

function applyTheme(theme: Theme): void {
  const root = document.documentElement
  const effectiveTheme = theme === "system" ? getSystemTheme() : theme

  if (effectiveTheme === "dark") {
    root.classList.add("dark")
  } else {
    root.classList.remove("dark")
  }
}

interface UseThemeReturn {
  theme: Theme
  effectiveTheme: "light" | "dark"
  setTheme: (theme: Theme) => void
}

export function useTheme(): UseThemeReturn {
  const [theme, setThemeState] = useState<Theme>(getStoredTheme)
  const [effectiveTheme, setEffectiveTheme] = useState<"light" | "dark">(
    theme === "system" ? getSystemTheme() : theme
  )

  // Apply theme on mount and when theme changes
  useEffect(() => {
    applyTheme(theme)
    setEffectiveTheme(theme === "system" ? getSystemTheme() : theme)
  }, [theme])

  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")

    const handleChange = () => {
      if (theme === "system") {
        applyTheme("system")
        setEffectiveTheme(getSystemTheme())
      }
    }

    mediaQuery.addEventListener("change", handleChange)
    return () => mediaQuery.removeEventListener("change", handleChange)
  }, [theme])

  const setTheme = useCallback((newTheme: Theme) => {
    localStorage.setItem(THEME_KEY, newTheme)
    setThemeState(newTheme)
  }, [])

  return {
    theme,
    effectiveTheme,
    setTheme,
  }
}
