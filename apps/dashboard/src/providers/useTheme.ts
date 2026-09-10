import { createContext, useContext } from "react"

type Theme = "dark"

export type { Theme }

export const ThemeContext = createContext<{ theme: Theme }>({ theme: "dark" })

export function useTheme() {
  return useContext(ThemeContext)
}
