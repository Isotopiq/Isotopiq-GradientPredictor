import { X, FlaskConical, Share2, ExternalLink } from 'lucide-react';
import { MoleculeViewer } from '@/components/MoleculeViewer';
import type { Compound } from '@/types';

interface CompoundDetailModalProps {
  compound: Compound | null;
  onClose: () => void;
  onUseInPredictor?: (compound: Compound) => void;
}

export function CompoundDetailModal({ compound, onClose, onUseInPredictor }: CompoundDetailModalProps) {
  if (!compound) return null;

  const properties = [
    { label: 'Molecular Weight', value: compound.mw?.toFixed(2), unit: 'g/mol' },
    { label: 'logP', value: compound.logp?.toFixed(2), unit: '' },
    { label: 'TPSA', value: compound.tpsa?.toFixed(1), unit: 'Å²' },
    { label: 'H-Bond Donors', value: compound.hbd?.toString(), unit: '' },
    { label: 'H-Bond Acceptors', value: compound.hba?.toString(), unit: '' },
    { label: 'Rotatable Bonds', value: compound.rotatable_bonds?.toString(), unit: '' },
    { label: 'Aromatic Rings', value: compound.aromatic_rings?.toString(), unit: '' },
    { label: 'logD (at pH)', value: compound.logd_at_ph?.toFixed(2), unit: '' },
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-border bg-card shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border p-4">
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-lg font-bold">
              {compound.name || 'Unnamed Compound'}
            </h2>
            {compound.cas && (
              <p className="text-xs text-muted-foreground">CAS: {compound.cas}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-2">
          {/* Structure */}
          <div>
            <label className="label">Structure</label>
            <MoleculeViewer
              smiles={compound.smiles || ''}
              width={400}
              height={300}
              autoFit
              className="mt-1 h-[300px] w-full"
            />
          </div>

          {/* Properties */}
          <div className="space-y-2">
            <label className="label">Physicochemical Properties</label>
            <div className="rounded-md border border-border">
              {properties.map((prop, i) => (
                <div
                  key={i}
                  className={`flex items-center justify-between px-3 py-1.5 text-xs ${
                    i < properties.length - 1 ? 'border-b border-border' : ''
                  }`}
                >
                  <span className="text-muted-foreground">{prop.label}</span>
                  <span className="tabular-nums font-medium">
                    {prop.value ?? '—'} {prop.unit && prop.value && <span className="text-muted-foreground">{prop.unit}</span>}
                  </span>
                </div>
              ))}
            </div>

            {compound.pka_values && compound.pka_values.length > 0 && (
              <div>
                <label className="label">pKa Values (estimated)</label>
                <div className="flex flex-wrap gap-1.5">
                  {compound.pka_values.map((pka, i) => (
                    <span key={i} className="badge badge-warning text-xs tabular-nums">
                      {pka.toFixed(1)}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* SMILES */}
          <div className="md:col-span-2">
            <label className="label">SMILES</label>
            <div className="mt-1 rounded-md border border-border bg-muted/30 p-2">
              <p className="break-all font-mono text-xs">{compound.smiles || '—'}</p>
            </div>
          </div>

          {/* InChI if available */}
          {compound.inchi && (
            <div className="md:col-span-2">
              <label className="label">InChI</label>
              <div className="mt-1 rounded-md border border-border bg-muted/30 p-2">
                <p className="break-all font-mono text-xs">{compound.inchi}</p>
              </div>
            </div>
          )}

          {/* Source */}
          {compound.source && (
            <div className="md:col-span-2 flex items-center gap-2 text-xs text-muted-foreground">
              <span>Source: {compound.source}</span>
              {compound.is_shared && (
                <span className="badge badge-success text-[10px]">
                  <Share2 size={8} className="mr-0.5" /> Shared
                </span>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-border p-4">
          {onUseInPredictor && (
            <button
              onClick={() => {
                onUseInPredictor(compound);
                onClose();
              }}
              className="btn-primary btn-sm"
            >
              <FlaskConical size={14} /> Use in Predictor
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
