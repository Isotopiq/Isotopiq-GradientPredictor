"""Unit tests for the rules engine."""
from __future__ import annotations

from app.core.chem.parser import parse_mol
from app.core.rules.engine import suggest_method


class TestRulesEngine:
    def test_polar_compound_suggests_hilic_or_c18(self):
        # Very polar: glycine zwitterion
        mol = parse_mol("[NH3+]CC(=O)[O-]").mol
        suggestion = suggest_method(mol)
        # Very polar -> HILIC or ion_pair
        assert suggestion.column.column_type in ("HILIC", "ion_pair", "C18")

    def test_hydrophobic_compound_suggests_c18(self):
        # Decane: very hydrophobic
        mol = parse_mol("CCCCCCCCCC").mol
        suggestion = suggest_method(mol)
        assert suggestion.column.column_type == "C18"

    def test_ph_recommendation_away_from_pka(self):
        # Acetic acid (pKa ~4.2)
        mol = parse_mol("CC(=O)O").mol
        suggestion = suggest_method(mol, retention_goal="neutral")
        # pH should be at least 1.5 away from pKa 4.2
        for lo, hi in suggestion.ph.warning_zones:
            assert not lo <= suggestion.ph.recommended_ph <= hi

    def test_additive_esi_plus(self):
        mol = parse_mol("CC(=O)O").mol
        suggestion = suggest_method(mol, ionization_mode="ESI+")
        assert "formic" in suggestion.additive.additive.lower() or "acetic" in suggestion.additive.additive.lower()

    def test_additive_esi_minus_basic(self):
        mol = parse_mol("CC(=O)O").mol
        suggestion = suggest_method(mol, ionization_mode="ESI-", retention_goal="ionized")
        # At high pH for ESI- -> ammonium bicarbonate
        assert "ammonium" in suggestion.additive.additive.lower()

    def test_gradient_table_has_points(self):
        mol = parse_mol("CCO").mol
        suggestion = suggest_method(mol)
        gt = suggestion.gradient["gradient_table"]
        assert len(gt) >= 3
        assert all("time_s" in p and "percent_b" in p for p in gt)

    def test_permanently_charged_detected(self):
        # Choline: quaternary ammonium
        mol = parse_mol("C[N+](C)(C)CCO").mol
        suggestion = suggest_method(mol)
        assert suggestion.permanently_charged is True

    def test_not_permanently_charged(self):
        mol = parse_mol("CCO").mol
        suggestion = suggest_method(mol)
        assert suggestion.permanently_charged is False
