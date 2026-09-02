import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Database, Search, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { columnsApi } from '@/api/columns';
import { EmptyState } from '@/components/EmptyState';
import { Skeleton } from '@/components/Skeleton';

const PAGE_SIZE = 25;

export function ColumnDatabasePage() {
  const [search, setSearch] = useState('');
  const [chemistryFilter, setChemistryFilter] = useState('');
  const [brandFilter, setBrandFilter] = useState('');
  const [particleFilter, setParticleFilter] = useState('');
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Debounce search
  const [debouncedSearch, setDebouncedSearch] = useState('');
  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(0);
    }, 300);
    return () => clearTimeout(t);
  }, [search]);

  const offset = page * PAGE_SIZE;

  const { data: result, isLoading } = useQuery({
    queryKey: ['columns', debouncedSearch, chemistryFilter, brandFilter, particleFilter, offset],
    queryFn: () =>
      columnsApi.list({
        search: debouncedSearch || undefined,
        chemistry: chemistryFilter || undefined,
        brand: brandFilter || undefined,
        particle_size: particleFilter ? parseFloat(particleFilter) : undefined,
        limit: PAGE_SIZE,
        offset,
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

  const columns = result?.columns || [];
  const total = result?.total || 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const selected = columns.find((c) => c.id === selectedId);

  const handleFilterChange = (setter: (v: string) => void) => (e: React.ChangeEvent<HTMLSelectElement>) => {
    setter(e.target.value);
    setPage(0);
  };

  return (
    <div className="mx-auto max-w-6xl p-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold">Commercial Column Database</h1>
        <p className="text-sm text-muted-foreground">
          Comprehensive database of {total > 0 ? total : '...'} LC column configurations from major manufacturers
        </p>
      </div>

      {/* Filters */}
      <div className="card-scientific mb-6">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
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
            <select className="input mt-1" value={chemistryFilter} onChange={handleFilterChange(setChemistryFilter)}>
              <option value="">All</option>
              {(chemistries || []).map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Brand</label>
            <select className="input mt-1" value={brandFilter} onChange={handleFilterChange(setBrandFilter)}>
              <option value="">All</option>
              {(brands || []).map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Particle Size</label>
            <select className="input mt-1" value={particleFilter} onChange={handleFilterChange(setParticleFilter)}>
              <option value="">All</option>
              <option value="1.5">1.5 µm</option>
              <option value="1.6">1.6 µm</option>
              <option value="1.7">1.7 µm</option>
              <option value="1.8">1.8 µm</option>
              <option value="1.9">1.9 µm</option>
              <option value="2.2">2.2 µm</option>
              <option value="2.6">2.6 µm</option>
              <option value="2.7">2.7 µm</option>
              <option value="3.0">3.0 µm</option>
              <option value="3.5">3.5 µm</option>
              <option value="4.0">4.0 µm</option>
              <option value="5.0">5.0 µm</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results */}
      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : columns.length === 0 ? (
        <EmptyState
          icon={<Database size={24} />}
          title="No columns found"
          description="Try adjusting your filters"
        />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Table + pagination */}
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
                    <th>ID</th>
                    <th>%C</th>
                    <th>pH</th>
                  </tr>
                </thead>
                <tbody>
                  {columns.map((c) => (
                    <tr
                      key={c.id}
                      onClick={() => setSelectedId(c.id)}
                      className="cursor-pointer"
                      style={selectedId === c.id ? { background: 'hsl(var(--muted))' } : undefined}
                    >
                      <td className="font-medium">{c.brand}</td>
                      <td className="max-w-[200px] truncate">{c.name}</td>
                      <td>
                        <span className="badge badge-info">{c.chemistry}</span>
                      </td>
                      <td>{c.particle_size_um}µm</td>
                      <td>{c.length_mm}mm</td>
                      <td>{c.inner_diameter_mm}mm</td>
                      <td className="text-muted-foreground">{c.stationary_phase?.carbon_load_pct ?? '—'}</td>
                      <td className="whitespace-nowrap">{c.ph_min}–{c.ph_max}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="mt-4 flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                Showing {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
              </p>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setPage(0)}
                  disabled={page === 0}
                  className="btn-ghost btn-sm p-1.5 disabled:opacity-30"
                  title="First page"
                >
                  <ChevronsLeft size={14} />
                </button>
                <button
                  type="button"
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="btn-ghost btn-sm p-1.5 disabled:opacity-30"
                  title="Previous page"
                >
                  <ChevronLeft size={14} />
                </button>
                <span className="px-3 text-xs font-medium">
                  Page {page + 1} of {totalPages || 1}
                </span>
                <button
                  type="button"
                  onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  className="btn-ghost btn-sm p-1.5 disabled:opacity-30"
                  title="Next page"
                >
                  <ChevronRight size={14} />
                </button>
                <button
                  type="button"
                  onClick={() => setPage(totalPages - 1)}
                  disabled={page >= totalPages - 1}
                  className="btn-ghost btn-sm p-1.5 disabled:opacity-30"
                  title="Last page"
                >
                  <ChevronsRight size={14} />
                </button>
              </div>
            </div>
          </div>

          {/* Detail panel */}
          <div>
            {selected ? (
              <div className="card-scientific sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto">
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

                {/* Stationary phase composition */}
                {selected.stationary_phase && (
                  <div className="mt-4 border-t border-border pt-3">
                    <p className="mb-2 text-xs font-bold">Stationary Phase Composition</p>
                    <div className="space-y-1.5 text-xs">
                      <DetailRow label="Carbon Load" value={`${selected.stationary_phase.carbon_load_pct}%`} />
                      <DetailRow label="Ligand Length" value={selected.stationary_phase.ligand_length > 0 ? `C${selected.stationary_phase.ligand_length}` : '—'} />
                      <DetailRow label="Bonding Density" value={`${selected.stationary_phase.bonding_density_umol_m2} µmol/m²`} />
                      <DetailRow label="Surface Area" value={`${selected.stationary_phase.surface_area_m2_g} m²/g`} />
                      <DetailRow label="Pore Size" value={`${selected.stationary_phase.pore_size_a} Å`} />
                      <DetailRow label="Endcapped" value={selected.stationary_phase.endcapped ? 'Yes' : 'No'} />
                      <DetailRow label="Polar Embedded" value={selected.stationary_phase.polar_embedded ? 'Yes' : 'No'} />
                      <DetailRow label="Particle Type" value={selected.stationary_phase.particle_type.replace('_', ' ')} />
                      <DetailRow label="Base Material" value={selected.stationary_phase.base_material.replace('_', ' ')} />
                      <DetailRow label="Hydrophobicity Index" value={selected.stationary_phase.hydrophobicity_index.toFixed(2)} />
                    </div>
                  </div>
                )}

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
