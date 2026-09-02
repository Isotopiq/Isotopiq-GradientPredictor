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
  const [renderError, setRenderError] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!rdkit || !smiles) {
      setSvg(null);
      setRenderError(false);
      return;
    }
    try {
      const mol = rdkit.get_mol(smiles);
      if (!mol.is_valid()) {
        setSvg(null);
        setRenderError(true);
        mol.delete();
        return;
      }
      const svgStr = mol.get_svg(width, height);
      setSvg(svgStr);
      setRenderError(false);
      mol.delete();
    } catch {
      setSvg(null);
      setRenderError(true);
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

  // If RDKit failed to load or the molecule couldn't be rendered,
  // show a graceful fallback with the SMILES string instead of crashing.
  if (error || renderError || !svg) {
    return (
      <div
        className={cn('flex flex-col items-center justify-center rounded-md border border-dashed border-border p-2', className)}
        style={{ width, height }}
      >
        <div className="text-center text-xs text-muted-foreground">
          {error ? 'RDKit unavailable' : smiles ? 'Cannot render structure' : 'No structure'}
        </div>
        {smiles && (
          <div className="mt-1 max-w-full overflow-hidden text-[10px] font-mono text-muted-foreground/70 break-all">
            {smiles.length > 60 ? smiles.slice(0, 57) + '...' : smiles}
          </div>
        )}
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
