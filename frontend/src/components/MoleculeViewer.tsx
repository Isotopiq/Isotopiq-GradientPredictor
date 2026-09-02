import { useEffect, useState, useRef } from 'react';
import { useRDKit } from '@/hooks/useRDKit';
import { cn } from '@/lib/utils';

interface MoleculeViewerProps {
  smiles: string;
  width?: number;
  height?: number;
  className?: string;
}

export function MoleculeViewer({
  smiles,
  width = 300,
  height = 200,
  className,
}: MoleculeViewerProps) {
  const { rdkit, loading, error } = useRDKit();
  const [svg, setSvg] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!rdkit || !smiles) {
      setSvg(null);
      return;
    }
    try {
      const mol = rdkit.get_mol(smiles);
      if (!mol.is_valid()) {
        setSvg(null);
        mol.delete();
        return;
      }
      const svgStr = mol.get_svg(width, height);
      setSvg(svgStr);
      mol.delete();
    } catch {
      setSvg(null);
    }
  }, [rdkit, smiles, width, height]);

  if (loading) {
    return (
      <div
        className={cn('flex items-center justify-center rounded-md border border-border bg-muted/30', className)}
        style={{ width, height }}
      >
        <div className="text-xs text-muted-foreground">Loading RDKit...</div>
      </div>
    );
  }

  if (error || !svg) {
    return (
      <div
        className={cn('flex items-center justify-center rounded-md border border-dashed border-border', className)}
        style={{ width, height }}
      >
        <div className="text-center text-xs text-muted-foreground">
          {error ? 'RDKit failed to load' : smiles ? 'Invalid SMILES' : 'No structure'}
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn('flex items-center justify-center rounded-md border border-border bg-card', className)}
      style={{ width, height }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

/** Compact thumbnail version for tables/lists */
export function MoleculeThumbnail({ smiles, size = 48 }: { smiles: string; size?: number }) {
  return <MoleculeViewer smiles={smiles} width={size} height={size} className="shrink-0" />;
}
