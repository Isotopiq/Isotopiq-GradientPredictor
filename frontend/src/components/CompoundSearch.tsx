import { useState, useEffect, useCallback, useRef } from 'react';
import { Search, Loader2, ExternalLink, Plus } from 'lucide-react';
import { apiClient } from '@/api/client';
import { cn } from '@/lib/utils';

interface SearchResult {
  name: string;
  smiles: string;
  inchikey: string;
  formula: string;
  mw: string;
  source: string;
}

interface CompoundSearchProps {
  onSelect: (result: SearchResult) => void;
  placeholder?: string;
}

export function CompoundSearch({ onSelect, placeholder = 'Search compound by name...' }: CompoundSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const search = useCallback(async (term: string) => {
    if (term.trim().length < 2) {
      setResults([]);
      return;
    }
    setLoading(true);
    try {
      const { data } = await apiClient.get<SearchResult[]>('/compounds/search/multi', {
        params: { name: term.trim(), limit: 15 },
      });
      setResults(data);
      setShowResults(true);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Debounced search on input
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.trim().length >= 2) {
      debounceRef.current = setTimeout(() => search(query), 400);
    } else {
      setResults([]);
    }
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, search]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowResults(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSelect = (result: SearchResult) => {
    onSelect(result);
    setShowResults(false);
    setQuery(result.name || result.smiles);
  };

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <Search
          size={14}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
        />
        <input
          className="input pl-9 pr-8"
          placeholder={placeholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setShowResults(true)}
        />
        {loading && (
          <Loader2
            size={14}
            className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-muted-foreground"
          />
        )}
      </div>

      {showResults && (results.length > 0 || (!loading && query.trim().length >= 2)) && (
        <div className="absolute z-50 mt-1 max-h-80 w-full overflow-y-auto rounded-md border border-border bg-card shadow-lg">
          {results.length === 0 && !loading && (
            <div className="p-3 text-center text-xs text-muted-foreground">
              No results found for "{query}"
            </div>
          )}
          {results.map((r, i) => (
            <button
              type="button"
              key={`${r.inchikey}-${i}`}
              onClick={() => handleSelect(r)}
              className={cn(
                'flex w-full items-start gap-3 border-b border-border p-3 text-left last:border-0',
                'hover:bg-muted transition-colors',
              )}
            >
              <div className="shrink-0">
                <span
                  className={cn(
                    'rounded px-1.5 py-0.5 text-[10px] font-medium',
                    r.source === 'pubchem'
                      ? 'bg-indigo-500/10 text-indigo-500'
                      : 'bg-emerald-500/10 text-emerald-500',
                  )}
                >
                  {r.source}
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{r.name}</p>
                <p className="truncate font-mono text-xs text-muted-foreground">{r.smiles}</p>
                <div className="mt-0.5 flex gap-3 text-xs text-muted-foreground">
                  <span>{r.formula}</span>
                  <span>{r.mw} g/mol</span>
                  {r.inchikey && <span className="truncate">{r.inchikey}</span>}
                </div>
              </div>
              <Plus size={14} className="mt-1 shrink-0 text-muted-foreground" />
            </button>
          ))}
          {results.length > 0 && (
            <div className="border-t border-border p-2 text-center">
              <a
                href={`https://pubchem.ncbi.nlm.nih.gov/#query=${encodeURIComponent(query)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                <ExternalLink size={10} />
                Search PubChem directly
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
