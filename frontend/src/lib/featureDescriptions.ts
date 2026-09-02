/** Human-readable descriptions for ML feature names. */

export const featureDescriptions: Record<string, string> = {
  mw: 'Molecular weight (g/mol)',
  logp: 'Calculated octanol-water partition coefficient',
  tpsa: 'Topological polar surface area (Å²)',
  hbd: 'Hydrogen bond donors',
  hba: 'Hydrogen bond acceptors',
  rotatable_bonds: 'Number of rotatable bonds',
  aromatic_rings: 'Number of aromatic rings',
  num_rings: 'Total ring count',
  num_heavy_atoms: 'Non-hydrogen atom count',
  num_heteroatoms: 'Heteroatom count (N, O, S, etc.)',
  fraction_csp3: 'Fraction of sp3-hybridized carbons',
  n_pka_sites: 'Number of ionizable sites',
  min_pka: 'Lowest estimated pKa',
  max_pka: 'Highest estimated pKa',
  ph: 'Mobile phase pH',
  percent_b_start: 'Starting %B (strong solvent)',
  percent_b_end: 'Final %B (strong solvent)',
  gradient_time_min: 'Gradient duration (minutes)',
  flow_rate_ml_min: 'Flow rate (mL/min)',
  temperature_c: 'Column temperature (°C)',
  col_C18: 'C18 column type (one-hot)',
  col_phenyl: 'Phenyl column type (one-hot)',
  col_HILIC: 'HILIC column type (one-hot)',
  col_ion_pair: 'Ion-pair column type (one-hot)',
  col_other: 'Other column type (one-hot)',
};

export function getFeatureDescription(name: string): string {
  return featureDescriptions[name] || name;
}

export function getFeatureCategory(name: string): 'molecular' | 'method' | 'column' {
  const molecular = ['mw', 'logp', 'tpsa', 'hbd', 'hba', 'rotatable_bonds', 'aromatic_rings',
    'num_rings', 'num_heavy_atoms', 'num_heteroatoms', 'fraction_csp3', 'n_pka_sites',
    'min_pka', 'max_pka'];
  const method = ['ph', 'percent_b_start', 'percent_b_end', 'gradient_time_min',
    'flow_rate_ml_min', 'temperature_c'];
  if (molecular.includes(name)) return 'molecular';
  if (method.includes(name)) return 'method';
  return 'column';
}
