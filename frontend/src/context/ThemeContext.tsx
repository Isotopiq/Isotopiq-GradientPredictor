import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

type Theme = 'light' | 'dark' | 'system';

interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: 'light' | 'dark';
  toggleTheme: () => void;
  setTheme: (t: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function getSystemTheme(): 'light' | 'dark' {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    const stored = localStorage.getItem('theme') as Theme | null;
    if (stored) return stored;
    return 'system';
  });

  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>(() => {
    const stored = localStorage.getItem('theme') as Theme | null;
    if (stored && stored !== 'system') return stored;
    return getSystemTheme();
  });

  useEffect(() => {
    const resolve = () => {
      const resolved = theme === 'system' ? getSystemTheme() : theme;
      setResolvedTheme(resolved);
      const root = document.documentElement;
      root.classList.toggle('dark', resolved === 'dark');
    };
    resolve();
    localStorage.setItem('theme', theme);

    // Listen to OS theme changes when in system mode
    if (theme === 'system') {
      const mq = window.matchMedia('(prefers-color-scheme: dark)');
      mq.addEventListener('change', resolve);
      return () => mq.removeEventListener('change', resolve);
    }
  }, [theme]);

  const toggleTheme = () => {
    setThemeState((prev) => {
      if (prev === 'light') return 'dark';
      if (prev === 'dark') return 'system';
      return 'light';
    });
  };

  const setTheme = (t: Theme) => setThemeState(t);

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
