import type { Compound, DescriptorInfo } from '@/types';

interface PropertyPanelProps {
  compound: Compound | null;
  descriptors?: DescriptorInfo | null;
  loading?: boolean;
}

function PropertyRow({ label, value, unit }: { label: string; value: string | number | null | undefined; unit?: string }) {
  return (
    <div className="flex justify-between border-b border-border py-1.5 text-sm last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium tabular-nums">
        {value !== null && value !== undefined ? value : '—'}
        {unit && value !== null && value !== undefined ? ` ${unit}` : ''}
      </span>
    </div>
  );
}

export function PropertyPanel({ compound, descriptors, loading }: PropertyPanelProps) {
  if (loading) {
    return (
      <div className="card animate-pulse">
        <div className="h-4 w-24 rounded bg-muted" />
        <div className="mt-3 space-y-2">
          {[...Array(7)].map((_, i) => (
            <div key={i} className="h-3 w-full rounded bg-muted" />
          ))}
        </div>
      </div>
    );
  }

  if (!compound && !descriptors) {
    return (
      <div className="card text-sm text-muted-foreground">
        Enter a structure to see calculated properties.
      </div>
    );
  }

  const d = descriptors;
  const c = compound;

  return (
    <div className="card">
      <h3 className="text-sm font-semibold">Properties</h3>
      <div className="mt-2">
        <PropertyRow label="MW" value={d?.mw ?? c?.mw} unit="g/mol" />
        <PropertyRow label="logP" value={d?.logp ?? c?.logp} />
        <PropertyRow label="TPSA" value={d?.tpsa ?? c?.tpsa} unit="Å²" />
        <PropertyRow label="HBD" value={d?.hbd ?? c?.hbd} />
        <PropertyRow label="HBA" value={d?.hba ?? c?.hba} />
        <PropertyRow label="Rotatable bonds" value={d?.rotatable_bonds ?? c?.rotatable_bonds} />
        <PropertyRow label="Aromatic rings" value={d?.aromatic_rings ?? c?.aromatic_rings} />
        {c?.pka_values && c.pka_values.length > 0 && (
          <PropertyRow label="pKa (est.)" value={c.pka_values.join(', ')} />
        )}
      </div>
    </div>
  );
}
