import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { cn } from '@/lib/utils';

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();

  const icon = theme === 'light' ? <Sun size={16} /> : theme === 'dark' ? <Moon size={16} /> : <Monitor size={16} />;
  const label = theme === 'light' ? 'Light' : theme === 'dark' ? 'Dark' : 'System';

  return (
    <button
      onClick={toggleTheme}
      className={cn(
        'inline-flex h-9 items-center gap-1.5 rounded-md border border-input bg-background px-2.5 text-xs font-medium transition-colors hover:bg-muted',
        className,
      )}
      aria-label={`Theme: ${label} (click to cycle)`}
      title={`Theme: ${label} — click to cycle`}
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}
