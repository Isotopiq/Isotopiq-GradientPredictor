"""Commercial column database — static reference data from manufacturer specs.

Sources: Thermo Fisher Scientific, Agilent Technologies, Waters Corporation,
Phenomenex, Restek, Shimadzu product documentation (2024-2025).
Focus: small molecule analysis columns.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ColumnSpec:
    id: str
    brand: str
    name: str
    chemistry: str  # C18, C8, phenyl, HILIC, PFP, etc.
    particle_size_um: float
    length_mm: int
    inner_diameter_mm: float
    ph_range: tuple[float, float]
    temperature_max_c: int
    usp_code: str | None
    notes: str


_COLUMNS: list[ColumnSpec] = [
    # =========================================================================
    # Thermo Fisher Scientific — Small Molecule Columns
    # =========================================================================

    # Hypersil GOLD VANQUISH (UHPLC, fully porous, 1.9 µm)
    ColumnSpec("thermo-hypersil-gold-vanquish-c18-19-21x50", "Thermo Fisher", "Hypersil GOLD VANQUISH C18", "C18", 1.9, 50, 2.1, (1, 11), 60, "L1", "UHPLC, ultrapure silica, 175Å pore, 220 m²/g, max 1000 bar, endcapped"),
    ColumnSpec("thermo-hypersil-gold-vanquish-c18-19-21x100", "Thermo Fisher", "Hypersil GOLD VANQUISH C18", "C18", 1.9, 100, 2.1, (1, 11), 60, "L1", "UHPLC, ultrapure silica, 175Å pore, 220 m²/g, max 1000 bar, endcapped"),
    ColumnSpec("thermo-hypersil-gold-vanquish-c18-19-21x150", "Thermo Fisher", "Hypersil GOLD VANQUISH C18", "C18", 1.9, 150, 2.1, (1, 11), 60, "L1", "UHPLC, ultrapure silica, 175Å pore, 220 m²/g, max 1000 bar, endcapped"),
    ColumnSpec("thermo-hypersil-gold-vanquish-c8-19-21x100", "Thermo Fisher", "Hypersil GOLD VANQUISH C8", "C8", 1.9, 100, 2.1, (1, 11), 60, "L7", "UHPLC, less retentive than C18, 175Å pore"),
    ColumnSpec("thermo-hypersil-gold-vanquish-aq-19-21x100", "Thermo Fisher", "Hypersil GOLD VANQUISH aQ", "C18", 1.9, 100, 2.1, (1, 11), 60, "L1", "UHPLC, 100% aqueous compatible, polar embedded"),
    ColumnSpec("thermo-hypersil-gold-vanquish-pfp-19-21x100", "Thermo Fisher", "Hypersil GOLD VANQUISH PFP", "PFP", 1.9, 100, 2.1, (1, 10), 50, "L43", "UHPLC, pentafluorophenyl, halogenated/aromatic selectivity"),
    ColumnSpec("thermo-hypersil-gold-vanquish-phenyl-19-21x100", "Thermo Fisher", "Hypersil GOLD VANQUISH Phenyl", "phenyl", 1.9, 100, 2.1, (1, 10), 50, "L11", "UHPLC, phenyl selectivity, pi-pi interactions"),

    # Hypersil GOLD (HPLC, 3 µm / 5 µm)
    ColumnSpec("thermo-hypersil-gold-c18-30-21x100", "Thermo Fisher", "Hypersil GOLD C18", "C18", 3.0, 100, 2.1, (1, 11), 50, "L1", "HPLC, high purity silica, 175Å pore, endcapped"),
    ColumnSpec("thermo-hypersil-gold-c18-30-46x150", "Thermo Fisher", "Hypersil GOLD C18", "C18", 3.0, 150, 4.6, (1, 11), 50, "L1", "HPLC, general purpose, analytical scale"),
    ColumnSpec("thermo-hypersil-gold-c18-50-46x250", "Thermo Fisher", "Hypersil GOLD C18", "C18", 5.0, 250, 4.6, (1, 11), 50, "L1", "HPLC, conventional analytical, 5µm"),
    ColumnSpec("thermo-hypersil-gold-c8-30-46x150", "Thermo Fisher", "Hypersil GOLD C8", "C8", 3.0, 150, 4.6, (1, 11), 50, "L7", "HPLC, less retention than C18"),
    ColumnSpec("thermo-hypersil-gold-phenyl-30-46x150", "Thermo Fisher", "Hypersil GOLD Phenyl", "phenyl", 3.0, 150, 4.6, (1, 10), 50, "L11", "HPLC, aromatic selectivity"),

    # Accucore VANQUISH (UHPLC, solid core, 1.5 µm)
    ColumnSpec("thermo-accucore-vanquish-c18plus-15-21x50", "Thermo Fisher", "Accucore VANQUISH C18+", "C18", 1.5, 50, 2.1, (2, 9), 60, "L1", "UHPLC, solid core 1.5µm, 80Å pore, 110 m²/g, max 1500 bar"),
    ColumnSpec("thermo-accucore-vanquish-c18plus-15-21x100", "Thermo Fisher", "Accucore VANQUISH C18+", "C18", 1.5, 100, 2.1, (2, 9), 60, "L1", "UHPLC, solid core 1.5µm, 80Å pore, 110 m²/g, max 1500 bar"),
    ColumnSpec("thermo-accucore-vanquish-c18plus-15-21x150", "Thermo Fisher", "Accucore VANQUISH C18+", "C18", 1.5, 150, 2.1, (2, 9), 60, "L1", "UHPLC, solid core 1.5µm, 80Å pore, 110 m²/g, max 1500 bar"),

    # Accucore (HPLC, solid core, 2.6 µm)
    ColumnSpec("thermo-accucore-c18-26-21x100", "Thermo Fisher", "Accucore C18", "C18", 2.6, 100, 2.1, (1, 11), 60, "L1", "Solid core 2.6µm, 80Å pore, 130 m²/g, pH 1-11, core-shell"),
    ColumnSpec("thermo-accucore-c18-26-46x150", "Thermo Fisher", "Accucore C18", "C18", 2.6, 150, 4.6, (1, 11), 60, "L1", "Solid core 2.6µm, HPLC, core-shell efficiency"),
    ColumnSpec("thermo-accucore-rp-ms-26-21x100", "Thermo Fisher", "Accucore RP-MS", "C18", 2.6, 100, 2.1, (2, 9), 60, None, "Solid core, LC-MS optimized, low bleed, 80Å pore"),
    ColumnSpec("thermo-accucore-aq-26-21x100", "Thermo Fisher", "Accucore aQ", "C18", 2.6, 100, 2.1, (2, 9), 60, "L1", "Solid core, 100% aqueous compatible, polar compounds"),
    ColumnSpec("thermo-accucore-c8-26-21x100", "Thermo Fisher", "Accucore C8", "C8", 2.6, 100, 2.1, (2, 9), 60, "L7", "Solid core, less retentive, fast elution"),
    ColumnSpec("thermo-accucore-phenyl-hexyl-26-21x100", "Thermo Fisher", "Accucore Phenyl-Hexyl", "phenyl", 2.6, 100, 2.1, (2, 8), 50, "L11", "Solid core, phenyl-hexyl, aromatic selectivity"),
    ColumnSpec("thermo-accucore-pfp-26-21x100", "Thermo Fisher", "Accucore PFP", "PFP", 2.6, 100, 2.1, (2, 8), 50, "L43", "Solid core, pentafluorophenyl, positional isomer separation"),
    ColumnSpec("thermo-accucore-polar-premium-26-21x100", "Thermo Fisher", "Accucore Polar Premium", "C18", 2.6, 100, 2.1, (1.5, 10.5), 50, "L60", "Solid core, polar embedded, 100% aqueous stable"),
    ColumnSpec("thermo-accucore-hilic-26-21x100", "Thermo Fisher", "Accucore HILIC", "HILIC", 2.6, 100, 2.1, (2, 8), 40, "L3", "Solid core HILIC, polar metabolites, 150Å pore"),
    ColumnSpec("thermo-accucore-150-amide-hilic-26-21x150", "Thermo Fisher", "Accucore 150 Amide HILIC", "HILIC", 2.6, 150, 2.1, (2, 8), 40, None, "Solid core, amide-bonded HILIC, 150Å pore for large polar metabolites"),
    ColumnSpec("thermo-accucore-c30-26-21x100", "Thermo Fisher", "Accucore C30", "C30", 2.6, 100, 2.1, (2, 8), 50, "L62", "Solid core C30, carotenoids, fat-soluble vitamins, shape selectivity"),

    # Acclaim VANQUISH (UHPLC, fully porous, 2.2 µm)
    ColumnSpec("thermo-acclaim-vanquish-c18-22-21x150", "Thermo Fisher", "Acclaim VANQUISH C18", "C18", 2.2, 150, 2.1, (2, 9), 60, "L1", "UHPLC, high carbon load, 120Å pore, basic compounds"),
    ColumnSpec("thermo-acclaim-vanquish-pa2-22-21x150", "Thermo Fisher", "Acclaim VANQUISH PA2", "C18", 2.2, 150, 2.1, (1.5, 10), 60, "L1", "UHPLC, polar-endcapped, multi-mode interactions"),

    # Acclaim (HPLC, 3 µm / 5 µm)
    ColumnSpec("thermo-acclaim-120-c18-30-46x150", "Thermo Fisher", "Acclaim 120 C18", "C18", 3.0, 150, 4.6, (2, 9), 60, "L1", "HPLC, 120Å pore, high carbon load, basic compounds"),
    ColumnSpec("thermo-acclaim-120-c18-50-46x250", "Thermo Fisher", "Acclaim 120 C18", "C18", 5.0, 250, 4.6, (2, 9), 60, "L1", "HPLC, conventional, 120Å pore"),
    ColumnSpec("thermo-acclaim-mixed-mode-hilic-30-21x150", "Thermo Fisher", "Acclaim Mixed-Mode HILIC", "HILIC", 3.0, 150, 2.1, (2, 7), 40, None, "HILIC + ion-exchange, charged polar compounds"),

    # Hypercarb (Porous Graphitic Carbon)
    ColumnSpec("thermo-hypercarb-50-21x100", "Thermo Fisher", "Hypercarb PGC", "PGC", 5.0, 100, 2.1, (1, 14), 150, None, "Porous graphitic carbon, extreme pH/temp, polar compound retention"),

    # =========================================================================
    # Agilent Technologies — Small Molecule Columns
    # =========================================================================

    # ZORBAX Eclipse Plus RRHD (UHPLC, 1.8 µm, 1200 bar)
    ColumnSpec("agilent-rrhd-eclipse-plus-c18-18-21x50", "Agilent", "ZORBAX RRHD Eclipse Plus C18", "C18", 1.8, 50, 2.1, (2, 9), 60, "L1", "UHPLC, 95Å pore, 160 m²/g, 9% carbon, double endcapped, max 1200 bar"),
    ColumnSpec("agilent-rrhd-eclipse-plus-c18-18-21x100", "Agilent", "ZORBAX RRHD Eclipse Plus C18", "C18", 1.8, 100, 2.1, (2, 9), 60, "L1", "UHPLC, 95Å pore, 160 m²/g, 9% carbon, double endcapped, max 1200 bar"),
    ColumnSpec("agilent-rrhd-eclipse-plus-c18-18-46x100", "Agilent", "ZORBAX RRHD Eclipse Plus C18", "C18", 1.8, 100, 4.6, (2, 9), 60, "L1", "UHPLC, analytical scale, 95Å pore, double endcapped"),
    ColumnSpec("agilent-rrhd-eclipse-plus-c18-18-46x150", "Agilent", "ZORBAX RRHD Eclipse Plus C18", "C18", 1.8, 150, 4.6, (2, 9), 60, "L1", "UHPLC, analytical scale, 95Å pore, double endcapped"),
    ColumnSpec("agilent-rrhd-eclipse-plus-c8-18-21x100", "Agilent", "ZORBAX RRHD Eclipse Plus C8", "C8", 1.8, 100, 2.1, (2, 9), 60, "L7", "UHPLC, 95Å pore, 7% carbon, double endcapped, less retentive"),
    ColumnSpec("agilent-rrhd-eclipse-plus-phenyl-hexyl-18-21x100", "Agilent", "ZORBAX RRHD Eclipse Plus Phenyl-Hexyl", "phenyl", 1.8, 100, 2.1, (2, 9), 60, "L11", "UHPLC, 95Å pore, phenyl-hexyl, aromatic selectivity"),
    ColumnSpec("agilent-rrhd-eclipse-plus-phenyl-hexyl-18-46x150", "Agilent", "ZORBAX RRHD Eclipse Plus Phenyl-Hexyl", "phenyl", 1.8, 150, 4.6, (2, 9), 60, "L11", "UHPLC, analytical, aromatic selectivity"),

    # ZORBAX Eclipse Plus (HPLC, 3.5 µm / 5 µm)
    ColumnSpec("agilent-eclipse-plus-c18-35-46x100", "Agilent", "ZORBAX Eclipse Plus C18", "C18", 3.5, 100, 4.6, (2, 9), 60, "L1", "HPLC, 95Å pore, double endcapped, good peak shape for bases"),
    ColumnSpec("agilent-eclipse-plus-c18-50-46x150", "Agilent", "ZORBAX Eclipse Plus C18", "C18", 5.0, 150, 4.6, (2, 9), 60, "L1", "HPLC, conventional, 95Å pore, double endcapped"),
    ColumnSpec("agilent-eclipse-plus-c18-50-46x250", "Agilent", "ZORBAX Eclipse Plus C18", "C18", 5.0, 250, 4.6, (2, 9), 60, "L1", "HPLC, conventional, 95Å pore, higher resolution"),
    ColumnSpec("agilent-eclipse-plus-phenyl-hexyl-35-46x150", "Agilent", "ZORBAX Eclipse Plus Phenyl-Hexyl", "phenyl", 3.5, 150, 4.6, (2, 9), 60, "L11", "HPLC, aromatic selectivity, 95Å pore"),

    # ZORBAX SB (StableBond, low pH optimized)
    ColumnSpec("agilent-sb-c18-18-21x50", "Agilent", "ZORBAX SB-C18", "C18", 1.8, 50, 2.1, (1, 8), 60, "L1", "UHPLC, StableBond, low pH optimized, 80Å pore, monofunctional"),
    ColumnSpec("agilent-sb-c18-35-46x150", "Agilent", "ZORBAX SB-C18", "C18", 3.5, 150, 4.6, (1, 8), 60, "L1", "HPLC, StableBond, low pH, 80Å pore, sterically protected"),
    ColumnSpec("agilent-sb-c18-50-46x250", "Agilent", "ZORBAX SB-C18", "C18", 5.0, 250, 4.6, (1, 8), 60, "L1", "HPLC, StableBond, conventional, low pH stable"),
    ColumnSpec("agilent-sb-c8-35-46x150", "Agilent", "ZORBAX SB-C8", "C8", 3.5, 150, 4.6, (1, 8), 60, "L7", "HPLC, StableBond C8, less retentive, low pH"),
    ColumnSpec("agilent-sb-aq-35-46x150", "Agilent", "ZORBAX SB-Aq", "C18", 3.5, 150, 4.6, (1, 8), 60, "L1", "HPLC, 100% aqueous, polar compounds, StableBond"),
    ColumnSpec("agilent-sb-phenyl-35-46x150", "Agilent", "ZORBAX SB-Phenyl", "phenyl", 3.5, 150, 4.6, (1, 8), 60, "L11", "HPLC, StableBond phenyl, aromatic selectivity"),

    # ZORBAX Extend-C18 (high pH, up to pH 11.5)
    ColumnSpec("agilent-extend-c18-18-21x100", "Agilent", "ZORBAX Extend-C18", "C18", 1.8, 100, 2.1, (2, 11.5), 60, "L1", "UHPLC, high pH stable, bidentate bonding, 80Å pore"),
    ColumnSpec("agilent-extend-c18-35-46x150", "Agilent", "ZORBAX Extend-C18", "C18", 3.5, 150, 4.6, (2, 11.5), 60, "L1", "HPLC, high pH, bidentate, basic compounds at high pH"),

    # ZORBAX RRHD Eclipse XDB (extra dense bonding)
    ColumnSpec("agilent-rrhd-eclipse-xdb-c18-18-21x100", "Agilent", "ZORBAX RRHD Eclipse XDB-C18", "C18", 1.8, 100, 2.1, (2, 9), 60, "L1", "UHPLC, extra dense bonding, 95Å pore, 8% carbon"),
    ColumnSpec("agilent-rrhd-eclipse-xdb-c8-18-21x100", "Agilent", "ZORBAX RRHD Eclipse XDB-C8", "C8", 1.8, 100, 2.1, (2, 9), 60, "L7", "UHPLC, extra dense bonding, less retentive"),

    # Poroshell 120 (solid core, 2.7 µm, 120Å)
    ColumnSpec("agilent-poroshell-120-c18-27-21x100", "Agilent", "Poroshell 120 EC-C18", "C18", 2.7, 100, 2.1, (2, 9), 60, "L1", "Solid core 2.7µm, 120Å pore, 90 m²/g, endcapped, HPLC efficiency"),
    ColumnSpec("agilent-poroshell-120-c18-27-46x100", "Agilent", "Poroshell 120 EC-C18", "C18", 2.7, 100, 4.6, (2, 9), 60, "L1", "Solid core 2.7µm, 120Å pore, analytical scale"),
    ColumnSpec("agilent-poroshell-120-c18-27-46x150", "Agilent", "Poroshell 120 EC-C18", "C18", 2.7, 150, 4.6, (2, 9), 60, "L1", "Solid core 2.7µm, 120Å pore, higher resolution"),
    ColumnSpec("agilent-poroshell-120-sb-c18-27-21x100", "Agilent", "Poroshell 120 SB-C18", "C18", 2.7, 100, 2.1, (1, 8), 60, "L1", "Solid core, StableBond, low pH optimized"),
    ColumnSpec("agilent-poroshell-120-phenyl-hexyl-27-21x100", "Agilent", "Poroshell 120 Phenyl-Hexyl", "phenyl", 2.7, 100, 2.1, (2, 9), 60, "L11", "Solid core, phenyl-hexyl, aromatic selectivity"),
    ColumnSpec("agilent-poroshell-120-hilic-z-27-21x150", "Agilent", "Poroshell 120 HILIC-Z", "HILIC", 2.7, 150, 2.1, (2, 9), 40, None, "Solid core HILIC, zwitterionic phase, polar metabolites"),
    ColumnSpec("agilent-poroshell-120-pfp-27-21x100", "Agilent", "Poroshell 120 PFP", "PFP", 2.7, 100, 2.1, (2, 8), 50, "L43", "Solid core, pentafluorophenyl, positional isomers"),

    # InfinityLab Poroshell 120 HILIC-Z (for metabolomics)
    ColumnSpec("agilent-poroshell-hilic-z-27-21x150", "Agilent", "InfinityLab Poroshell HILIC-Z", "HILIC", 2.7, 150, 2.1, (2, 9), 40, None, "PEEK-lined, zwitterionic, polar metabolomics, vitamins, nucleotides"),

    # =========================================================================
    # Waters Corporation — Small Molecule Columns
    # =========================================================================

    # ACQUITY UPLC BEH (1.7 µm, hybrid silica, pH 1-12)
    ColumnSpec("waters-beh-c18-17-21x50", "Waters", "ACQUITY UPLC BEH C18", "C18", 1.7, 50, 2.1, (1, 12), 60, "L1", "UPLC, BEH hybrid, 130Å pore, 185 m²/g, 18% carbon, max 18000 psi"),
    ColumnSpec("waters-beh-c18-17-21x100", "Waters", "ACQUITY UPLC BEH C18", "C18", 1.7, 100, 2.1, (1, 12), 60, "L1", "UPLC, BEH hybrid, 130Å pore, 185 m²/g, 18% carbon, general purpose"),
    ColumnSpec("waters-beh-c18-17-21x150", "Waters", "ACQUITY UPLC BEH C18", "C18", 1.7, 150, 2.1, (1, 12), 60, "L1", "UPLC, BEH hybrid, 130Å pore, higher resolution"),
    ColumnSpec("waters-beh-c18-17-46x100", "Waters", "ACQUITY UPLC BEH C18", "C18", 1.7, 100, 4.6, (1, 12), 60, "L1", "UPLC, analytical scale, BEH hybrid"),
    ColumnSpec("waters-beh-c8-17-21x100", "Waters", "ACQUITY UPLC BEH C8", "C8", 1.7, 100, 2.1, (1, 12), 60, "L7", "UPLC, BEH C8, less retentive, 130Å pore"),
    ColumnSpec("waters-beh-shield-rp18-17-21x100", "Waters", "ACQUITY UPLC BEH Shield RP18", "C18", 1.7, 100, 2.1, (1, 12), 60, "L1", "UPLC, polar embedded group, alternate selectivity"),
    ColumnSpec("waters-beh-phenyl-17-21x100", "Waters", "ACQUITY UPLC BEH Phenyl", "phenyl", 1.7, 100, 2.1, (1, 12), 60, "L11", "UPLC, BEH phenyl, aromatic selectivity, pi-pi"),
    ColumnSpec("waters-beh-amide-17-21x100", "Waters", "ACQUITY UPLC BEH Amide", "HILIC", 1.7, 100, 2.1, (1, 12), 60, None, "UPLC, amide-bonded HILIC, 130Å pore, polar metabolites"),
    ColumnSpec("waters-beh-hilic-17-21x100", "Waters", "ACQUITY UPLC BEH HILIC", "HILIC", 1.7, 100, 2.1, (1, 12), 45, "L3", "UPLC, unbonded BEH HILIC, 130Å pore, sugars/nucleotides"),

    # ACQUITY UPLC HSS (High Strength Silica, 1.8 µm, pH 1-8)
    ColumnSpec("waters-hss-c18-18-21x50", "Waters", "ACQUITY UPLC HSS C18", "C18", 1.8, 50, 2.1, (1, 8), 45, "L1", "UPLC, HSS silica, 100Å pore, 230 m²/g, 15% carbon, max 18000 psi"),
    ColumnSpec("waters-hss-c18-18-21x100", "Waters", "ACQUITY UPLC HSS C18", "C18", 1.8, 100, 2.1, (1, 8), 45, "L1", "UPLC, HSS silica, 100Å pore, increased retention vs BEH, low pH"),
    ColumnSpec("waters-hss-c18-18-21x150", "Waters", "ACQUITY UPLC HSS C18", "C18", 1.8, 150, 2.1, (1, 8), 45, "L1", "UPLC, HSS silica, 100Å pore, higher resolution"),
    ColumnSpec("waters-hss-t3-18-21x100", "Waters", "ACQUITY UPLC HSS T3", "C18", 1.8, 100, 2.1, (2, 11), 45, "L1", "UPLC, trifunctionally bonded, 100% aqueous compatible, polar compounds"),
    ColumnSpec("waters-hss-t3-18-21x150", "Waters", "ACQUITY UPLC HSS T3", "C18", 1.8, 150, 2.1, (2, 11), 45, "L1", "UPLC, HSS T3, metabolomics standard, 100Å pore"),
    ColumnSpec("waters-hss-pfp-18-21x100", "Waters", "ACQUITY UPLC HSS PFP", "PFP", 1.8, 100, 2.1, (1, 8), 45, "L43", "UPLC, pentafluorophenyl, halogenated compounds"),

    # ACQUITY UPLC CSH (Charged Surface Hybrid, 1.7 µm)
    ColumnSpec("waters-csh-c18-17-21x100", "Waters", "ACQUITY UPLC CSH C18", "C18", 1.7, 100, 2.1, (1, 12), 60, "L1", "UPLC, charged surface hybrid, improved peak shape in low-ionic MP"),
    ColumnSpec("waters-csh-c18-17-21x150", "Waters", "ACQUITY UPLC CSH C18", "C18", 1.7, 150, 2.1, (1, 12), 60, "L1", "UPLC, CSH, lipidomics standard, 130Å pore"),
    ColumnSpec("waters-csh-phenyl-hexyl-17-21x100", "Waters", "ACQUITY UPLC CSH Phenyl-Hexyl", "phenyl", 1.7, 100, 2.1, (1, 12), 60, "L11", "UPLC, CSH phenyl-hexyl, charged surface, aromatic selectivity"),
    ColumnSpec("waters-csh-fluoro-phenyl-17-21x100", "Waters", "ACQUITY UPLC CSH Fluoro-Phenyl", "PFP", 1.7, 100, 2.1, (1, 12), 50, "L43", "UPLC, CSH fluoro-phenyl, alternate selectivity"),

    # Atlantis PREMIER BEH Z-HILIC
    ColumnSpec("waters-atlantis-premier-beh-z-hilic-17-21x100", "Waters", "Atlantis Premier BEH Z-HILIC", "HILIC", 1.7, 100, 2.1, (1, 12), 60, "L3", "UPLC, sulfobetaine zwitterionic, low-adsorption hardware, metabolomics"),

    # XBridge (HPLC, BEH, 3.5 µm / 5 µm, pH 1-12, up to 90°C)
    ColumnSpec("waters-xbridge-c18-35-46x100", "Waters", "XBridge BEH C18", "C18", 3.5, 100, 4.6, (1, 12), 90, "L1", "HPLC, BEH hybrid, 130Å pore, high pH stable, up to 90°C"),
    ColumnSpec("waters-xbridge-c18-35-46x150", "Waters", "XBridge BEH C18", "C18", 3.5, 150, 4.6, (1, 12), 90, "L1", "HPLC, BEH hybrid, 130Å pore, high pH, high temp"),
    ColumnSpec("waters-xbridge-c18-50-46x250", "Waters", "XBridge BEH C18", "C18", 5.0, 250, 4.6, (1, 12), 90, "L1", "HPLC, conventional, BEH hybrid, 130Å pore"),
    ColumnSpec("waters-xbridge-phenyl-35-46x150", "Waters", "XBridge BEH Phenyl", "phenyl", 3.5, 150, 4.6, (1, 12), 90, "L11", "HPLC, BEH phenyl, aromatic selectivity, high pH"),
    ColumnSpec("waters-xbridge-hilic-35-46x150", "Waters", "XBridge BEH HILIC", "HILIC", 3.5, 150, 4.6, (1, 12), 45, "L3", "HPLC, BEH HILIC, 130Å pore, polar compounds"),

    # XSelect (HPLC, CSH, 3.5 µm / 5 µm)
    ColumnSpec("waters-xselect-csh-c18-35-46x150", "Waters", "XSelect CSH C18", "C18", 3.5, 150, 4.6, (1, 12), 90, "L1", "HPLC, CSH charged surface, improved peak shape, 130Å pore"),
    ColumnSpec("waters-xselect-csh-phenyl-hexyl-35-46x150", "Waters", "XSelect CSH Phenyl-Hexyl", "phenyl", 3.5, 150, 4.6, (1, 12), 90, "L11", "HPLC, CSH phenyl-hexyl, charged surface"),

    # =========================================================================
    # Phenomenex
    # =========================================================================
    ColumnSpec("phenomenex-kinetex-c18-26-21x100", "Phenomenex", "Kinetex C18", "C18", 2.6, 100, 2.1, (1.5, 10), 60, "L1", "Core-shell 2.6µm, 100Å pore, 200 m²/g, high efficiency"),
    ColumnSpec("phenomenex-kinetex-c18-26-46x150", "Phenomenex", "Kinetex C18", "C18", 2.6, 150, 4.6, (1.5, 10), 60, "L1", "Core-shell HPLC, 100Å pore, 200 m²/g"),
    ColumnSpec("phenomenex-kinetex-c18-16-21x100", "Phenomenex", "Kinetex XB-C18", "C18", 1.7, 100, 2.1, (1.5, 10), 60, "L1", "UHPLC core-shell 1.7µm, extended pH, 100Å pore"),
    ColumnSpec("phenomenex-kinetex-biphenyl-26-21x100", "Phenomenex", "Kinetex Biphenyl", "phenyl", 2.6, 100, 2.1, (1.5, 10), 60, "L11", "Core-shell biphenyl, enhanced aromatic selectivity, PAHs/drugs"),
    ColumnSpec("phenomenex-kinetex-f5-26-21x100", "Phenomenex", "Kinetex F5", "PFP", 2.6, 100, 2.1, (1.5, 10), 50, "L43", "Core-shell pentafluorophenyl, positional isomers"),
    ColumnSpec("phenomenex-kinetex-hilic-26-21x150", "Phenomenex", "Kinetex HILIC", "HILIC", 2.6, 150, 2.1, (2, 8), 40, "L3", "Core-shell HILIC, 100Å pore, polar metabolites"),
    ColumnSpec("phenomenex-luna-c18-30-46x150", "Phenomenex", "Luna C18(2)", "C18", 3.0, 150, 4.6, (1.5, 10), 60, "L1", "Fully porous, 100Å pore, 400 m²/g, general purpose"),
    ColumnSpec("phenomenex-luna-c18-50-46x250", "Phenomenex", "Luna C18(2)", "C18", 5.0, 250, 4.6, (1.5, 10), 60, "L1", "Fully porous, conventional HPLC, 100Å pore"),
    ColumnSpec("phenomenex-luna-omega-c18-30-21x100", "Phenomenex", "Luna Omega C18", "C18", 3.0, 100, 2.1, (1.5, 12), 60, "L1", "Fully porous, polar endcapped, 110Å pore, 21st century silica"),
    ColumnSpec("phenomenex-luna-phenyl-hexyl-30-46x150", "Phenomenex", "Luna Phenyl-Hexyl", "phenyl", 3.0, 150, 4.6, (1.5, 10), 60, "L11", "Fully porous, phenyl-hexyl, 100Å pore"),

    # =========================================================================
    # Restek
    # =========================================================================
    ColumnSpec("restek-arc-c18-27-21x100", "Restek", "ARC C18", "C18", 2.7, 100, 2.1, (1.5, 10), 60, "L1", "Core-shell 2.7µm, LC-MS optimized, 160Å pore"),
    ColumnSpec("restek-biphenyl-26-21x100", "Restek", "Biphenyl", "phenyl", 2.6, 100, 2.1, (1.5, 10), 60, "L11", "Core-shell biphenyl, enhanced aromatic selectivity, PAHs/drugs"),
    ColumnSpec("restek-biphenyl-26-46x150", "Restek", "Biphenyl", "phenyl", 2.6, 150, 4.6, (1.5, 10), 60, "L11", "Core-shell biphenyl, analytical scale"),
    ColumnSpec("restek-arc-18-27-21x100", "Restek", "ARC-18", "C18", 2.7, 100, 2.1, (1.5, 10), 60, "L1", "Core-shell, 160Å pore, 90 m²/g, LC-MS optimized"),

    # =========================================================================
    # Shimadzu
    # =========================================================================
    ColumnSpec("shimadzu-shim-pack-giss-c18-19-21x100", "Shimadzu", "Shim-pack GISS C18", "C18", 1.9, 100, 2.1, (2, 8), 50, "L1", "UHPLC, low bleed for MS, 120Å pore"),
    ColumnSpec("shimadzu-shim-pack-ods-iii-30-46x150", "Shimadzu", "Shim-pack ODS-III", "C18", 3.0, 150, 4.6, (2, 8), 50, "L1", "HPLC, general purpose, 150Å pore"),

    # =========================================================================
    # Specialty / Ion-pair
    # =========================================================================
    ColumnSpec("thermo-dionex-ionpac-ns-30-21x150", "Thermo Fisher", "IonPac NS", "ion_pair", 3.0, 150, 2.1, (2, 12), 60, None, "Ion-pair compatible, charged surfactants"),
]


def list_columns(
    chemistry: str | None = None,
    brand: str | None = None,
    limit: int = 100,
) -> list[ColumnSpec]:
    """List columns, optionally filtered."""
    result = _COLUMNS
    if chemistry:
        result = [c for c in result if c.chemistry == chemistry]
    if brand:
        result = [c for c in result if c.brand.lower() == brand.lower()]
    return result[:limit]


def get_column(column_id: str) -> ColumnSpec | None:
    """Get a single column by ID."""
    for c in _COLUMNS:
        if c.id == column_id:
            return c
    return None


def column_to_dict(c: ColumnSpec) -> dict[str, Any]:
    return {
        "id": c.id,
        "brand": c.brand,
        "name": c.name,
        "chemistry": c.chemistry,
        "particle_size_um": c.particle_size_um,
        "length_mm": c.length_mm,
        "inner_diameter_mm": c.inner_diameter_mm,
        "ph_min": c.ph_range[0],
        "ph_max": c.ph_range[1],
        "temperature_max_c": c.temperature_max_c,
        "usp_code": c.usp_code,
        "notes": c.notes,
    }


def get_brands() -> list[str]:
    """Return unique brand names."""
    return sorted({c.brand for c in _COLUMNS})


def get_chemistries() -> list[str]:
    """Return unique chemistry types."""
    return sorted({c.chemistry for c in _COLUMNS})
