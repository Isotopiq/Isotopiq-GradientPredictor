import { useState, useEffect, useMemo } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend } from 'recharts';
import { Columns, Calculator, Search, X, Plus } from 'lucide-react';
import { columnsApi } from '@/api/columns';
import { toast } from 'sonner';
import type { TanakaParameters, ColumnComparisonResult, ColumnSpec } from '@/types';

const PARAM_LABELS: Record<string, string> = {
  k_pb: 'Hydrophobicity',
  alpha_ch2: 'Methylene Sel.',
  alpha_t_o: 'Shape Sel.',
  alpha_c_p: 'H-Bond',
  alpha_b_a_76: 'Ion Exch. (7.6)',
  alpha_b_a_27: 'Ion Exch. (2.7)',
};

const COLUMN_COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b'];
const COLUMN_LABELS = ['A', 'B', 'C', 'D'];
const MAX_COLUMNS = 4;

interface SelectedColumn {
  columnId: string;
  params: TanakaParameters | null;
  loading: boolean;
}

export function ColumnComparisonPage() {
  const [reference, setReference] = useState<Record<string, TanakaParameters>>({});
  const [dbColumns, setDbColumns] = useState<ColumnSpec[]>([]);
  const [dbLoading, setDbLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showDropdown, setShowDropdown] = useState<number | null>(null);
  const [selected, setSelected] = useState<SelectedColumn[]>([
    { columnId: '', params: null, loading: false },
    { columnId: '', params: null, loading: false },
  ]);
  const [results, setResults] = useState<ColumnComparisonResult[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    columnsApi.getTanakaReference().then(res => {
      setReference(res.reference_columns);
    }).catch(() => toast.error('Failed to load reference columns'));

    // Load column database (fetch in batches for performance)
    setDbLoading(true);
    columnsApi.list({ limit: 200, offset: 0 }).then(res => {
      setDbColumns(res.columns);
    }).catch(() => toast.error('Failed to load column database'))
      .finally(() => setDbLoading(false));
  }, []);

  // Filter columns by search term
  const filteredColumns = useMemo(() => {
    if (!search.trim()) return dbColumns.slice(0, 100);
    const q = search.toLowerCase();
    return dbColumns.filter(c =>
      c.name.toLowerCase().includes(q) ||
      c.brand.toLowerCase().includes(q) ||
      c.chemistry.toLowerCase().includes(q) ||
      c.id.toLowerCase().includes(q)
    ).slice(0, 100);
  }, [dbColumns, search]);

  const activeColumns = selected.filter(s => s.params !== null);

  const handleSelectColumn = async (slot: number, columnId: string) => {
    // Check if already selected in another slot
    if (selected.some((s, i) => i !== slot && s.columnId === columnId)) {
      toast.error('Column already selected in another slot');
      return;
    }

    setSelected(prev => prev.map((s, i) => i === slot ? { ...s, columnId, loading: true, params: null } : s));
    setShowDropdown(null);
    setSearch('');

    try {
      const params = await columnsApi.getTanakaForColumn(columnId);
      setSelected(prev => prev.map((s, i) => i === slot ? { ...s, params, loading: false } : s));
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to load column parameters');
      setSelected(prev => prev.map((s, i) => i === slot ? { ...s, loading: false, columnId: '' } : s));
    }
  };

  const handleSelectReference = (slot: number, refKey: string) => {
    if (selected.some((s, i) => i !== slot && s.columnId === refKey)) {
      toast.error('Column already selected in another slot');
      return;
    }
    const params = reference[refKey];
    if (params) {
      setSelected(prev => prev.map((s, i) => i === slot ? { columnId: refKey, params, loading: false } : s));
    }
    setShowDropdown(null);
    setSearch('');
  };

  const handleClearSlot = (slot: number) => {
    setSelected(prev => prev.map((s, i) => i === slot ? { columnId: '', params: null, loading: false } : s));
    setResults([]);
  };

  const handleAddSlot = () => {
    if (selected.length >= MAX_COLUMNS) return;
    setSelected(prev => [...prev, { columnId: '', params: null, loading: false }]);
  };

  const handleRemoveSlot = (slot: number) => {
    if (selected.length <= 2) {
      toast.error('Need at least 2 columns for comparison');
      return;
    }
    setSelected(prev => prev.filter((_, i) => i !== slot));
    setResults([]);
  };

  const handleCompare = async () => {
    const valid = selected.filter(s => s.params);
    if (valid.length < 2) {
      toast.error('Select at least 2 columns');
      return;
    }
    setLoading(true);
    try {
      const newResults: ColumnComparisonResult[] = [];
      // Pairwise comparisons
      for (let i = 0; i < valid.length; i++) {
        for (let j = i + 1; j < valid.length; j++) {
          const res = await columnsApi.compareColumns(valid[i].params!, valid[j].params!);
          newResults.push(res);
        }
      }
      setResults(newResults);
      toast.success(`Compared ${valid.length} columns (${newResults.length} pairs)`);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Comparison failed');
    } finally {
      setLoading(false);
    }
  };

  // Radar chart data — supports up to 4 columns
  const radarData = useMemo(() => {
    const active = selected.filter(s => s.params);
    if (active.length === 0) return [];
    return Object.keys(PARAM_LABELS).map(key => {
      const row: Record<string, any> = { parameter: PARAM_LABELS[key] };
      active.forEach((s, i) => {
        row[`col${i}`] = (s.params as any)[key] || 0;
      });
      return row;
    });
  }, [selected]);

  const getColumnLabel = (slot: number) => {
    const s = selected[slot];
    if (!s) return '';
    if (s.params) return s.params.column_name;
    if (s.loading) return 'Loading...';
    return '';
  };

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4">
      <div className="flex items-center gap-2">
        <Columns className="h-5 w-5 text-accent" />
        <h1 className="text-xl font-bold">Tanaka Column Comparison</h1>
      </div>
      <p className="text-sm text-muted-foreground">
        Compare up to {MAX_COLUMNS} columns using the six Tanaka characterization parameters with radar plots and Column Distance Factor (CDF). Select from the commercial column database or reference types.
      </p>

      {/* Column selectors */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {selected.map((slot, slotIdx) => (
          <div key={slotIdx} className="card-scientific relative">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">
                <span
                  className="mr-2 inline-flex h-5 w-5 items-center justify-center rounded text-xs font-bold text-white"
                  style={{ background: COLUMN_COLORS[slotIdx % COLUMN_COLORS.length] }}
                >
                  {COLUMN_LABELS[slotIdx]}
                </span>
                {slot.params ? getColumnLabel(slotIdx) : slot.loading ? 'Loading...' : 'Select a column'}
              </h2>
              <div className="flex items-center gap-1">
                {slot.params && (
                  <button
                    onClick={() => handleClearSlot(slotIdx)}
                    className="text-muted-foreground hover:text-foreground"
                    title="Clear"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
                {selected.length > 2 && (
                  <button
                    onClick={() => handleRemoveSlot(slotIdx)}
                    className="text-red-500 hover:text-red-700 text-xs"
                    title="Remove slot"
                  >
                    Remove
                  </button>
                )}
              </div>
            </div>

            {/* Dropdown trigger */}
            {!slot.params && !slot.loading && (
              <div className="mt-2">
                <button
                  onClick={() => { setShowDropdown(showDropdown === slotIdx ? null : slotIdx); setSearch(''); }}
                  className="flex w-full items-center gap-2 rounded border border-border bg-background px-2 py-1.5 text-sm text-muted-foreground hover:border-accent"
                >
                  <Search className="h-3 w-3" />
                  Search columns from database...
                </button>
              </div>
            )}

            {/* Dropdown panel */}
            {showDropdown === slotIdx && (
              <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-80 overflow-hidden rounded-lg border border-border bg-card shadow-lg">
                {/* Search input */}
                <div className="border-b border-border p-2">
                  <div className="flex items-center gap-2">
                    <Search className="h-3 w-3 text-muted-foreground" />
                    <input
                      type="text"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Search by name, brand, or chemistry..."
                      autoFocus
                      className="flex-1 bg-transparent text-sm outline-none"
                    />
                  </div>
                </div>

                {/* Reference columns section */}
                <div className="max-h-64 overflow-y-auto">
                  <div className="border-b border-border/50 bg-muted/30 px-2 py-1 text-[10px] font-semibold uppercase text-muted-foreground">
                    Reference Types
                  </div>
                  {Object.entries(reference).map(([key, col]) => (
                    <button
                      key={key}
                      onClick={() => handleSelectReference(slotIdx, key)}
                      className="flex w-full items-center justify-between px-3 py-1.5 text-xs hover:bg-muted"
                    >
                      <span>{col.column_name}</span>
                      <span className="text-muted-foreground">{col.column_type}</span>
                    </button>
                  ))}

                  {/* Database columns section */}
                  <div className="border-b border-border/50 bg-muted/30 px-2 py-1 text-[10px] font-semibold uppercase text-muted-foreground">
                    Commercial Database {dbLoading ? '(loading...)' : `(${dbColumns.length} columns)`}
                  </div>
                  {dbLoading ? (
                    <div className="px-3 py-2 text-xs text-muted-foreground">Loading column database...</div>
                  ) : filteredColumns.length === 0 ? (
                    <div className="px-3 py-2 text-xs text-muted-foreground">No columns match "{search}"</div>
                  ) : (
                    filteredColumns.map(col => (
                      <button
                        key={col.id}
                        onClick={() => handleSelectColumn(slotIdx, col.id)}
                        className="flex w-full items-center justify-between px-3 py-1.5 text-xs hover:bg-muted"
                      >
                        <span className="truncate">
                          <span className="font-medium">{col.brand} {col.name}</span>
                          <span className="ml-1 text-muted-foreground">{col.particle_size_um}µm {col.length_mm}×{col.inner_diameter_mm}</span>
                        </span>
                        <span className="ml-2 shrink-0 badge badge-info text-[9px]">{col.chemistry}</span>
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* Show Tanaka params summary if loaded */}
            {slot.params && (
              <div className="mt-2 grid grid-cols-3 gap-1 text-[10px] text-muted-foreground">
                <span>k<sub>PB</sub>: {slot.params.k_pb.toFixed(2)}</span>
                <span>α<sub>CH2</sub>: {slot.params.alpha_ch2.toFixed(2)}</span>
                <span>α<sub>T/O</sub>: {slot.params.alpha_t_o.toFixed(2)}</span>
                <span>α<sub>C/P</sub>: {slot.params.alpha_c_p.toFixed(2)}</span>
                <span>α<sub>B/A</sub>⁷·⁶: {slot.params.alpha_b_a_76.toFixed(2)}</span>
                <span>α<sub>B/A</sub>²·⁷: {slot.params.alpha_b_a_27.toFixed(2)}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Add column slot button */}
      {selected.length < MAX_COLUMNS && (
        <button
          onClick={handleAddSlot}
          className="flex items-center gap-1 text-xs text-accent hover:underline"
        >
          <Plus className="h-3 w-3" /> Add column slot ({selected.length}/{MAX_COLUMNS})
        </button>
      )}

      <button onClick={handleCompare} disabled={loading || activeColumns.length < 2} className="btn-primary flex items-center gap-2 text-sm">
        <Calculator className="h-4 w-4" />
        {loading ? 'Comparing...' : `Compare ${activeColumns.length} Columns`}
      </button>

      {/* Radar Chart */}
      {activeColumns.length >= 2 && (
        <div className="card-scientific">
          <h2 className="text-sm font-semibold">Tanaka Parameter Radar</h2>
          <ResponsiveContainer width="100%" height={400}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="parameter" tick={{ fontSize: 10 }} />
              <PolarRadiusAxis tick={{ fontSize: 9 }} />
              {activeColumns.map((s, i) => (
                <Radar
                  key={i}
                  name={s.params!.column_name}
                  dataKey={`col${i}`}
                  stroke={COLUMN_COLORS[i % COLUMN_COLORS.length]}
                  fill={COLUMN_COLORS[i % COLUMN_COLORS.length]}
                  fillOpacity={0.15}
                />
              ))}
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Comparison Results — pairwise */}
      {results.length > 0 && (
        <div className="space-y-3">
          <div className="card-scientific">
            <h2 className="text-sm font-semibold">Pairwise Comparison Metrics</h2>
            <table className="mt-2 w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-2 py-1 text-left">Pair</th>
                  <th className="px-2 py-1 text-right">CDF</th>
                  <th className="px-2 py-1 text-right">Similarity</th>
                  <th className="px-2 py-1 text-right">Orthogonality</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td className="px-2 py-1 font-medium">
                      {r.column_a.column_name} <span className="text-muted-foreground">vs</span> {r.column_b.column_name}
                    </td>
                    <td className="px-2 py-1 text-right tabular-nums">{r.cdf.toFixed(3)}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{(r.similarity * 100).toFixed(1)}%</td>
                    <td className="px-2 py-1 text-right tabular-nums">{(r.orthogonality * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Parameter table for first pair (most detailed) */}
          {results[0] && (
            <div className="card-scientific">
              <h2 className="text-sm font-semibold">
                Parameter Details: {results[0].column_a.column_name} vs {results[0].column_b.column_name}
              </h2>
              <table className="mt-2 w-full text-xs">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-2 py-1 text-left">Parameter</th>
                    <th className="px-2 py-1 text-right">{results[0].column_a.column_name}</th>
                    <th className="px-2 py-1 text-right">{results[0].column_b.column_name}</th>
                    <th className="px-2 py-1 text-right">|Δ|</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.keys(PARAM_LABELS).map(key => (
                    <tr key={key} className="border-b border-border/50">
                      <td className="px-2 py-1">{PARAM_LABELS[key]}</td>
                      <td className="px-2 py-1 text-right tabular-nums">{(results[0].column_a as any)[key].toFixed(3)}</td>
                      <td className="px-2 py-1 text-right tabular-nums">{(results[0].column_b as any)[key].toFixed(3)}</td>
                      <td className="px-2 py-1 text-right tabular-nums">{results[0].parameter_differences[key].toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="card-scientific text-xs text-muted-foreground">
            <p><strong>Interpretation:</strong></p>
            <ul className="ml-4 mt-1 list-disc space-y-1">
              <li><strong>CDF &lt; 1:</strong> Columns are very similar — substitutable for most methods.</li>
              <li><strong>CDF 1-3:</strong> Moderate difference — may require method adjustment.</li>
              <li><strong>CDF &gt; 3:</strong> Very different columns — useful for orthogonal screening.</li>
              <li><strong>High orthogonality:</strong> Columns provide complementary selectivity — good for 2D-LC.</li>
              <li><strong>Note:</strong> Tanaka parameters for commercial columns are estimated from stationary phase properties. For precise work, experimental Tanaka characterization is recommended.</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
