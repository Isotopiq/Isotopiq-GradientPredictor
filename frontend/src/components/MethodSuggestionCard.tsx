import { AlertTriangle, FlaskConical, Droplet, Beaker } from 'lucide-react';
import type { MethodSuggestion } from '@/types';

interface MethodSuggestionCardProps {
  suggestion: MethodSuggestion | null;
  loading?: boolean;
}

export function MethodSuggestionCard({ suggestion, loading }: MethodSuggestionCardProps) {
  if (loading) {
    return (
      <div className="card animate-pulse">
        <div className="h-4 w-32 rounded bg-muted" />
        <div className="mt-3 space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 w-full rounded bg-muted" />
          ))}
        </div>
      </div>
    );
  }

  if (!suggestion) {
    return (
      <div className="card text-sm text-muted-foreground">
        Method suggestion will appear here after structure input.
      </div>
    );
  }

  const { column, ph, additive } = suggestion;

  return (
    <div className="card space-y-3">
      <h3 className="text-sm font-semibold">Method Suggestion</h3>

      {/* Column */}
      <div className="rounded-md border border-border p-3">
        <div className="flex items-center gap-2">
          <FlaskConical size={14} className="text-accent" />
          <span className="text-xs font-medium text-muted-foreground">Column</span>
        </div>
        <p className="mt-1 text-base font-semibold">{column.column_type}</p>
        <p className="mt-1 text-xs text-muted-foreground">{column.rationale}</p>
        {column.alternatives.length > 0 && (
          <p className="mt-1 text-xs text-muted-foreground">
            Alternatives: {column.alternatives.join(', ')}
          </p>
        )}
      </div>

      {/* pH */}
      <div className="rounded-md border border-border p-3">
        <div className="flex items-center gap-2">
          <Droplet size={14} className="text-accent" />
          <span className="text-xs font-medium text-muted-foreground">Mobile Phase pH</span>
        </div>
        <p className="mt-1 text-base font-semibold tabular-nums">{ph.recommended_ph}</p>
        <p className="mt-1 text-xs text-muted-foreground">{ph.rationale}</p>
        {ph.warning_zones.length > 0 && (
          <div className="mt-2 flex items-start gap-1.5 rounded bg-warning/10 p-2 text-xs text-warning">
            <AlertTriangle size={12} className="mt-0.5 shrink-0" />
            <span>
              Avoid pH{' '}
              {ph.warning_zones.map(([lo, hi]) => `${lo}–${hi}`).join(', ')} (near pKa — poor peak shape)
            </span>
          </div>
        )}
      </div>

      {/* Additive */}
      <div className="rounded-md border border-border p-3">
        <div className="flex items-center gap-2">
          <Beaker size={14} className="text-accent" />
          <span className="text-xs font-medium text-muted-foreground">Additive</span>
        </div>
        <p className="mt-1 text-sm font-semibold">{additive.additive}</p>
        <p className="mt-1 text-xs text-muted-foreground">{additive.rationale}</p>
        {additive.alternatives.length > 0 && (
          <p className="mt-1 text-xs text-muted-foreground">
            Alternatives: {additive.alternatives.join(', ')}
          </p>
        )}
      </div>
    </div>
  );
}
