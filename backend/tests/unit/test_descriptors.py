"""Unit tests for chem.descriptors."""
from __future__ import annotations

from app.core.chem.descriptors import compute_descriptors
from app.core.chem.parser import parse_mol


class TestDescriptors:
    def test_ethanol(self):
        mol = parse_mol("CCO").mol
        d = compute_descriptors(mol)
        assert 45 < d.mw < 47  # ethanol MW ~46
        assert -0.5 < d.logp < 0.5
        assert d.hbd == 1  # one OH
        assert d.hba == 1  # one O
        assert d.rotatable_bonds == 0

    def test_caffeine(self):
        mol = parse_mol("CN1C=NC2=C1C(=O)N(C(=O)N2C)C").mol
        d = compute_descriptors(mol)
        assert 190 < d.mw < 200  # caffeine MW ~194
        assert d.hbd == 0
        assert d.hba >= 2  # multiple N/O acceptors
        assert d.aromatic_rings >= 0

    def test_ibuprofen(self):
        mol = parse_mol("CC(C)CC1=CC=C(C=C1)C(C)C(=O)O").mol
        d = compute_descriptors(mol)
        assert 200 < d.mw < 210
        assert d.hbd == 1  # COOH
        assert d.hba >= 1
        assert d.rotatable_bonds >= 3

    def test_zwitterion(self):
        # Glycine zwitterion
        mol = parse_mol("[NH3+]CC(=O)[O-]").mol
        d = compute_descriptors(mol)
        assert 70 < d.mw < 80
        assert d.tpsa > 40  # polar
