import { useState } from 'react';
import { Download, X, Loader2 } from 'lucide-react';

export interface ExportSection {
  key: string;
  label: string;
  default: boolean;
}

interface ExportDialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  sections: ExportSection[];
  onExport: (selected: Record<string, boolean>) => Promise<void>;
}

export function ExportDialog({ open, onClose, title, sections, onExport }: ExportDialogProps) {
  const [selected, setSelected] = useState<Record<string, boolean>>(
    () => Object.fromEntries(sections.map((s) => [s.key, s.default])),
  );
  const [exporting, setExporting] = useState(false);

  if (!open) return null;

  const toggle = (key: string) => {
    setSelected((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const selectAll = () => {
    setSelected(Object.fromEntries(sections.map((s) => [s.key, true])));
  };

  const deselectAll = () => {
    setSelected(Object.fromEntries(sections.map((s) => [s.key, false])));
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await onExport(selected);
      onClose();
    } catch {
      // Error handling is done by the caller (toast)
    } finally {
      setExporting(false);
    }
  };

  const selectedCount = Object.values(selected).filter(Boolean).length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 animate-fade-in" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-2xl animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold">{title}</h2>
          <button onClick={onClose} className="rounded-md p-1 text-muted-foreground hover:bg-muted">
            <X size={16} />
          </button>
        </div>

        <p className="mb-3 text-sm text-muted-foreground">Select sections to include:</p>

        <div className="mb-3 flex gap-2">
          <button onClick={selectAll} className="btn-outline btn-xs">Select All</button>
          <button onClick={deselectAll} className="btn-outline btn-xs">Deselect All</button>
        </div>

        <div className="max-h-64 space-y-1 overflow-y-auto">
          {sections.map((section) => (
            <label
              key={section.key}
              className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-2 hover:bg-muted"
            >
              <input
                type="checkbox"
                checked={selected[section.key] ?? false}
                onChange={() => toggle(section.key)}
                className="h-4 w-4 rounded border-border accent-[hsl(var(--accent))]"
              />
              <span className="text-sm">{section.label}</span>
            </label>
          ))}
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="btn-outline btn-sm">
            Cancel
          </button>
          <button
            onClick={handleExport}
            disabled={exporting || selectedCount === 0}
            className="btn-primary btn-sm"
          >
            {exporting ? (
              <><Loader2 size={14} className="mr-1 animate-spin" /> Generating...</>
            ) : (
              <><Download size={14} className="mr-1" /> Export PDF</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
