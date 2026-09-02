import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GradientChart } from '@/components/GradientChart';

// Mock ResizeObserver for Recharts ResponsiveContainer
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;

// Mock getBoundingClientRect
Element.prototype.getBoundingClientRect = () => ({
  width: 400,
  height: 200,
  top: 0,
  left: 0,
  right: 400,
  bottom: 200,
  x: 0,
  y: 0,
  toJSON: () => {},
});

describe('GradientChart', () => {
  it('shows empty state when no data', () => {
    render(<GradientChart gradientTable={null} />);
    expect(screen.getByText(/gradient profile will appear/i)).toBeInTheDocument();
  });

  it('renders chart with gradient data', () => {
    const table = [
      { time_s: 0, percent_b: 5 },
      { time_s: 60, percent_b: 5 },
      { time_s: 1200, percent_b: 95 },
      { time_s: 1320, percent_b: 95 },
    ];
    const { container } = render(<GradientChart gradientTable={table} />);
    // Recharts renders an SVG
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });
});
