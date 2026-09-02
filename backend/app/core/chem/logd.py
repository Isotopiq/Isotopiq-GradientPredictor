"""logD calculation at a given pH from logP + pKa (Henderson-Hasselbalch)."""
from __future__ import annotations

from rdkit import Chem

from app.core.chem.pka import PkaSite, estimate_pka_sites


def logd_at_ph(mol: Chem.Mol, ph: float, logp: float) -> float:
    """Estimate logD at a given pH.

    For each ionizable site, apply the Henderson-Hasselbalch correction:
      - acid:  fraction_ionized = 1 / (1 + 10^(pKa - pH)); logD -= log10(1 + 10^(pKa-pH))
      - base:  fraction_ionized = 1 / (1 + 10^(pH - pKa)); logD -= log10(1 + 10^(pH-pKa))

    This is the standard additive approximation (ignores zwitterion complexity).
    """
    sites = estimate_pka_sites(mol)
    if not sites:
        return logp

    correction = 0.0
    for site in sites:
        if site.acid_base == "acid":
            # Acid: ionized (deprotonated) at pH > pKa; correction grows with pH
            correction += _hh_log10_term(ph - site.pka)
        else:  # base
            # Base: ionized (protonated) at pH < pKa; correction grows as pH drops
            correction += _hh_log10_term(site.pka - ph)
    return logp - correction


def _hh_log10_term(x: float) -> float:
    """log10(1 + 10^x), numerically stable for large |x|."""
    import math

    if x > 30:
        return x
    if x < -30:
        return 0.0
    return math.log10(1.0 + 10.0**x)


def fraction_ionized(site: PkaSite, ph: float) -> float:
    """Fraction of the site in ionized form at the given pH."""
    if site.acid_base == "acid":
        return 1.0 / (1.0 + 10.0 ** (site.pka - ph))
    return 1.0 / (1.0 + 10.0 ** (ph - site.pka))
