import { useState } from 'react';
import { CheckCircle2, XCircle, SlidersHorizontal } from 'lucide-react';
import type { SuitabilityCriteria, SuitabilityEvaluation } from '@/types';

interface Props {
  criteria: SuitabilityCriteria;
  onCriteriaChange: (c: SuitabilityCriteria) => void;
  evaluation: SuitabilityEvaluation | null;
}

export function SuitabilityCriteriaPanel({ criteria, onCriteriaChange, evaluation }: Props) {
  const [expanded, setExpanded] = useState(false);

  const update = (field: keyof SuitabilityCriteria, value: number) => {
    onCriteriaChange({ ...criteria, [field]: value });
  };

  return (
    <div className="card-scientific">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 text-left"
      >
        <SlidersHorizontal className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold">Suitability Criteria</h3>
        {evaluation && (
          <span className={`badge text-[10px] ${evaluation.all_passed ? 'badge-success' : 'badge-warning'}`}>
            Score: {(evaluation.overall_score * 100).toFixed(0)}%
          </span>
        )}
        <span className="ml-auto text-xs text-muted-foreground">{expanded ? '▼' : '▶'}</span>
      </button>

      {expanded && (
        <div className="mt-3 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs text-muted-foreground">Min Resolution (Rs)</span>
              <input
                type="number"
                step="0.1"
                min="0"
                value={criteria.min_resolution}
                onChange={(e) => update('min_resolution', parseFloat(e.target.value) || 0)}
                className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
              />
            </label>
            <label className="block">
              <span className="text-xs text-muted-foreground">Max Run Time (min)</span>
              <input
                type="number"
                step="1"
                min="1"
                value={criteria.max_run_time_min}
                onChange={(e) => update('max_run_time_min', parseFloat(e.target.value) || 0)}
                className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
              />
            </label>
            <label className="block">
              <span className="text-xs text-muted-foreground">Min k (retention factor)</span>
              <input
                type="number"
                step="0.1"
                min="0"
                value={criteria.min_k}
                onChange={(e) => update('min_k', parseFloat(e.target.value) || 0)}
                className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
              />
            </label>
            <label className="block">
              <span className="text-xs text-muted-foreground">Max k (retention factor)</span>
              <input
                type="number"
                step="1"
                min="1"
                value={criteria.max_k}
                onChange={(e) => update('max_k', parseFloat(e.target.value) || 0)}
                className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
              />
            </label>
          </div>

          {evaluation && (
            <div className="mt-3 space-y-1">
              <h4 className="text-xs font-semibold text-muted-foreground">Evaluation</h4>
              {evaluation.criteria.map((c) => (
                <div key={c.name} className="flex items-center gap-2 text-xs">
                  {c.passed ? (
                    <CheckCircle2 className="h-3 w-3 text-green-500" />
                  ) : (
                    <XCircle className="h-3 w-3 text-red-500" />
                  )}
                  <span className="font-medium">{c.name}</span>
                  <span className="text-muted-foreground">{c.detail}</span>
                  <span className="ml-auto text-muted-foreground">Target: {c.target}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
