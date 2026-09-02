import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Command } from 'cmdk';
import {
  LayoutDashboard,
  FlaskConical,
  BookMarked,
  Upload,
  BarChart3,
  Layers,
  GitCompare,
  Database,
  LayoutTemplate,
  Search,
} from 'lucide-react';
import { compoundsApi } from '@/api/compounds';

interface CommandItem {
  id: string;
  label: string;
  category: string;
  icon: React.ReactNode;
  action: () => void;
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [compoundResults, setCompoundResults] = useState<Array<{ name: string; smiles: string }>>([]);
  const navigate = useNavigate();

  // Toggle with Ctrl+K / Cmd+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Debounced compound search
  useEffect(() => {
    if (!search || search.length < 3 || !open) {
      setCompoundResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const results = await compoundsApi.searchMulti(search, 5);
        setCompoundResults(results);
      } catch {
        setCompoundResults([]);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [search, open]);

  const navItems: CommandItem[] = [
    { id: 'nav-dashboard', label: 'Go to Dashboard', category: 'Navigate', icon: <LayoutDashboard size={16} />, action: () => navigate('/dashboard') },
    { id: 'nav-predictor', label: 'Go to Predictor', category: 'Navigate', icon: <FlaskConical size={16} />, action: () => navigate('/') },
    { id: 'nav-methods', label: 'Go to Method Library', category: 'Navigate', icon: <BookMarked size={16} />, action: () => navigate('/methods') },
    { id: 'nav-data', label: 'Go to Data Upload', category: 'Navigate', icon: <Upload size={16} />, action: () => navigate('/data') },
    { id: 'nav-models', label: 'Go to ML Models', category: 'Navigate', icon: <BarChart3 size={16} />, action: () => navigate('/models') },
    { id: 'nav-batch', label: 'Go to Batch Analysis', category: 'Navigate', icon: <Layers size={16} />, action: () => navigate('/batch') },
    { id: 'nav-compare', label: 'Go to Method Comparison', category: 'Navigate', icon: <GitCompare size={16} />, action: () => navigate('/compare') },
    { id: 'nav-columns', label: 'Go to Column Database', category: 'Navigate', icon: <Database size={16} />, action: () => navigate('/columns') },
    { id: 'nav-templates', label: 'Go to Templates', category: 'Navigate', icon: <LayoutTemplate size={16} />, action: () => navigate('/templates') },
  ];

  const handleSelect = useCallback((item: CommandItem) => {
    item.action();
    setOpen(false);
    setSearch('');
  }, []);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-[15vh]" onClick={() => setOpen(false)}>
      <Command
        className="w-full max-w-xl overflow-hidden rounded-lg border border-border bg-card shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        shouldFilter={false}
      >
        <div className="flex items-center gap-2 border-b border-border px-3">
          <Search size={16} className="text-muted-foreground" />
          <Command.Input
            autoFocus
            placeholder="Search compounds or navigate..."
            value={search}
            onValueChange={setSearch}
            className="h-12 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          <kbd className="rounded border border-border px-1 text-[10px] text-muted-foreground">ESC</kbd>
        </div>
        <Command.List className="max-h-[400px] overflow-y-auto p-2">
          <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
            No results found.
          </Command.Empty>

          {navItems.length > 0 && (
            <Command.Group heading="Navigate" className="text-sm">
              {navItems.map((item) => (
                <Command.Item
                  key={item.id}
                  value={item.label}
                  onSelect={() => handleSelect(item)}
                  className="flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-2 text-sm aria-selected:bg-muted"
                >
                  {item.icon}
                  <span>{item.label}</span>
                </Command.Item>
              ))}
            </Command.Group>
          )}

          {compoundResults.length > 0 && (
            <Command.Group heading="Compounds" className="text-sm">
              {compoundResults.map((c, i) => (
                <Command.Item
                  key={`compound-${i}`}
                  value={`compound-${c.name}-${c.smiles}`}
                  onSelect={() => {
                    navigate(`/?smiles=${encodeURIComponent(c.smiles)}`);
                    setOpen(false);
                    setSearch('');
                  }}
                  className="flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-2 text-sm aria-selected:bg-muted"
                >
                  <Search size={14} className="text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{c.name}</p>
                    <p className="truncate text-xs text-muted-foreground">{c.smiles}</p>
                  </div>
                </Command.Item>
              ))}
            </Command.Group>
          )}
        </Command.List>
      </Command>
    </div>
  );
}
