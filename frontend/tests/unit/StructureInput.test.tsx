import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider } from '@/context/ThemeContext';
import { StructureInput } from '@/components/StructureInput';

// Mock the API
vi.mock('@/api/compounds', () => ({
  compoundsApi: {
    create: vi.fn().mockResolvedValue({ id: '1', smiles: 'CCO', mw: 46 }),
    pubchemLookup: vi.fn().mockResolvedValue({ smiles: 'CN1C=NC2=C1C(=O)N(C(=O)N2C)C' }),
    searchMulti: vi.fn().mockResolvedValue([]),
  },
}));

describe('StructureInput', () => {
  it('renders all tabs', () => {
    render(
      <ThemeProvider>
        <StructureInput onCompoundCreated={() => {}} onSmilesChange={() => {}} />
      </ThemeProvider>,
    );
    expect(screen.getByText('Draw')).toBeInTheDocument();
    expect(screen.getByText('Paste')).toBeInTheDocument();
    expect(screen.getByText('Upload')).toBeInTheDocument();
    expect(screen.getByText('Search')).toBeInTheDocument();
  });

  it('switches to search tab', () => {
    render(
      <ThemeProvider>
        <StructureInput onCompoundCreated={() => {}} onSmilesChange={() => {}} />
      </ThemeProvider>,
    );
    // Search is the default tab, so the search input should be visible
    expect(screen.getByPlaceholderText(/Search compound by name/i)).toBeInTheDocument();
  });

  it('has a calculate button', () => {
    render(
      <ThemeProvider>
        <StructureInput onCompoundCreated={() => {}} onSmilesChange={() => {}} />
      </ThemeProvider>,
    );
    expect(screen.getByText('Calculate Descriptors')).toBeInTheDocument();
  });
});
