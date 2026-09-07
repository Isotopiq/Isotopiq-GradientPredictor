import { Atom, Info, AlertTriangle, CheckCircle2, Zap, BookOpen } from 'lucide-react';

export interface ModelInfo {
  mechanism?: string;
  mechanismLabel?: string;
  modelLabel?: string;
  modelEquation?: string;
  modelReference?: string;
  modelRationale?: string;
  modelRequires?: string;
  confidence?: number;
  extrapolating?: boolean;
}

interface Props {
  info: ModelInfo | null;
  loading?: boolean;
}

export function ModelInfoCard({ info, loading }: Props) {
  if (loading) {
    return (
      <div className="card-scientific">
        <div className="flex items-center gap-2">
          <Atom className="h-4 w-4 text-accent animate-pulse" />
          <h3 className="text-sm font-semibold">Retention Model</h3>
          <span className="text-[10px] text-muted-foreground">computing...</span>
        </div>
      </div>
    );
  }

  if (!info || !info.modelLabel) {
    return (
      <div className="card-scientific">
        <div className="flex items-center gap-2">
          <Atom className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold text-muted-foreground">Retention Model</h3>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          Run a prediction to see which retention model was used.
        </p>
      </div>
    );
  }

  const confidence = info.confidence;
  const confidencePct = confidence != null ? Math.round(confidence * 100) : null;
  const confidenceColor =
    confidencePct != null
      ? confidencePct >= 70
        ? 'hsl(var(--success))'
        : confidencePct >= 40
          ? 'hsl(var(--warning))'
          : 'hsl(var(--destructive))'
      : null;

  return (
    <div className="card-scientific">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Atom className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold">Retention Model</h3>
        <span className="badge badge-info text-[10px]">
          {info.mechanismLabel || info.mechanism || '—'}
        </span>
      </div>

      {/* Model name + auto-selected badge */}
      <div className="mt-2 flex items-center gap-2">
        <Zap size={12} className="text-accent shrink-0" />
        <span className="text-xs font-medium">{info.modelLabel}</span>
      </div>

      {/* Equation */}
      {info.modelEquation && (
        <div className="mt-2 rounded-md bg-muted/40 px-2 py-1.5">
          <p className="font-mono text-[11px] text-foreground">{info.modelEquation}</p>
        </div>
      )}

      {/* Rationale */}
      {info.modelRationale && (
        <p className="mt-2 text-[11px] text-muted-foreground">
          <Info size={10} className="inline mr-1" />
          {info.modelRationale}
        </p>
      )}

      {/* Requires + reference */}
      <div className="mt-1.5 space-y-0.5">
        {info.modelRequires && (
          <p className="text-[10px] text-muted-foreground">
            <CheckCircle2 size={10} className="inline mr-1 text-green-500" />
            Requires: {info.modelRequires}
          </p>
        )}
        {info.modelReference && (
          <p className="text-[10px] text-muted-foreground">
            <BookOpen size={10} className="inline mr-1" />
            {info.modelReference}
          </p>
        )}
      </div>

      {/* Confidence bar */}
      {confidencePct != null && (
        <div className="mt-2 flex items-center gap-2">
          <span className="text-[10px] text-muted-foreground shrink-0">Confidence</span>
          <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${confidencePct}%`, backgroundColor: confidenceColor ?? undefined }}
            />
          </div>
          <span className="text-[10px] tabular-nums text-muted-foreground">{confidencePct}%</span>
          {info.extrapolating && (
            <span className="badge badge-warning text-[9px]">
              <AlertTriangle size={9} className="mr-0.5" />
              Extrapolating
            </span>
          )}
        </div>
      )}
    </div>
  );
}
