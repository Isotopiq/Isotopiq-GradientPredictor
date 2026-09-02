import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from '@/context/ThemeContext';
import { ThemeToggle } from '@/components/ThemeToggle';

describe('ThemeToggle', () => {
  it('renders a toggle button', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    );
    const button = screen.getByRole('button', { name: 'Toggle theme' });
    expect(button).toBeInTheDocument();
  });
});
