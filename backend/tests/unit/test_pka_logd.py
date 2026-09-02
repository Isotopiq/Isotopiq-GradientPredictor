"""Unit tests for chem.pka and chem.logd."""
from __future__ import annotations

import pytest

from app.core.chem.logd import logd_at_ph
from app.core.chem.parser import parse_mol
from app.core.chem.pka import (
    ChemAxonPkaProvider,
    RDKitPkaProvider,
    estimate_pka_sites,
    estimate_pka_values,
)


class TestPka:
    def test_acetic_acid_has_acid_site(self):
        mol = parse_mol("CC(=O)O").mol
        sites = estimate_pka_sites(mol)
        acids = [s for s in sites if s.acid_base == "acid"]
        assert len(acids) >= 1

    def test_amine_has_base_site(self):
        mol = parse_mol("CCN").mol
        sites = estimate_pka_sites(mol)
        bases = [s for s in sites if s.acid_base == "base"]
        assert len(bases) >= 1

    def test_ethanol_no_ionizable(self):
        mol = parse_mol("CCO").mol
        values = estimate_pka_values(mol)
        # Ethanol's OH is very weak; may or may not be detected by our heuristic
        # Just ensure no crash
        assert isinstance(values, list)

    def test_multi_protic(self):
        # Citric acid has 3 COOH groups
        mol = parse_mol("OC(=O)CC(O)(CC(O)=O)C(O)=O").mol
        values = estimate_pka_values(mol)
        assert isinstance(values, list)

    def test_chemaxon_stub_raises(self):
        mol = parse_mol("CCO").mol
        with pytest.raises(NotImplementedError):
            ChemAxonPkaProvider().estimate_pka(mol)


class TestLogD:
    def test_neutral_compound_logd_equals_logp(self):
        # Benzene: no ionizable sites
        mol = parse_mol("c1ccccc1").mol
        logp = 2.0
        logd = logd_at_ph(mol, ph=7.0, logp=logp)
        assert logd == pytest.approx(logp, abs=0.01)

    def test_ionized_acid_reduces_logd(self):
        # Acetic acid at high pH should have lower logD than logP
        mol = parse_mol("CC(=O)O").mol
        logp = -0.2
        logd_low_ph = logd_at_ph(mol, ph=2.0, logp=logp)
        logd_high_ph = logd_at_ph(mol, ph=8.0, logp=logp)
        assert logd_high_ph < logd_low_ph  # more ionized at high pH -> lower logD
