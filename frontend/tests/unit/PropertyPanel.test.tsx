import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PropertyPanel } from '@/components/PropertyPanel';
import type { Compound } from '@/types';

const mockCompound: Compound = {
  id: '1',
  owner_id: null,
  is_shared: false,
  name: 'Ethanol',
  smiles: 'CCO',
  inchi: null,
  inchikey: null,
  molfile: null,
  cas: null,
  mw: 46.07,
  logp: -0.2,
  logd_at_ph: null,
  pka_values: null,
  tpsa: 20.23,
  hbd: 1,
  hba: 1,
  rotatable_bonds: 0,
  aromatic_rings: 0,
  source: 'manual',
};

describe('PropertyPanel', () => {
  it('shows empty state when no compound', () => {
    render(<PropertyPanel compound={null} />);
    expect(screen.getByText(/enter a structure/i)).toBeInTheDocument();
  });

  it('shows loading skeleton', () => {
    render(<PropertyPanel compound={null} loading={true} />);
    const skeleton = document.querySelector('.animate-pulse');
    expect(skeleton).toBeInTheDocument();
  });

  it('displays compound properties', () => {
    render(<PropertyPanel compound={mockCompound} />);
    // Name is not displayed in the panel, only properties
    expect(screen.queryByText('Ethanol')).not.toBeInTheDocument();
    expect(screen.getByText('46.07 g/mol')).toBeInTheDocument();
  });
});
