import { Moon, Sun } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { cn } from '@/lib/utils';

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();
  return (
    <button
      onClick={toggleTheme}
      className={cn(
        'inline-flex h-9 w-9 items-center justify-center rounded-md border border-input bg-background transition-colors hover:bg-muted',
        className,
      )}
      aria-label="Toggle theme"
    >
      {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
    </button>
  );
}
