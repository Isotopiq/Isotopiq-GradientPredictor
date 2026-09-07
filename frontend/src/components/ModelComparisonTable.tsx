import { useState } from 'react';
import { ChevronDown, ChevronRight, Zap, BarChart3 } from 'lucide-react';
import type { ModelComparisonEntry } from '@/types';

interface Props {
  comparison: ModelComparisonEntry[];
  loading?: boolean;
  onModelSelect?: (modelKey: string) => void;
}

export function ModelComparisonTable({ comparison, loading, onModelSelect }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (loading) {
    return (
      <div className="card-scientific">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-accent animate-pulse" />
          <h3 className="text-sm font-semibold">Model Comparison</h3>
          <span className="text-[10px] text-muted-foreground">computing...</span>
        </div>
      </div>
    );
  }

  if (!comparison || comparison.length === 0) {
    return null;
  }

  // Don't show the table if there's only one model (no comparison to make)
  if (comparison.length === 1) {
    return null;
  }

  const selectedEntry = comparison.find((c) => c.is_selected);

  return (
    <div className="card-scientific">
      {/* Collapsible header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 text-left"
      >
        {expanded ? (
          <ChevronDown size={14} className="text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight size={14} className="text-muted-foreground shrink-0" />
        )}
        <BarChart3 className="h-4 w-4 text-accent shrink-0" />
        <h3 className="text-sm font-semibold">Model Comparison</h3>
        <span className="text-[10px] text-muted-foreground">
          {comparison.length} models
        </span>
        {!expanded && selectedEntry && (
          <span className="ml-auto text-[10px] text-muted-foreground">
            Best: {selectedEntry.model_label}
          </span>
        )}
      </button>

      {expanded && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="py-1.5 pr-3">Model</th>
                <th className="py-1.5 pr-3">Equation</th>
                <th className="py-1.5 pr-3 text-right">Pred. RT</th>
                <th className="py-1.5 pr-3 text-right">Conf.</th>
                <th className="py-1.5 pr-2"></th>
              </tr>
            </thead>
            <tbody>
              {comparison.map((entry) => (
                <tr
                  key={entry.model_key}
                  onClick={() => onModelSelect?.(entry.model_key)}
                  className={`border-b border-border/50 cursor-pointer transition-colors ${
                    entry.is_selected
                      ? 'bg-accent/10'
                      : 'hover:bg-muted/30'
                  }`}
                >
                  <td className="py-1.5 pr-3 font-medium">
                    {entry.model_label}
                  </td>
                  <td className="py-1.5 pr-3 font-mono text-[10px] text-muted-foreground">
                    {entry.equation}
                  </td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">
                    {(entry.predicted_rt_s / 60).toFixed(2)} min
                  </td>
                  <td className="py-1.5 pr-3 text-right tabular-nums">
                    {Math.round(entry.confidence * 100)}%
                  </td>
                  <td className="py-1.5 pr-2">
                    {entry.is_selected && (
                      <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-accent">
                        <Zap size={10} />
                        Selected
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {onModelSelect && (
            <p className="mt-2 text-[10px] text-muted-foreground">
              Click a row to switch to that model.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
