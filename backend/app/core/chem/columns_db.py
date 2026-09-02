"""Commercial column database — comprehensive reference data from manufacturer specs.

Uses a generator approach: each column "family" is defined once with its chemistry,
pH range, temperature, USP code, and notes. Standard particle-size / length /
inner-diameter variants are then generated automatically.

Sources: Thermo Fisher, Agilent, Waters, Phenomenex, Restek, Shimadzu
product documentation (2024-2025). Focus: small-molecule analysis columns.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StationaryPhase:
    """Detailed stationary phase composition for retention modeling.

    Attributes are derived from manufacturer specification sheets and
    published chromatographic literature. Values represent typical
    production specifications; actual lots may vary ±10%.
    """
    carbon_load_pct: float          # % carbon by weight (e.g., 18.0 for C18)
    ligand_length: int              # carbon chain length of primary ligand (C18=18, C8=8, C4=4, phenyl=6, PFP=6, HILIC=0)
    bonding_density_umol_m2: float  # bonding density (µmol/m²), typically 1.5-4.0
    surface_area_m2_g: float        # specific surface area (m²/g)
    pore_size_a: float              # average pore diameter (Å)
    endcapped: bool                 # whether the phase is endcapped
    polar_embedded: bool            # has polar embedded group (e.g., AQ, Shield)
    particle_type: str              # "fully_porous", "core_shell", "hybrid", "graphitic"
    base_material: str              # "silica", "hybrid_silica", "organic_polymer", "graphitic_carbon"
    # Normalized ligand hydrophobicity (C18=1.0 reference)
    # C8=0.56, C4=0.33, phenyl=0.39, PFP=0.33, C30=1.67, HILIC=0.0, PGC=2.0
    hydrophobicity_index: float


# Ligand hydrophobicity indices (normalized to C18 = 1.0)
_LIGAND_HYDRO = {
    "C18": 1.0, "C8": 0.56, "C4": 0.33, "C30": 1.67,
    "phenyl": 0.39, "PFP": 0.33, "HILIC": 0.0, "PGC": 2.0,
    "ion_pair": 0.5,
}


@dataclass(frozen=True)
class ColumnSpec:
    id: str
    brand: str
    name: str
    chemistry: str
    particle_size_um: float
    length_mm: int
    inner_diameter_mm: float
    ph_range: tuple[float, float]
    temperature_max_c: int
    usp_code: str | None
    notes: str
    phase: StationaryPhase | None = None


# ---------------------------------------------------------------------------
# Dimension presets — standard configurations offered by manufacturers
# ---------------------------------------------------------------------------

# UHPLC / UPLC dimensions (sub-2-micron and core-shell ~1.5-1.9 µm)
_UHPLC_DIMS: list[tuple[int, float]] = [
    (30, 2.1), (50, 2.1), (75, 2.1), (100, 2.1), (150, 2.1),
    (50, 3.0), (100, 3.0), (150, 3.0),
    (50, 4.6), (100, 4.6), (150, 4.6),
]

# Core-shell / SFC dimensions (2.6-2.7 µm)
_CORESHELL_DIMS: list[tuple[int, float]] = [
    (30, 2.1), (50, 2.1), (75, 2.1), (100, 2.1), (150, 2.1),
    (50, 3.0), (100, 3.0), (150, 3.0),
    (50, 4.6), (100, 4.6), (150, 4.6), (250, 4.6),
]

# HPLC dimensions (3.0-3.5 µm)
_HPLC_DIMS: list[tuple[int, float]] = [
    (50, 2.1), (100, 2.1), (150, 2.1),
    (50, 3.0), (100, 3.0), (150, 3.0),
    (50, 4.6), (100, 4.6), (150, 4.6), (250, 4.6),
]

# Conventional HPLC dimensions (5 µm)
_CONV_DIMS: list[tuple[int, float]] = [
    (100, 2.1), (150, 2.1),
    (100, 3.0), (150, 3.0), (250, 3.0),
    (100, 4.6), (150, 4.6), (250, 4.6),
    (150, 10.0), (250, 10.0),  # semi-prep
]

# HILIC often uses longer columns
_HILIC_DIMS: list[tuple[int, float]] = [
    (50, 2.1), (100, 2.1), (150, 2.1),
    (100, 3.0), (150, 3.0),
    (100, 4.6), (150, 4.6),
]

# Narrow HILIC set for core-shell HILIC
_HILIC_CORESHELL_DIMS: list[tuple[int, float]] = [
    (50, 2.1), (100, 2.1), (150, 2.1),
    (100, 4.6), (150, 4.6),
]


@dataclass(frozen=True)
class ColumnFamily:
    """Definition of a column product line with its base properties."""
    brand: str
    name: str
    chemistry: str
    ph_range: tuple[float, float]
    temp_max_c: int
    usp_code: str | None
    notes: str
    variants: dict[float, list[tuple[int, float]]]
    phase: StationaryPhase | None = None


def _gen_columns(fam: ColumnFamily) -> list[ColumnSpec]:
    """Generate all ColumnSpec entries for a family."""
    cols: list[ColumnSpec] = []
    for psize, dims in fam.variants.items():
        for length, id_mm in dims:
            p_str = str(psize).replace(".", "")
            id_str = str(id_mm).replace(".", "")
            cid = f"{fam.brand.lower().replace(' ', '-')}-{fam.name.lower().replace(' ', '-').replace('/', '-').replace('+', 'plus')}-{p_str}-{id_str}x{length}"
            cols.append(ColumnSpec(
                id=cid,
                brand=fam.brand,
                name=fam.name,
                chemistry=fam.chemistry,
                particle_size_um=psize,
                length_mm=length,
                inner_diameter_mm=id_mm,
                ph_range=fam.ph_range,
                temperature_max_c=fam.temp_max_c,
                usp_code=fam.usp_code,
                notes=fam.notes,
                phase=fam.phase,
            ))
    return cols


# ---------------------------------------------------------------------------
# Column family definitions
# ---------------------------------------------------------------------------

_FAMILIES: list[ColumnFamily] = [

    # =======================================================================
    # THERMO FISHER
    # =======================================================================

    ColumnFamily("Thermo Fisher", "Hypersil GOLD VANQUISH C18", "C18",
        (1, 11), 60, "L1",
        "UHPLC, ultrapure silica, 175Å pore, 220 m²/g, max 1000 bar, endcapped",
        {1.9: _UHPLC_DIMS}),

    ColumnFamily("Thermo Fisher", "Hypersil GOLD VANQUISH C8", "C8",
        (1, 11), 60, "L7",
        "UHPLC, ultrapure silica, 175Å pore, less retentive than C18, endcapped",
        {1.9: _UHPLC_DIMS}),

    ColumnFamily("Thermo Fisher", "Hypersil GOLD VANQUISH aQ", "C18",
        (1, 11), 60, "L1",
        "UHPLC, 100% aqueous compatible, polar embedded, 175Å pore",
        {1.9: _UHPLC_DIMS}),

    ColumnFamily("Thermo Fisher", "Hypersil GOLD VANQUISH PFP", "PFP",
        (1, 10), 50, "L43",
        "UHPLC, pentafluorophenyl, halogenated/aromatic selectivity, 175Å pore",
        {1.9: _UHPLC_DIMS}),

    ColumnFamily("Thermo Fisher", "Hypersil GOLD VANQUISH Phenyl", "phenyl",
        (1, 10), 50, "L11",
        "UHPLC, phenyl selectivity, pi-pi interactions, 175Å pore",
        {1.9: _UHPLC_DIMS}),

    ColumnFamily("Thermo Fisher", "Hypersil GOLD C18", "C18",
        (1, 11), 50, "L1",
        "HPLC, high purity silica, 175Å pore, 220 m²/g, endcapped",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Thermo Fisher", "Hypersil GOLD C8", "C8",
        (1, 11), 50, "L7",
        "HPLC, high purity silica, less retention than C18, 175Å pore",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Thermo Fisher", "Hypersil GOLD aQ", "C18",
        (1, 11), 50, "L1",
        "HPLC, 100% aqueous compatible, polar embedded",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Thermo Fisher", "Hypersil GOLD Phenyl", "phenyl",
        (1, 10), 50, "L11",
        "HPLC, aromatic selectivity, 175Å pore",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Thermo Fisher", "Hypersil GOLD PFP", "PFP",
        (1, 10), 50, "L43",
        "HPLC, pentafluorophenyl, positional isomer selectivity",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    # Accucore VANQUISH (solid core 1.5 µm, UHPLC)
    ColumnFamily("Thermo Fisher", "Accucore VANQUISH C18+", "C18",
        (2, 9), 60, "L1",
        "UHPLC solid core 1.5µm, 80Å pore, 110 m²/g, max 1500 bar",
        {1.5: _UHPLC_DIMS}),

    # Accucore (solid core 2.6 µm)
    ColumnFamily("Thermo Fisher", "Accucore C18", "C18",
        (1, 11), 60, "L1",
        "Solid core 2.6µm, 80Å pore, 130 m²/g, core-shell efficiency",
        {2.6: _CORESHELL_DIMS}),

    ColumnFamily("Thermo Fisher", "Accucore RP-MS", "C18",
        (2, 9), 60, None,
        "Solid core 2.6µm, LC-MS optimized, low bleed, 80Å pore",
        {2.6: _CORESHELL_DIMS}),

    ColumnFamily("Thermo Fisher", "Accucore aQ", "C18",
        (2, 9), 60, "L1",
        "Solid core 2.6µm, 100% aqueous compatible, polar compounds",
        {2.6: _CORESHELL_DIMS}),

    ColumnFamily("Thermo Fisher", "Accucore C8", "C8",
        (2, 9), 60, "L7",
        "Solid core 2.6µm, less retentive, fast elution, 80Å pore",
        {2.6: _CORESHELL_DIMS}),

    ColumnFamily("Thermo Fisher", "Accucore Phenyl-Hexyl", "phenyl",
        (2, 8), 50, "L11",
        "Solid core 2.6µm, phenyl-hexyl, aromatic selectivity",
        {2.6: _CORESHELL_DIMS}),

    ColumnFamily("Thermo Fisher", "Accucore PFP", "PFP",
        (2, 8), 50, "L43",
        "Solid core 2.6µm, pentafluorophenyl, positional isomer separation",
        {2.6: _CORESHELL_DIMS}),

    ColumnFamily("Thermo Fisher", "Accucore Polar Premium", "C18",
        (1.5, 10.5), 50, "L60",
        "Solid core 2.6µm, polar embedded, 100% aqueous stable",
        {2.6: _CORESHELL_DIMS}),

    ColumnFamily("Thermo Fisher", "Accucore HILIC", "HILIC",
        (2, 8), 40, "L3",
        "Solid core 2.6µm HILIC, 150Å pore, polar metabolites",
        {2.6: _HILIC_CORESHELL_DIMS}),

    ColumnFamily("Thermo Fisher", "Accucore 150 Amide HILIC", "HILIC",
        (2, 8), 40, None,
        "Solid core 2.6µm, amide-bonded HILIC, 150Å pore for large polar metabolites",
        {2.6: _HILIC_CORESHELL_DIMS}),

    ColumnFamily("Thermo Fisher", "Accucore C30", "C30",
        (2, 8), 50, "L62",
        "Solid core 2.6µm C30, carotenoids, fat-soluble vitamins, shape selectivity",
        {2.6: _CORESHELL_DIMS}),

    # Acclaim VANQUISH (fully porous 2.2 µm UHPLC)
    ColumnFamily("Thermo Fisher", "Acclaim VANQUISH C18", "C18",
        (2, 9), 60, "L1",
        "UHPLC, high carbon load, 120Å pore, basic compounds",
        {2.2: _UHPLC_DIMS}),

    ColumnFamily("Thermo Fisher", "Acclaim VANQUISH PA2", "C18",
        (1.5, 10), 60, "L1",
        "UHPLC, polar-endcapped, multi-mode interactions, 120Å pore",
        {2.2: _UHPLC_DIMS}),

    # Acclaim (HPLC 3/5 µm)
    ColumnFamily("Thermo Fisher", "Acclaim 120 C18", "C18",
        (2, 9), 60, "L1",
        "HPLC, 120Å pore, high carbon load, basic compounds",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Thermo Fisher", "Acclaim 120 C8", "C8",
        (2, 9), 60, "L7",
        "HPLC, 120Å pore, less retentive than C18",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Thermo Fisher", "Acclaim Mixed-Mode HILIC", "HILIC",
        (2, 7), 40, None,
        "HILIC + ion-exchange, charged polar compounds, 120Å pore",
        {3.0: _HILIC_DIMS}),

    # Hypercarb (Porous Graphitic Carbon)
    ColumnFamily("Thermo Fisher", "Hypercarb PGC", "PGC",
        (1, 14), 150, None,
        "Porous graphitic carbon, extreme pH/temp, polar compound retention",
        {5.0: [(30, 2.1), (50, 2.1), (100, 2.1), (150, 2.1), (100, 4.6), (150, 4.6)]}),

    # =======================================================================
    # AGILENT
    # =======================================================================

    ColumnFamily("Agilent", "ZORBAX RRHD Eclipse Plus C18", "C18",
        (2, 9), 60, "L1",
        "UHPLC 1.8µm, 95Å pore, 160 m²/g, 9% carbon, double endcapped, max 1200 bar",
        {1.8: _UHPLC_DIMS}),

    ColumnFamily("Agilent", "ZORBAX RRHD Eclipse Plus C8", "C8",
        (2, 9), 60, "L7",
        "UHPLC 1.8µm, 95Å pore, 7% carbon, double endcapped, less retentive",
        {1.8: _UHPLC_DIMS}),

    ColumnFamily("Agilent", "ZORBAX RRHD Eclipse Plus Phenyl-Hexyl", "phenyl",
        (2, 9), 60, "L11",
        "UHPLC 1.8µm, 95Å pore, phenyl-hexyl, aromatic selectivity",
        {1.8: _UHPLC_DIMS}),

    ColumnFamily("Agilent", "ZORBAX Eclipse Plus C18", "C18",
        (2, 9), 60, "L1",
        "HPLC, 95Å pore, double endcapped, good peak shape for bases",
        {3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Agilent", "ZORBAX Eclipse Plus C8", "C8",
        (2, 9), 60, "L7",
        "HPLC, 95Å pore, double endcapped, less retentive",
        {3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Agilent", "ZORBAX Eclipse Plus Phenyl-Hexyl", "phenyl",
        (2, 9), 60, "L11",
        "HPLC, 95Å pore, phenyl-hexyl, aromatic selectivity",
        {3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    # ZORBAX SB (StableBond, low pH)
    ColumnFamily("Agilent", "ZORBAX SB-C18", "C18",
        (1, 8), 60, "L1",
        "StableBond, low pH optimized, 80Å pore, monofunctional, sterically protected",
        {1.8: _UHPLC_DIMS, 3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Agilent", "ZORBAX SB-C8", "C8",
        (1, 8), 60, "L7",
        "StableBond C8, low pH, 80Å pore, less retentive",
        {1.8: _UHPLC_DIMS, 3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Agilent", "ZORBAX SB-Aq", "C18",
        (1, 8), 60, "L1",
        "StableBond, 100% aqueous, polar compounds, 80Å pore",
        {1.8: _UHPLC_DIMS, 3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Agilent", "ZORBAX SB-Phenyl", "phenyl",
        (1, 8), 60, "L11",
        "StableBond phenyl, aromatic selectivity, 80Å pore",
        {1.8: _UHPLC_DIMS, 3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    # ZORBAX Extend-C18 (high pH)
    ColumnFamily("Agilent", "ZORBAX Extend-C18", "C18",
        (2, 11.5), 60, "L1",
        "High pH stable, bidentate bonding, 80Å pore, basic compounds at high pH",
        {1.8: _UHPLC_DIMS, 3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    # ZORBAX Eclipse XDB (extra dense bonding)
    ColumnFamily("Agilent", "ZORBAX Eclipse XDB-C18", "C18",
        (2, 9), 60, "L1",
        "Extra dense bonding, 95Å pore, 8% carbon, double endcapped",
        {1.8: _UHPLC_DIMS, 3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Agilent", "ZORBAX Eclipse XDB-C8", "C8",
        (2, 9), 60, "L7",
        "Extra dense bonding, 95Å pore, less retentive",
        {1.8: _UHPLC_DIMS, 3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Agilent", "ZORBAX Eclipse XDB-Phenyl", "phenyl",
        (2, 9), 60, "L11",
        "Extra dense bonding, 95Å pore, phenyl selectivity",
        {3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Agilent", "ZORBAX Eclipse XDB-C18-80", "C18",
        (2, 9), 60, "L1",
        "Extra dense bonding, 80Å pore wide-pore variant, proteins/peptides",
        {3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    # Poroshell 120 (solid core 2.7 µm, 120Å)
    ColumnFamily("Agilent", "Poroshell 120 EC-C18", "C18",
        (2, 9), 60, "L1",
        "Solid core 2.7µm, 120Å pore, 90 m²/g, endcapped, HPLC efficiency",
        {2.7: _CORESHELL_DIMS}),

    ColumnFamily("Agilent", "Poroshell 120 SB-C18", "C18",
        (1, 8), 60, "L1",
        "Solid core 2.7µm, StableBond, low pH optimized, 120Å pore",
        {2.7: _CORESHELL_DIMS}),

    ColumnFamily("Agilent", "Poroshell 120 HPH-C18", "C18",
        (2, 11), 60, "L1",
        "Solid core 2.7µm, high pH hybrid, 120Å pore, bidentate",
        {2.7: _CORESHELL_DIMS}),

    ColumnFamily("Agilent", "Poroshell 120 EC-C8", "C8",
        (2, 9), 60, "L7",
        "Solid core 2.7µm, 120Å pore, less retentive, endcapped",
        {2.7: _CORESHELL_DIMS}),

    ColumnFamily("Agilent", "Poroshell 120 Phenyl-Hexyl", "phenyl",
        (2, 9), 60, "L11",
        "Solid core 2.7µm, phenyl-hexyl, aromatic selectivity, 120Å pore",
        {2.7: _CORESHELL_DIMS}),

    ColumnFamily("Agilent", "Poroshell 120 PFP", "PFP",
        (2, 8), 50, "L43",
        "Solid core 2.7µm, pentafluorophenyl, positional isomers, 120Å pore",
        {2.7: _CORESHELL_DIMS}),

    ColumnFamily("Agilent", "Poroshell 120 HILIC-Z", "HILIC",
        (2, 9), 40, None,
        "Solid core 2.7µm HILIC, zwitterionic phase, polar metabolites, 120Å pore",
        {2.7: _HILIC_CORESHELL_DIMS}),

    ColumnFamily("Agilent", "Poroshell 120 Bonus-RP", "C18",
        (2, 9), 60, "L60",
        "Solid core 2.7µm, polar embedded amide, 100% aqueous stable, 120Å pore",
        {2.7: _CORESHELL_DIMS}),

    # InfinityLab Poroshell 120 specialty
    ColumnFamily("Agilent", "InfinityLab Poroshell HILIC-Z", "HILIC",
        (2, 9), 40, None,
        "PEEK-lined, zwitterionic, polar metabolomics, vitamins, nucleotides",
        {2.7: _HILIC_CORESHELL_DIMS}),

    # =======================================================================
    # WATERS
    # =======================================================================

    # ACQUITY UPLC BEH (1.7 µm, hybrid silica, pH 1-12)
    ColumnFamily("Waters", "ACQUITY UPLC BEH C18", "C18",
        (1, 12), 60, "L1",
        "UPLC, BEH hybrid, 130Å pore, 185 m²/g, 18% carbon, max 18000 psi",
        {1.7: _UHPLC_DIMS}),

    ColumnFamily("Waters", "ACQUITY UPLC BEH C8", "C8",
        (1, 12), 60, "L7",
        "UPLC, BEH C8, 130Å pore, less retentive, 13% carbon",
        {1.7: _UHPLC_DIMS}),

    ColumnFamily("Waters", "ACQUITY UPLC BEH Shield RP18", "C18",
        (1, 12), 60, "L1",
        "UPLC, BEH hybrid, polar embedded group, alternate selectivity, 130Å pore",
        {1.7: _UHPLC_DIMS}),

    ColumnFamily("Waters", "ACQUITY UPLC BEH Phenyl", "phenyl",
        (1, 12), 60, "L11",
        "UPLC, BEH phenyl, aromatic selectivity, pi-pi, 130Å pore",
        {1.7: _UHPLC_DIMS}),

    ColumnFamily("Waters", "ACQUITY UPLC BEH Amide", "HILIC",
        (1, 12), 60, None,
        "UPLC, amide-bonded HILIC, 130Å pore, polar metabolites, sugars",
        {1.7: _HILIC_CORESHELL_DIMS}),

    ColumnFamily("Waters", "ACQUITY UPLC BEH HILIC", "HILIC",
        (1, 12), 45, "L3",
        "UPLC, unbonded BEH HILIC, 130Å pore, sugars/nucleotides",
        {1.7: _HILIC_CORESHELL_DIMS}),

    # ACQUITY UPLC HSS (1.8 µm, pH 1-8)
    ColumnFamily("Waters", "ACQUITY UPLC HSS C18", "C18",
        (1, 8), 45, "L1",
        "UPLC, HSS silica, 100Å pore, 230 m²/g, 15% carbon, max 18000 psi",
        {1.8: _UHPLC_DIMS}),

    ColumnFamily("Waters", "ACQUITY UPLC HSS C18 SB", "C18",
        (1, 8), 45, "L1",
        "UPLC, HSS silica, low surface coverage, less retentive, 100Å pore",
        {1.8: _UHPLC_DIMS}),

    ColumnFamily("Waters", "ACQUITY UPLC HSS T3", "C18",
        (2, 11), 45, "L1",
        "UPLC, trifunctionally bonded, 100% aqueous compatible, polar compounds, 100Å pore",
        {1.8: _UHPLC_DIMS}),

    ColumnFamily("Waters", "ACQUITY UPLC HSS PFP", "PFP",
        (1, 8), 45, "L43",
        "UPLC, HSS pentafluorophenyl, halogenated/aromatic compounds, 100Å pore",
        {1.8: _UHPLC_DIMS}),

    # ACQUITY UPLC CSH (1.7 µm, charged surface hybrid)
    ColumnFamily("Waters", "ACQUITY UPLC CSH C18", "C18",
        (1, 12), 60, "L1",
        "UPLC, charged surface hybrid, improved peak shape in low-ionic MP, 130Å pore",
        {1.7: _UHPLC_DIMS}),

    ColumnFamily("Waters", "ACQUITY UPLC CSH C8", "C8",
        (1, 12), 60, "L7",
        "UPLC, CSH C8, charged surface, less retentive, 130Å pore",
        {1.7: _UHPLC_DIMS}),

    ColumnFamily("Waters", "ACQUITY UPLC CSH Phenyl-Hexyl", "phenyl",
        (1, 12), 60, "L11",
        "UPLC, CSH phenyl-hexyl, charged surface, aromatic selectivity, 130Å pore",
        {1.7: _UHPLC_DIMS}),

    ColumnFamily("Waters", "ACQUITY UPLC CSH Fluoro-Phenyl", "PFP",
        (1, 12), 50, "L43",
        "UPLC, CSH fluoro-phenyl, alternate selectivity, 130Å pore",
        {1.7: _UHPLC_DIMS}),

    # ACQUITY Premier BEH (1.7 µm, low-adsorption MaxPeak hardware)
    ColumnFamily("Waters", "ACQUITY Premier BEH C18", "C18",
        (1, 12), 60, "L1",
        "Premier UPLC, BEH hybrid, MaxPeak low-adsorption hardware, 130Å pore, 18% carbon",
        {1.7: _UHPLC_DIMS}),

    ColumnFamily("Waters", "ACQUITY Premier BEH C8", "C8",
        (1, 12), 60, "L7",
        "Premier UPLC, BEH C8, MaxPeak hardware, less retentive, 130Å pore",
        {1.7: _UHPLC_DIMS}),

    ColumnFamily("Waters", "ACQUITY Premier BEH Shield RP18", "C18",
        (1, 12), 60, "L1",
        "Premier UPLC, BEH Shield, polar embedded, MaxPeak hardware, 130Å pore",
        {1.7: _UHPLC_DIMS}),

    ColumnFamily("Waters", "ACQUITY Premier BEH Phenyl", "phenyl",
        (1, 12), 60, "L11",
        "Premier UPLC, BEH Phenyl, MaxPeak hardware, aromatic selectivity, 130Å pore",
        {1.7: _UHPLC_DIMS}),

    ColumnFamily("Waters", "ACQUITY Premier CSH C18", "C18",
        (1, 12), 60, "L1",
        "Premier UPLC, CSH charged surface, MaxPeak hardware, 130Å pore",
        {1.7: _UHPLC_DIMS}),

    ColumnFamily("Waters", "ACQUITY Premier HSS T3", "C18",
        (2, 11), 45, "L1",
        "Premier UPLC, HSS T3, 100% aqueous, MaxPeak hardware, 100Å pore",
        {1.8: _UHPLC_DIMS}),

    # Atlantis Premier
    ColumnFamily("Waters", "Atlantis Premier BEH Z-HILIC", "HILIC",
        (1, 12), 60, "L3",
        "UPLC, sulfobetaine zwitterionic, MaxPeak low-adsorption hardware, metabolomics",
        {1.7: _HILIC_CORESHELL_DIMS}),

    ColumnFamily("Waters", "Atlantis Premier BEH C18 AX", "C18",
        (1, 12), 60, "L1",
        "Premier, BEH C18 with anion-exchange, mixed-mode for acidic compounds, 130Å pore",
        {1.7: _UHPLC_DIMS}),

    # XBridge (HPLC, BEH, 3.5/5 µm, pH 1-12, up to 90°C)
    ColumnFamily("Waters", "XBridge BEH C18", "C18",
        (1, 12), 90, "L1",
        "HPLC, BEH hybrid, 130Å pore, high pH stable, up to 90°C, 18% carbon",
        {3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Waters", "XBridge BEH C8", "C8",
        (1, 12), 90, "L7",
        "HPLC, BEH C8, 130Å pore, less retentive, high pH stable",
        {3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Waters", "XBridge BEH Shield RP18", "C18",
        (1, 12), 90, "L1",
        "HPLC, BEH Shield, polar embedded, alternate selectivity, 130Å pore",
        {3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Waters", "XBridge BEH Phenyl", "phenyl",
        (1, 12), 90, "L11",
        "HPLC, BEH phenyl, aromatic selectivity, high pH, 130Å pore",
        {3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Waters", "XBridge BEH HILIC", "HILIC",
        (1, 12), 45, "L3",
        "HPLC, BEH HILIC, 130Å pore, polar compounds, sugars",
        {3.5: _HILIC_DIMS, 5.0: _HILIC_DIMS}),

    # XSelect (HPLC, CSH, 3.5/5 µm)
    ColumnFamily("Waters", "XSelect CSH C18", "C18",
        (1, 12), 90, "L1",
        "HPLC, CSH charged surface, improved peak shape, 130Å pore, 18% carbon",
        {3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Waters", "XSelect CSH C8", "C8",
        (1, 12), 90, "L7",
        "HPLC, CSH C8, charged surface, less retentive, 130Å pore",
        {3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Waters", "XSelect CSH Phenyl-Hexyl", "phenyl",
        (1, 12), 90, "L11",
        "HPLC, CSH phenyl-hexyl, charged surface, aromatic selectivity, 130Å pore",
        {3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Waters", "XSelect CSH Fluoro-Phenyl", "PFP",
        (1, 12), 50, "L43",
        "HPLC, CSH fluoro-phenyl, alternate selectivity, 130Å pore",
        {3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Waters", "XSelect HSS T3", "C18",
        (2, 11), 45, "L1",
        "HPLC, HSS T3, 100% aqueous compatible, polar compounds, 100Å pore",
        {3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Waters", "XSelect HSS PFP", "PFP",
        (1, 8), 45, "L43",
        "HPLC, HSS pentafluorophenyl, halogenated compounds, 100Å pore",
        {3.5: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    # =======================================================================
    # PHENOMENEX
    # =======================================================================

    # Kinetex (core-shell)
    ColumnFamily("Phenomenex", "Kinetex C18", "C18",
        (1.5, 10), 60, "L1",
        "Core-shell, 100Å pore, 200 m²/g, high efficiency, UHPLC/HPLC",
        {1.7: _UHPLC_DIMS, 2.6: _CORESHELL_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Phenomenex", "Kinetex XB-C18", "C18",
        (1.5, 10), 60, "L1",
        "Core-shell, extended pH range C18, 100Å pore, 200 m²/g",
        {1.7: _UHPLC_DIMS, 2.6: _CORESHELL_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Phenomenex", "Kinetex EVO C18", "C18",
        (1.5, 11), 60, "L1",
        "Core-shell, extended pH 1.5-11, 100Å pore, organosilica",
        {2.6: _CORESHELL_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Phenomenex", "Kinetex Biphenyl", "phenyl",
        (1.5, 10), 60, "L11",
        "Core-shell biphenyl, enhanced aromatic selectivity, PAHs/drugs, 100Å pore",
        {1.7: _UHPLC_DIMS, 2.6: _CORESHELL_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Phenomenex", "Kinetex F5", "PFP",
        (1.5, 10), 50, "L43",
        "Core-shell pentafluorophenyl, positional isomers, 100Å pore",
        {1.7: _UHPLC_DIMS, 2.6: _CORESHELL_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Phenomenex", "Kinetex HILIC", "HILIC",
        (2, 8), 40, "L3",
        "Core-shell HILIC, 100Å pore, polar metabolites",
        {2.6: _HILIC_CORESHELL_DIMS, 5.0: _HILIC_DIMS}),

    ColumnFamily("Phenomenex", "Kinetex Polar C18", "C18",
        (1.5, 10), 60, "L1",
        "Core-shell, polar endcapped, 100% aqueous stable, 100Å pore",
        {2.6: _CORESHELL_DIMS, 5.0: _CONV_DIMS}),

    # Luna (fully porous)
    ColumnFamily("Phenomenex", "Luna C18(2)", "C18",
        (1.5, 10), 60, "L1",
        "Fully porous, 100Å pore, 400 m²/g, general purpose, endcapped",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Phenomenex", "Luna C8(2)", "C8",
        (1.5, 10), 60, "L7",
        "Fully porous, 100Å pore, 400 m²/g, less retentive",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Phenomenex", "Luna Omega C18", "C18",
        (1.5, 12), 60, "L1",
        "Fully porous, polar endcapped, 110Å pore, 21st century silica",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Phenomenex", "Luna Omega PS C18", "C18",
        (1.5, 12), 60, "L1",
        "Fully porous, polar endcapped, 100% aqueous, 110Å pore",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Phenomenex", "Luna Phenyl-Hexyl", "phenyl",
        (1.5, 10), 60, "L11",
        "Fully porous, phenyl-hexyl, 100Å pore, aromatic selectivity",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Phenomenex", "Luna Omega Polar C18", "C18",
        (1.5, 12), 60, "L1",
        "Fully porous, polar endcapped for 100% aqueous, 110Å pore",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    # Gemini (wide pH)
    ColumnFamily("Phenomenex", "Gemini C18", "C18",
        (1, 12), 60, "L1",
        "Fully porous, 110Å pore, pH 1-12, organosilica, high pH stable",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Phenomenex", "Gemini-NX C18", "C18",
        (1, 12), 60, "L1",
        "Fully porous, nano-engineered, 110Å pore, pH 1-12, extended temp",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    # Synergi (polar embedded / RP)
    ColumnFamily("Phenomenex", "Synergi Polar-RP", "C18",
        (1.5, 10), 60, "L1",
        "Fully porous, polar embedded ether phase, 80Å pore, 100% aqueous",
        {4.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    # =======================================================================
    # RESTEK
    # =======================================================================

    ColumnFamily("Restek", "ARC C18", "C18",
        (1.5, 10), 60, "L1",
        "Core-shell 2.7µm, LC-MS optimized, 160Å pore, 90 m²/g",
        {2.7: _CORESHELL_DIMS}),

    ColumnFamily("Restek", "ARC-18", "C18",
        (1.5, 10), 60, "L1",
        "Core-shell 2.7µm, 160Å pore, 90 m²/g, LC-MS optimized",
        {2.7: _CORESHELL_DIMS}),

    ColumnFamily("Restek", "Biphenyl", "phenyl",
        (1.5, 10), 60, "L11",
        "Core-shell biphenyl, enhanced aromatic selectivity, PAHs/drugs",
        {2.6: _CORESHELL_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Restek", "Force C18", "C18",
        (1, 11), 60, "L1",
        "UHPLC 1.8µm, high purity silica, 100Å pore, LC-MS optimized",
        {1.8: _UHPLC_DIMS}),

    ColumnFamily("Restek", "Force Biphenyl", "phenyl",
        (1, 11), 60, "L11",
        "UHPLC 1.8µm biphenyl, enhanced aromatic selectivity, 100Å pore",
        {1.8: _UHPLC_DIMS}),

    ColumnFamily("Restek", "Raptor ARC C18", "C18",
        (1.5, 10), 60, "L1",
        "Raptor core-shell 2.7µm, 160Å pore, LC-MS, Restek flagship",
        {2.7: _CORESHELL_DIMS}),

    ColumnFamily("Restek", "Raptor Biphenyl", "phenyl",
        (1.5, 10), 60, "L11",
        "Raptor core-shell 2.7µm biphenyl, drug screening, aromatic selectivity",
        {2.7: _CORESHELL_DIMS}),

    # =======================================================================
    # SHIMADZU
    # =======================================================================

    ColumnFamily("Shimadzu", "Shim-pack GISS C18", "C18",
        (2, 8), 50, "L1",
        "UHPLC, low bleed for MS, 120Å pore, high inertness",
        {1.9: _UHPLC_DIMS}),

    ColumnFamily("Shimadzu", "Shim-pack ODS-III", "C18",
        (2, 8), 50, "L1",
        "HPLC, general purpose, 150Å pore, conventional",
        {3.0: _HPLC_DIMS, 5.0: _CONV_DIMS}),

    ColumnFamily("Shimadzu", "Shim-pack Scepter C18-120", "C18",
        (1, 10), 50, "L1",
        "UHPLC 1.9µm, hybrid silica, 120Å pore, pH 1-10, LC-MS",
        {1.9: _UHPLC_DIMS}),

    ColumnFamily("Shimadzu", "Shim-pack Scepter C18-300", "C18",
        (1, 10), 50, "L1",
        "UHPLC 1.9µm, hybrid silica, 300Å pore, biomolecules",
        {1.9: _UHPLC_DIMS}),

    ColumnFamily("Shimadzu", "Shim-pack XR-ODS III", "C18",
        (2, 8), 50, "L1",
        "UHPLC 1.6µm, 120Å pore, high speed, LC-MS",
        {1.6: _UHPLC_DIMS}),

    # =======================================================================
    # SPECIALTY
    # =======================================================================

    ColumnFamily("Thermo Fisher", "IonPac NS", "ion_pair",
        (2, 12), 60, None,
        "Ion-pair compatible, charged surfactants, ionic compounds",
        {3.0: [(50, 2.1), (100, 2.1), (150, 2.1)]}),
]


# ---------------------------------------------------------------------------
# Stationary phase composition lookup
# ---------------------------------------------------------------------------

def _infer_phase(fam: ColumnFamily) -> StationaryPhase:
    """Infer stationary phase composition from family properties.

    Uses manufacturer-published specifications. Values are typical
    production specs; actual lots may vary ±10%.
    """
    name_lower = fam.name.lower()
    chem = fam.chemistry

    # Determine base material
    if "hypercarb" in name_lower or chem == "PGC":
        return StationaryPhase(
            carbon_load_pct=100.0, ligand_length=0,
            bonding_density_umol_m2=0.0, surface_area_m2_g=120.0,
            pore_size_a=250.0, endcapped=False, polar_embedded=False,
            particle_type="graphitic", base_material="graphitic_carbon",
            hydrophobicity_index=_LIGAND_HYDRO["PGC"],
        )

    # Hybrid silica (BEH, HSS is pure silica)
    is_hybrid = any(k in name_lower for k in ["beh", "csh", "scepter", "gemini"])
    base = "hybrid_silica" if is_hybrid else "silica"

    # Core-shell detection
    is_core_shell = any(k in name_lower for k in [
        "accucore", "poroshell", "kinetex", "core", "raptor", "arc",
    ])
    particle_type = "core_shell" if is_core_shell else "fully_porous"

    # Determine pore size from notes
    notes_lower = fam.notes.lower()
    if "300å" in notes_lower or "300 å" in notes_lower:
        pore_size = 300.0
        surface_area = 80.0
    elif "175å" in notes_lower or "175 å" in notes_lower:
        pore_size = 175.0
        surface_area = 220.0
    elif "160å" in notes_lower or "160 å" in notes_lower:
        pore_size = 160.0
        surface_area = 100.0
    elif "150å" in notes_lower or "150 å" in notes_lower:
        pore_size = 150.0
        surface_area = 180.0
    elif "120å" in notes_lower or "120 å" in notes_lower:
        pore_size = 120.0
        surface_area = 175.0
    elif "100å" in notes_lower or "100 å" in notes_lower:
        pore_size = 100.0
        surface_area = 230.0 if "hss" in name_lower else 200.0
    elif "95å" in notes_lower or "95 å" in notes_lower:
        pore_size = 95.0
        surface_area = 160.0
    elif "80å" in notes_lower or "80 å" in notes_lower:
        pore_size = 80.0
        surface_area = 130.0 if is_core_shell else 180.0
    elif "110å" in notes_lower or "110 å" in notes_lower:
        pore_size = 110.0
        surface_area = 175.0
    else:
        pore_size = 120.0
        surface_area = 170.0

    # Override surface area from notes if explicitly stated
    for sa_val in [220, 230, 200, 185, 175, 160, 130, 110, 100, 90, 400]:
        if f"{sa_val} m²/g" in notes_lower or f"{sa_val} m2/g" in notes_lower:
            surface_area = float(sa_val)
            break

    # Determine ligand properties by chemistry
    endcapped = True
    polar_embedded = False

    if chem == "C18":
        ligand_length = 18
        # Carbon load varies by pore size and bonding type
        if pore_size <= 80:
            carbon_load = 9.0 if "sb" in name_lower else 10.0
        elif pore_size <= 100:
            carbon_load = 15.0 if "hss" in name_lower else 12.0
        elif pore_size <= 120:
            carbon_load = 18.0
        elif pore_size <= 175:
            carbon_load = 20.0
        else:
            carbon_load = 12.0
        # Adjust for specific brands
        if "behl" in name_lower or "beh c18" in name_lower:
            carbon_load = 18.0
        elif "eclipse plus" in name_lower and "rrhd" in name_lower:
            carbon_load = 9.0
        elif "eclipse plus" in name_lower:
            carbon_load = 8.0
        elif "sb-c18" in name_lower or "sb c18" in name_lower:
            carbon_load = 9.0
            endcapped = False  # SB is not endcapped
        elif "extend" in name_lower:
            carbon_load = 8.0
        elif "accucore" in name_lower and "vanquish" in name_lower:
            carbon_load = 9.0
        elif "accucore c18" in name_lower and "rp-ms" not in name_lower:
            carbon_load = 9.0
        elif "kinetex" in name_lower:
            carbon_load = 15.0 if "xb" not in name_lower else 16.0
        elif "luna" in name_lower and "omega" not in name_lower:
            carbon_load = 17.0
        elif "luna omega" in name_lower:
            carbon_load = 18.0
        elif "gemini" in name_lower:
            carbon_load = 16.0
        elif "synergi" in name_lower:
            carbon_load = 14.0
        elif "force" in name_lower:
            carbon_load = 12.0
        elif "shim-pack" in name_lower:
            carbon_load = 15.0
        # Bonding density
        if "sb" in name_lower:
            bonding_density = 3.5  # monofunctional, sterically protected
        elif "extend" in name_lower:
            bonding_density = 2.8  # bidentate
        else:
            bonding_density = 3.2  # typical difunctional
        hydro_idx = _LIGAND_HYDRO["C18"]

    elif chem == "C8":
        ligand_length = 8
        if pore_size <= 80:
            carbon_load = 7.0
        elif pore_size <= 120:
            carbon_load = 10.0
        else:
            carbon_load = 8.0
        if "behl" in name_lower or "beh c8" in name_lower:
            carbon_load = 13.0
        elif "eclipse" in name_lower:
            carbon_load = 7.0
        elif "sb-c8" in name_lower or "sb c8" in name_lower:
            carbon_load = 7.0
            endcapped = False
        bonding_density = 3.5
        hydro_idx = _LIGAND_HYDRO["C8"]

    elif chem == "C30":
        ligand_length = 30
        carbon_load = 12.0
        bonding_density = 1.8  # large ligand, lower density
        hydro_idx = _LIGAND_HYDRO["C30"]

    elif chem == "phenyl":
        ligand_length = 6
        carbon_load = 8.0 if pore_size <= 100 else 10.0
        if "biphenyl" in name_lower:
            carbon_load = 12.0
            ligand_length = 12  # biphenyl has two rings
        bonding_density = 3.0
        hydro_idx = _LIGAND_HYDRO["phenyl"]
        if "biphenyl" in name_lower:
            hydro_idx = 0.55  # biphenyl is more retentive than phenyl

    elif chem == "PFP":
        ligand_length = 6
        carbon_load = 8.0
        bonding_density = 2.8
        hydro_idx = _LIGAND_HYDRO["PFP"]

    elif chem == "HILIC":
        ligand_length = 0
        carbon_load = 0.0
        bonding_density = 0.0
        if "amide" in name_lower:
            bonding_density = 2.5
            hydro_idx = -0.3
        elif "z-hilic" in name_lower or "hilic-z" in name_lower:
            bonding_density = 2.0
            hydro_idx = -0.4
        else:
            hydro_idx = _LIGAND_HYDRO["HILIC"]
        endcapped = False
        # HILIC phases have different surface area considerations
        if "150" in name_lower and "amide" in name_lower:
            pore_size = 150.0
            surface_area = 100.0

    elif chem == "ion_pair":
        ligand_length = 0
        carbon_load = 0.0
        bonding_density = 0.0
        hydro_idx = _LIGAND_HYDRO["ion_pair"]
        endcapped = False

    else:
        ligand_length = 18
        carbon_load = 15.0
        bonding_density = 3.0
        hydro_idx = _LIGAND_HYDRO["C18"]

    # Polar embedded / AQ detection
    if any(k in name_lower for k in [" aq", "aq-", "shield", "polar premium", "polar-rp", "polar embedded", "bonus-rp", "pa2"]):
        polar_embedded = True
        carbon_load *= 0.9  # slightly lower due to polar group

    # Core-shell has lower effective surface area (solid core)
    if is_core_shell:
        surface_area *= 0.55  # effective area is ~55% of fully porous

    return StationaryPhase(
        carbon_load_pct=round(carbon_load, 1),
        ligand_length=ligand_length,
        bonding_density_umol_m2=round(bonding_density, 1),
        surface_area_m2_g=round(surface_area, 1),
        pore_size_a=pore_size,
        endcapped=endcapped,
        polar_embedded=polar_embedded,
        particle_type=particle_type,
        base_material=base,
        hydrophobicity_index=hydro_idx,
    )


# ---------------------------------------------------------------------------
# Generate all column entries
# ---------------------------------------------------------------------------

_COLUMNS: list[ColumnSpec] = []
for _fam in _FAMILIES:
    if _fam.phase is None:
        _fam = ColumnFamily(
            brand=_fam.brand, name=_fam.name, chemistry=_fam.chemistry,
            ph_range=_fam.ph_range, temp_max_c=_fam.temp_max_c,
            usp_code=_fam.usp_code, notes=_fam.notes,
            variants=_fam.variants, phase=_infer_phase(_fam),
        )
    _COLUMNS.extend(_gen_columns(_fam))


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------

def list_columns(
    chemistry: str | None = None,
    brand: str | None = None,
    search: str | None = None,
    particle_size: float | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[ColumnSpec], int]:
    """List columns with optional filtering and pagination.

    Returns (columns_page, total_count).
    """
    result = _COLUMNS
    if chemistry:
        result = [c for c in result if c.chemistry == chemistry]
    if brand:
        result = [c for c in result if c.brand.lower() == brand.lower()]
    if particle_size is not None:
        result = [c for c in result if abs(c.particle_size_um - particle_size) < 0.01]
    if search:
        q = search.lower()
        result = [c for c in result if q in c.name.lower() or q in c.brand.lower() or q in c.chemistry.lower()]
    total = len(result)
    return result[offset:offset + limit], total


def get_column(column_id: str) -> ColumnSpec | None:
    """Get a single column by ID."""
    for c in _COLUMNS:
        if c.id == column_id:
            return c
    return None


def column_to_dict(c: ColumnSpec) -> dict[str, Any]:
    d = {
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
    if c.phase is not None:
        d["stationary_phase"] = {
            "carbon_load_pct": c.phase.carbon_load_pct,
            "ligand_length": c.phase.ligand_length,
            "bonding_density_umol_m2": c.phase.bonding_density_umol_m2,
            "surface_area_m2_g": c.phase.surface_area_m2_g,
            "pore_size_a": c.phase.pore_size_a,
            "endcapped": c.phase.endcapped,
            "polar_embedded": c.phase.polar_embedded,
            "particle_type": c.phase.particle_type,
            "base_material": c.phase.base_material,
            "hydrophobicity_index": c.phase.hydrophobicity_index,
        }
    return d


def get_brands() -> list[str]:
    """Return unique brand names."""
    return sorted({c.brand for c in _COLUMNS})


def get_chemistries() -> list[str]:
    """Return unique chemistry types."""
    return sorted({c.chemistry for c in _COLUMNS})


def get_column_count() -> int:
    """Return total number of columns in the database."""
    return len(_COLUMNS)
