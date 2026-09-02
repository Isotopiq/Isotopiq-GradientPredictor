import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Database, Search } from 'lucide-react';
import { columnsApi } from '@/api/columns';
import { EmptyState } from '@/components/EmptyState';
import { Skeleton } from '@/components/Skeleton';

export function ColumnDatabasePage() {
  const [search, setSearch] = useState('');
  const [chemistryFilter, setChemistryFilter] = useState('');
  const [brandFilter, setBrandFilter] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: columns, isLoading } = useQuery({
    queryKey: ['columns', chemistryFilter, brandFilter],
    queryFn: () =>
      columnsApi.list({
        chemistry: chemistryFilter || undefined,
        brand: brandFilter || undefined,
        limit: 200,
      }),
  });

  const { data: chemistries } = useQuery({
    queryKey: ['chemistries'],
    queryFn: () => columnsApi.chemistries(),
  });

  const { data: brands } = useQuery({
    queryKey: ['brands'],
    queryFn: () => columnsApi.brands(),
  });

  const filtered = (columns || []).filter((c) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      c.brand.toLowerCase().includes(q) ||
      c.chemistry.toLowerCase().includes(q)
    );
  });

  const selected = filtered.find((c) => c.id === selectedId);

  return (
    <div className="mx-auto max-w-6xl p-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold">Commercial Column Database</h1>
        <p className="text-sm text-muted-foreground">
          Searchable database of common LC columns with specifications
        </p>
      </div>

      {/* Filters */}
      <div className="card-scientific mb-6">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label className="label">Search</label>
            <div className="relative mt-1">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                className="input pl-8"
                placeholder="Name, brand, chemistry..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
          <div>
            <label className="label">Chemistry</label>
            <select
              className="input mt-1"
              value={chemistryFilter}
              onChange={(e) => setChemistryFilter(e.target.value)}
            >
              <option value="">All</option>
              {(chemistries || []).map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Brand</label>
            <select
              className="input mt-1"
              value={brandFilter}
              onChange={(e) => setBrandFilter(e.target.value)}
            >
              <option value="">All</option>
              {(brands || []).map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Results */}
      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Database size={24} />}
          title="No columns found"
          description="Try adjusting your filters"
        />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Table */}
          <div className="lg:col-span-2">
            <div className="card-scientific overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Brand</th>
                    <th>Name</th>
                    <th>Chemistry</th>
                    <th>Particle</th>
                    <th>Length</th>
                    <th>pH Range</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((c) => (
                    <tr
                      key={c.id}
                      onClick={() => setSelectedId(c.id)}
                      className="cursor-pointer"
                      style={selectedId === c.id ? { background: 'hsl(var(--muted))' } : undefined}
                    >
                      <td className="font-medium">{c.brand}</td>
                      <td>{c.name}</td>
                      <td>
                        <span className="badge badge-info">{c.chemistry}</span>
                      </td>
                      <td>{c.particle_size_um}µm</td>
                      <td>{c.length_mm}mm</td>
                      <td>{c.ph_min}–{c.ph_max}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Detail panel */}
          <div>
            {selected ? (
              <div className="card-scientific sticky top-20">
                <h3 className="text-sm font-bold">{selected.brand} {selected.name}</h3>
                <span className="badge badge-info mt-1">{selected.chemistry}</span>

                <div className="mt-4 space-y-2 text-xs">
                  <DetailRow label="Particle Size" value={`${selected.particle_size_um} µm`} />
                  <DetailRow label="Length" value={`${selected.length_mm} mm`} />
                  <DetailRow label="Inner Diameter" value={`${selected.inner_diameter_mm} mm`} />
                  <DetailRow label="pH Range" value={`${selected.ph_min} – ${selected.ph_max}`} />
                  <DetailRow label="Max Temperature" value={`${selected.temperature_max_c} °C`} />
                  <DetailRow label="USP Code" value={selected.usp_code || '—'} />
                </div>

                {/* pH range bar */}
                <div className="mt-4">
                  <p className="mb-1 text-xs font-medium">pH Stability Range</p>
                  <div className="relative h-3 rounded-full bg-muted">
                    <div
                      className="absolute h-3 rounded-full bg-success"
                      style={{
                        left: `${(selected.ph_min / 14) * 100}%`,
                        right: `${((14 - selected.ph_max) / 14) * 100}%`,
                      }}
                    />
                  </div>
                  <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
                    <span>0</span><span>7</span><span>14</span>
                  </div>
                </div>

                {selected.notes && (
                  <p className="mt-4 text-xs text-muted-foreground">{selected.notes}</p>
                )}
              </div>
            ) : (
              <div className="card-scientific py-8 text-center text-sm text-muted-foreground">
                Select a column to view details
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-border pb-1 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
