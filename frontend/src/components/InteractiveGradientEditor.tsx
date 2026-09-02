import { useState, useRef, useCallback, useEffect } from 'react';
import { Plus, Trash2, GripVertical } from 'lucide-react';
import type { GradientPoint } from '@/types';
import { cn } from '@/lib/utils';

interface InteractiveGradientEditorProps {
  points: GradientPoint[];
  onChange: (points: GradientPoint[]) => void;
  maxTimeS?: number;
  maxPercentB?: number;
}

export function InteractiveGradientEditor({
  points,
  onChange,
  maxTimeS = 1800,
  maxPercentB = 100,
}: InteractiveGradientEditorProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [draggingIdx, setDraggingIdx] = useState<number | null>(null);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  const width = 600;
  const height = 280;
  const padding = { top: 20, right: 40, bottom: 40, left: 50 };
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;

  const sortedPoints = [...points].sort((a, b) => a.time_s - b.time_s);

  const xScale = (timeS: number) => padding.left + (timeS / maxTimeS) * plotW;
  const yScale = (pctB: number) => padding.top + plotH - (pctB / maxPercentB) * plotH;

  const invXScale = (px: number) => {
    const val = ((px - padding.left) / plotW) * maxTimeS;
    return Math.max(0, Math.min(maxTimeS, Math.round(val)));
  };
  const invYScale = (py: number) => {
    const val = ((padding.top + plotH - py) / plotH) * maxPercentB;
    return Math.max(0, Math.min(maxPercentB, Math.round(val * 10) / 10));
  };

  const handlePointerDown = (e: React.PointerEvent, idx: number) => {
    e.preventDefault();
    e.stopPropagation();
    setDraggingIdx(idx);
    setSelectedIdx(idx);
    (e.target as Element).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (draggingIdx === null || !svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const scaleX = width / rect.width;
      const scaleY = height / rect.height;
      const px = (e.clientX - rect.left) * scaleX;
      const py = (e.clientY - rect.top) * scaleY;

      const newTime = invXScale(px);
      const newPctB = invYScale(py);

      const updated = [...sortedPoints];
      updated[draggingIdx] = {
        time_s: newTime,
        percent_b: newPctB,
      };

      // Keep first point at time 0 and last point at max time
      if (draggingIdx === 0) updated[0] = { ...updated[0], time_s: 0 };
      if (draggingIdx === updated.length - 1) {
        updated[draggingIdx] = { ...updated[draggingIdx], time_s: maxTimeS };
      }

      // Re-sort and update
      updated.sort((a, b) => a.time_s - b.time_s);
      onChange(updated);
    },
    [draggingIdx, sortedPoints, onChange, maxTimeS],
  );

  const handlePointerUp = () => {
    setDraggingIdx(null);
  };

  const addPoint = (e: React.MouseEvent) => {
    if (!svgRef.current) return;
    if (draggingIdx !== null) return;
    const rect = svgRef.current.getBoundingClientRect();
    const scaleX = width / rect.width;
    const scaleY = height / rect.height;
    const px = (e.clientX - rect.left) * scaleX;
    const py = (e.clientY - rect.top) * scaleY;

    // Only add if click is within plot area
    if (px < padding.left || px > width - padding.right) return;
    if (py < padding.top || py > height - padding.bottom) return;

    const newTime = invXScale(px);
    const newPctB = invYScale(py);
    const updated = [...sortedPoints, { time_s: newTime, percent_b: newPctB }];
    updated.sort((a, b) => a.time_s - b.time_s);
    onChange(updated);
  };

  const deletePoint = (idx: number) => {
    if (sortedPoints.length <= 2) return; // Keep at least 2 points
    const updated = sortedPoints.filter((_, i) => i !== idx);
    onChange(updated);
    setSelectedIdx(null);
  };

  // Build gradient path
  const pathD = sortedPoints
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(p.time_s)} ${yScale(p.percent_b)}`)
    .join(' ');

  // Fill area under gradient
  const fillD = `${pathD} L ${xScale(sortedPoints[sortedPoints.length - 1]?.time_s || 0)} ${yScale(0)} L ${xScale(sortedPoints[0]?.time_s || 0)} ${yScale(0)} Z`;

  return (
    <div className="card-scientific">
      <div className="section-header mb-3">
        <div>
          <h2>Interactive Gradient Editor</h2>
          <p>Drag waypoints to adjust • Click on plot to add • Right-click point to delete</p>
        </div>
        <div className="flex gap-2">
          <button
            className="btn-outline btn-sm"
            onClick={() => onChange([{ time_s: 0, percent_b: 5 }, { time_s: maxTimeS, percent_b: 95 }])}
          >
            Reset
          </button>
        </div>
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${width} ${height}`}
        className="w-full cursor-crosshair touch-none"
        onClick={addPoint}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
      >
        {/* Grid */}
        {[0, 25, 50, 75, 100].map((pct) => (
          <g key={`grid-${pct}`}>
            <line
              x1={padding.left}
              y1={yScale(pct)}
              x2={width - padding.right}
              y2={yScale(pct)}
              stroke="hsl(var(--border))"
              strokeDasharray="3 3"
            />
            <text
              x={padding.left - 8}
              y={yScale(pct) + 4}
              textAnchor="end"
              fontSize="10"
              fill="hsl(var(--muted-foreground))"
            >
              {pct}%
            </text>
          </g>
        ))}

        {[0, 5, 10, 15, 20, 25, 30].map((t) => {
          const timeS = t * 60;
          if (timeS > maxTimeS) return null;
          return (
            <g key={`grid-t-${t}`}>
              <line
                x1={xScale(timeS)}
                y1={padding.top}
                x2={xScale(timeS)}
                y2={height - padding.bottom}
                stroke="hsl(var(--border))"
                strokeDasharray="3 3"
              />
              <text
                x={xScale(timeS)}
                y={height - padding.bottom + 16}
                textAnchor="middle"
                fontSize="10"
                fill="hsl(var(--muted-foreground))"
              >
                {t}m
              </text>
            </g>
          );
        })}

        {/* Axis labels */}
        <text
          x={width / 2}
          y={height - 4}
          textAnchor="middle"
          fontSize="11"
          fill="hsl(var(--foreground))"
          fontWeight="500"
        >
          Time
        </text>
        <text
          x={14}
          y={height / 2}
          textAnchor="middle"
          fontSize="11"
          fill="hsl(var(--foreground))"
          fontWeight="500"
          transform={`rotate(-90, 14, ${height / 2})`}
        >
          %B
        </text>

        {/* Gradient fill */}
        <path d={fillD} fill="hsl(var(--chart-1))" fillOpacity={0.1} />

        {/* Gradient line */}
        <path
          d={pathD}
          fill="none"
          stroke="hsl(var(--chart-1))"
          strokeWidth={2.5}
          strokeLinejoin="round"
        />

        {/* Waypoints */}
        {sortedPoints.map((p, idx) => (
          <g
            key={`wp-${idx}`}
            onPointerDown={(e) => handlePointerDown(e, idx)}
            onContextMenu={(e) => {
              e.preventDefault();
              deletePoint(idx);
            }}
            className="cursor-grab active:cursor-grabbing"
          >
            {/* Hit area (larger, invisible) */}
            <circle
              cx={xScale(p.time_s)}
              cy={yScale(p.percent_b)}
              r={12}
              fill="transparent"
            />
            {/* Visible circle */}
            <circle
              cx={xScale(p.time_s)}
              cy={yScale(p.percent_b)}
              r={selectedIdx === idx ? 7 : 5}
              fill={selectedIdx === idx ? 'hsl(var(--accent))' : 'hsl(var(--card))'}
              stroke="hsl(var(--accent))"
              strokeWidth={2}
            />
            {/* Label */}
            <text
              x={xScale(p.time_s)}
              y={yScale(p.percent_b) - 12}
              textAnchor="middle"
              fontSize="10"
              fill="hsl(var(--foreground))"
              fontWeight="600"
              pointerEvents="none"
            >
              {p.percent_b.toFixed(0)}%
            </text>
          </g>
        ))}
      </svg>

      {/* Gradient table */}
      <div className="mt-3 overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Time (min)</th>
              <th>%B</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sortedPoints.map((p, idx) => (
              <tr
                key={idx}
                className={cn(selectedIdx === idx && 'bg-muted')}
                onClick={() => setSelectedIdx(idx)}
              >
                <td className="text-muted-foreground">{idx + 1}</td>
                <td>{(p.time_s / 60).toFixed(2)}</td>
                <td>{p.percent_b.toFixed(1)}%</td>
                <td>
                  {sortedPoints.length > 2 && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deletePoint(idx);
                      }}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
