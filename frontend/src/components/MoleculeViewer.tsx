import { useEffect, useState, useRef, useCallback } from 'react';
import { useRDKit } from '@/hooks/useRDKit';
import { cn } from '@/lib/utils';

interface MoleculeViewerProps {
  smiles: string;
  width?: number;
  height?: number;
  className?: string;
  /** When true, the SVG fills the container while preserving aspect ratio */
  autoFit?: boolean;
}

export function MoleculeViewer({
  smiles,
  width = 300,
  height = 200,
  className,
  autoFit = false,
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
      // Use RDKit's built-in SVG generation with the specified dimensions
      // For autoFit, render at a larger internal resolution so the molecule
      // doesn't look squished when scaled down by CSS
      const renderW = autoFit ? Math.max(width, 250) : width;
      const renderH = autoFit ? Math.max(height, 250) : height;
      const svgStr = mol.get_svg(renderW, renderH);
      setSvg(svgStr);
      setRenderError(false);
      mol.delete();
    } catch {
      setSvg(null);
      setRenderError(true);
    }
  }, [rdkit, smiles, width, height, autoFit]);

  if (loading) {
    return (
      <div
        className={cn('flex items-center justify-center rounded-md border border-border bg-muted/30', className)}
        style={autoFit ? undefined : { width, height }}
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
        style={autoFit ? undefined : { width, height }}
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

  // For autoFit mode, make the SVG responsive — it will scale to fit the container
  // while preserving aspect ratio via the SVG's viewBox
  const responsiveSvg = autoFit
    ? svg.replace(/width="(\d+)"/, 'width="100%"').replace(/height="(\d+)"/, 'height="100%"')
    : svg;

  return (
    <div
      ref={containerRef}
      className={cn('flex items-center justify-center rounded-md border border-border bg-card overflow-hidden', className)}
      style={autoFit ? undefined : { width, height }}
      dangerouslySetInnerHTML={{ __html: responsiveSvg }}
    />
  );
}

/**
 * Compact thumbnail version for tables/lists.
 * Renders at a higher internal resolution and scales down via CSS
 * so large molecules don't look squished.
 */
export function MoleculeThumbnail({
  smiles,
  size = 56,
  onClick,
  className,
}: {
  smiles: string;
  size?: number;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'shrink-0',
        onClick && 'cursor-pointer hover:ring-2 hover:ring-accent/40 transition-all',
        className,
      )}
      style={{ width: size, height: size }}
      title={onClick ? 'Click to view details' : undefined}
    >
      <MoleculeViewer
        smiles={smiles}
        width={size}
        height={size}
        autoFit
        className="h-full w-full"
      />
    </div>
  );
}
