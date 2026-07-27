import React, { createContext, useContext, useEffect } from "react"

type Theme = "dark"

const ThemeContext = createContext<{ theme: Theme }>({ theme: "dark" })

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const root = window.document.documentElement
    root.classList.add("dark")
  }, [])

  return (
    <ThemeContext.Provider value={{ theme: "dark" }}>
      {children}
    </ThemeContext.Provider>
  )
}

export const useTheme = () => useContext(ThemeContext)
