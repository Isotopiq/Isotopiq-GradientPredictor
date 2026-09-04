"""pH selector with ionic forms visualization.

Provides ionic species distribution across pH 0-14, suitability
classification (suitable/acceptable/prohibited), and buffer
recommendations, similar to ACD/Labs pH Selector.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.chem.pka import estimate_pka_sites


@dataclass
class IonicSpecies:
    """An ionic species at a given pH."""
    ph: float
    fractions: list[float]  # fraction of each ionizable form
    net_charge: float
    logd_estimate: float | None = None


@dataclass
class PhDistribution:
    """Ionic species distribution across a pH range."""
    ph_values: list[float]
    species_fractions: list[list[float]]  # [ph_index][species_index]
    net_charges: list[float]
    pka_sites: list[dict[str, Any]]
    smiles: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ph_values": [round(p, 2) for p in self.ph_values],
            "species_fractions": [[round(f, 4) for f in row] for row in self.species_fractions],
            "net_charges": [round(c, 4) for c in self.net_charges],
            "pka_sites": self.pka_sites,
            "smiles": self.smiles,
        }


@dataclass
class PhSuitabilityMap:
    """pH suitability classification for a mixture."""
    ph_values: list[float]
    zones: list[str]  # "suitable", "acceptable", "prohibited" per pH
    min_logd: list[float]  # minimum logD across all compounds at each pH
    recommended_phs: list[float]
    buffer_suggestions: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ph_values": [round(p, 2) for p in self.ph_values],
            "zones": self.zones,
            "min_logd": [round(v, 4) for v in self.min_logd],
            "recommended_phs": [round(p, 2) for p in self.recommended_phs],
            "buffer_suggestions": self.buffer_suggestions,
        }


def ph_distribution(
    smiles: str,
    ph_min: float = 0.0,
    ph_max: float = 14.0,
    steps: int = 100,
    logp: float = 2.0,
) -> PhDistribution:
    """Compute ionic species distribution across a pH range.

    Uses multi-site Henderson-Hasselbalch for each ionizable site.
    """
    from app.core.chem.parser import parse_mol

    mol = parse_mol(smiles).mol
    sites = estimate_pka_sites(mol)

    ph_values = [ph_min + (ph_max - ph_min) * i / (steps - 1) for i in range(steps)]

    # For each pH, compute the fraction of each ionizable form
    # Each site can be protonated or deprotonated
    species_fractions: list[list[float]] = []
    net_charges: list[float] = []

    for ph in ph_values:
        if not sites:
            species_fractions.append([1.0])
            net_charges.append(0.0)
            continue

        # For each site, compute protonated fraction
        fractions = []
        total_charge = 0.0
        for site in sites:
            if site.acid_base == "acid":
                # HA ⇌ H+ + A- ; fraction protonated (neutral) = 1/(1+10^(pH-pKa))
                frac_protonated = 1.0 / (1.0 + 10 ** (ph - site.pka))
                fractions.append(frac_protonated)
                total_charge += -(1.0 - frac_protonated)  # deprotonated = -1
            else:  # base
                # BH+ ⇌ B + H+ ; fraction protonated (charged) = 1/(1+10^(pKa-pH))
                frac_protonated = 1.0 / (1.0 + 10 ** (site.pka - ph))
                fractions.append(frac_protonated)
                total_charge += frac_protonated  # protonated = +1

        species_fractions.append(fractions)
        net_charges.append(total_charge)

    pka_site_dicts = [
        {"pka": s.pka, "acid_base": s.acid_base, "atom_idx": s.atom_idx}
        for s in sites
    ]

    return PhDistribution(
        ph_values=ph_values,
        species_fractions=species_fractions,
        net_charges=net_charges,
        pka_sites=pka_site_dicts,
        smiles=smiles,
    )


def ph_suitability(
    smiles_list: list[str],
    ph_min: float = 2.0,
    ph_max: float = 10.0,
    steps: int = 80,
    buffer_count: int = 4,
) -> PhSuitabilityMap:
    """Compute pH suitability map for a mixture of compounds.

    Classifies each pH as:
    - "suitable": all compounds in stable (neutral or fully ionized) form
    - "acceptable": some compounds near pKa (within ±1.0)
    - "prohibited": one or more compounds at pKa (within ±0.5)
    """
    from app.core.chem.descriptors import compute_descriptors
    from app.core.chem.logd import logd_at_ph
    from app.core.chem.parser import parse_mol

    all_pka_values: list[list[float]] = []
    all_logps: list[float] = []

    for smi in smiles_list:
        try:
            mol = parse_mol(smi).mol
            desc = compute_descriptors(mol)
            sites = estimate_pka_sites(mol)
            all_pka_values.append([s.pka for s in sites])
            all_logps.append(desc.logp)
        except Exception:
            all_pka_values.append([])
            all_logps.append(2.0)

    ph_values = [ph_min + (ph_max - ph_min) * i / (steps - 1) for i in range(steps)]
    zones: list[str] = []
    min_logds: list[float] = []

    for ph in ph_values:
        # Check proximity to pKa for all compounds
        min_pka_dist = float("inf")
        logds = []
        for i, pkas in enumerate(all_pka_values):
            for pka in pkas:
                dist = abs(ph - pka)
                if dist < min_pka_dist:
                    min_pka_dist = dist
            # Compute logD at this pH
            try:
                mol = parse_mol(smiles_list[i]).mol
                ld = logd_at_ph(mol, ph, all_logps[i])
            except Exception:
                ld = all_logps[i]
            logds.append(ld)

        min_logd = min(logds) if logds else 0.0
        min_logds.append(min_logd)

        if min_pka_dist < 0.5:
            zones.append("prohibited")
        elif min_pka_dist < 1.0:
            zones.append("acceptable")
        else:
            zones.append("suitable")

    # Find recommended pH values at suitable plateaus
    recommended = _find_plateaus(ph_values, zones, buffer_count)

    # Buffer suggestions
    buffer_suggestions = []
    for rec_ph in recommended:
        buffer_suggestions.append(suggest_buffer(rec_ph))

    return PhSuitabilityMap(
        ph_values=ph_values,
        zones=zones,
        min_logd=min_logds,
        recommended_phs=recommended,
        buffer_suggestions=buffer_suggestions,
    )


def suggest_buffer(ph: float) -> dict[str, Any]:
    """Suggest the best buffer for a target pH."""
    buffers = [
        {"name": "Formic acid", "pKa": 3.75, "range": (2.7, 3.7), "ms_compatible": True,
         "recipe": "0.1% formic acid in water"},
        {"name": "Ammonium formate", "pKa": 3.75, "range": (3.0, 4.5), "ms_compatible": True,
         "recipe": "10 mM ammonium formate, adjust with formic acid"},
        {"name": "Acetic acid", "pKa": 4.76, "range": (3.7, 5.5), "ms_compatible": True,
         "recipe": "0.1% acetic acid in water"},
        {"name": "Ammonium acetate", "pKa": 4.76, "range": (4.0, 6.0), "ms_compatible": True,
         "recipe": "10 mM ammonium acetate, adjust with acetic acid or ammonia"},
        {"name": "Ammonium bicarbonate", "pKa": 9.25, "range": (8.0, 10.0), "ms_compatible": True,
         "recipe": "10 mM ammonium bicarbonate, adjust with ammonia"},
        {"name": "Phosphate", "pKa": 7.2, "range": (6.0, 8.0), "ms_compatible": False,
         "recipe": "10 mM potassium phosphate, non-volatile (not MS-compatible)"},
        {"name": "Formate (high pH)", "pKa": 3.75, "range": (2.7, 3.7), "ms_compatible": True,
         "recipe": "0.1% formic acid"},
    ]

    best = None
    best_dist = float("inf")
    for buf in buffers:
        lo, hi = buf["range"]
        if lo <= ph <= hi:
            dist = abs(ph - buf["pKa"])
            if dist < best_dist:
                best_dist = dist
                best = buf

    if best is None:
        # Find closest by pKa
        for buf in buffers:
            dist = abs(ph - buf["pKa"])
            if dist < best_dist:
                best_dist = dist
                best = buf

    return best or {"name": "Custom", "recipe": "No standard buffer", "ms_compatible": False,
                    "range": (ph, ph), "pKa": ph}


def _find_plateaus(ph_values: list[float], zones: list[str], count: int) -> list[float]:
    """Find pH values at the center of suitable plateaus."""
    plateaus: list[tuple[float, float]] = []  # (start, end)
    in_plateau = False
    start = 0.0

    for i, zone in enumerate(zones):
        if zone == "suitable" and not in_plateau:
            in_plateau = True
            start = ph_values[i]
        elif zone != "suitable" and in_plateau:
            in_plateau = False
            plateaus.append((start, ph_values[i - 1]))

    if in_plateau:
        plateaus.append((start, ph_values[-1]))

    # Sort by width (widest first) and take top `count`
    plateaus.sort(key=lambda p: p[1] - p[0], reverse=True)
    recommended = []
    for p in plateaus[:count]:
        center = (p[0] + p[1]) / 2
        recommended.append(center)

    return sorted(recommended)
