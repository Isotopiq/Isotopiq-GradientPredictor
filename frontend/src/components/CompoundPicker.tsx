import { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, Search, Plus, Check } from 'lucide-react';
import { compoundsApi } from '@/api/compounds';
import { MoleculeThumbnail } from '@/components/MoleculeViewer';
import { cn } from '@/lib/utils';
import type { Compound } from '@/types';

interface CompoundPickerProps {
  onSelect: (compound: Compound) => void;
  placeholder?: string;
  className?: string;
}

export function CompoundPicker({ onSelect, placeholder = 'Select saved compound...', className }: CompoundPickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 200);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch('');
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const { data: compounds } = useQuery({
    queryKey: ['compounds', debouncedSearch],
    queryFn: () => compoundsApi.list(debouncedSearch || undefined, 50, 0),
    enabled: open,
  });

  const handleSelect = useCallback((compound: Compound) => {
    onSelect(compound);
    setOpen(false);
    setSearch('');
  }, [onSelect]);

  return (
    <div ref={ref} className={cn('relative', className)}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="input flex items-center justify-between text-sm"
      >
        <span className="flex items-center gap-2 text-muted-foreground">
          <Search size={14} />
          {placeholder}
        </span>
        <ChevronDown size={14} className={cn('transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border border-border bg-card shadow-lg">
          {/* Search input */}
          <div className="border-b border-border p-2">
            <input
              autoFocus
              className="input text-sm"
              placeholder="Search by name or SMILES..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* Results */}
          <div className="max-h-64 overflow-y-auto">
            {compounds && compounds.length > 0 ? (
              compounds.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => handleSelect(c)}
                  className="flex w-full items-center gap-3 px-2 py-2 text-left hover:bg-muted/50"
                >
                  {c.smiles && <MoleculeThumbnail smiles={c.smiles} size={36} />}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium">
                      {c.name || 'Unnamed'}
                    </p>
                    <p className="truncate font-mono text-[10px] text-muted-foreground">
                      {c.smiles || '—'}
                    </p>
                  </div>
                  <div className="shrink-0 text-right text-[10px] text-muted-foreground">
                    {c.mw && <div>MW {c.mw.toFixed(0)}</div>}
                    {c.logp != null && <div>logP {c.logp.toFixed(1)}</div>}
                  </div>
                </button>
              ))
            ) : (
              <div className="p-4 text-center text-xs text-muted-foreground">
                {search ? 'No compounds found' : 'No saved compounds yet'}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
