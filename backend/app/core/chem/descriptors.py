"""Molecular descriptor calculation via RDKit."""
from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors, AllChem, rdFreeSASA


@dataclass(frozen=True)
class Descriptor3DResult:
    """3D conformer-based descriptors for shape-dependent selectivity."""
    radius_of_gyration: float  # compactness (Å)
    asphericity: float  # 0=spherical, 1=rod
    eccentricity: float  # 0=circular, 1=linear
    pmi1: float  # principal moment of inertia (smallest)
    pmi2: float
    pmi3: float  # principal moment of inertia (largest)
    pmi_ratio_12: float  # PMI1/PMI2 (0=planar, 1=symmetric)
    pmi_ratio_13: float  # PMI1/PMI3 (0=rod, 1=spherical)
    sasa: float  # solvent accessible surface area (Å²)


@dataclass(frozen=True)
class DescriptorResult:
    mw: float
    logp: float
    tpsa: float
    hbd: int
    hba: int
    rotatable_bonds: int
    aromatic_rings: int
    num_rings: int
    num_heavy_atoms: int
    num_heteroatoms: int
    fraction_csp3: float
    # 3D descriptors (None if conformer generation fails)
    descriptors_3d: Descriptor3DResult | None = None


def compute_descriptors(mol: Chem.Mol) -> DescriptorResult:
    """Compute the core physicochemical descriptors used by the rules engine."""
    return DescriptorResult(
        mw=Descriptors.MolWt(mol),
        logp=Crippen.MolLogP(mol),
        tpsa=rdMolDescriptors.CalcTPSA(mol),
        hbd=rdMolDescriptors.CalcNumHBD(mol),
        hba=rdMolDescriptors.CalcNumHBA(mol),
        rotatable_bonds=rdMolDescriptors.CalcNumRotatableBonds(mol),
        aromatic_rings=rdMolDescriptors.CalcNumAromaticRings(mol),
        num_rings=rdMolDescriptors.CalcNumRings(mol),
        num_heavy_atoms=mol.GetNumHeavyAtoms(),
        num_heteroatoms=rdMolDescriptors.CalcNumHeteroatoms(mol),
        fraction_csp3=rdMolDescriptors.CalcFractionCSP3(mol),
        descriptors_3d=compute_3d_descriptors(mol),
    )


def compute_3d_descriptors(mol: Chem.Mol) -> Descriptor3DResult | None:
    """Compute 3D conformer-based shape descriptors.

    Returns None if conformer generation fails (e.g., macrocycles,
    very large molecules, or molecules without explicit hydrogens).
    """
    try:
        mol = Chem.AddHs(mol)
        params = AllChem.ETKDGv3()
        params.randomSeed = 42
        conf_id = AllChem.EmbedMolecule(mol, params)
        if conf_id < 0:
            # Try older ETKDG as fallback
            params2 = AllChem.ETKDGv2()
            params2.randomSeed = 42
            conf_id = AllChem.EmbedMolecule(mol, params2)
        if conf_id < 0:
            return None

        # Optimize with UFF
        try:
            AllChem.UFFOptimizeMolecule(mol, maxIters=200)
        except Exception:
            pass

        # Principal moments of inertia
        pmi1 = rdMolDescriptors.CalcPMI1(mol)
        pmi2 = rdMolDescriptors.CalcPMI2(mol)
        pmi3 = rdMolDescriptors.CalcPMI3(mol)

        # Radius of gyration
        rgyr = rdMolDescriptors.CalcRadiusOfGyration(mol)

        # Asphericity and eccentricity
        asph = rdMolDescriptors.CalcAsphericity(mol)
        ecc = rdMolDescriptors.CalcEccentricity(mol)

        # Solvent accessible surface area
        sasa = 0.0
        try:
            radii = rdFreeSASA.classifyAtoms(mol)
            sasa = rdFreeSASA.CalcSASA(mol, radii, confIdx=0)
        except Exception:
            pass

        return Descriptor3DResult(
            radius_of_gyration=round(rgyr, 3),
            asphericity=round(asph, 4),
            eccentricity=round(ecc, 4),
            pmi1=round(pmi1, 3),
            pmi2=round(pmi2, 3),
            pmi3=round(pmi3, 3),
            pmi_ratio_12=round(pmi1 / max(pmi2, 1e-8), 4),
            pmi_ratio_13=round(pmi1 / max(pmi3, 1e-8), 4),
            sasa=round(sasa, 2),
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# MS m/z and adduct prediction (F9)
# ---------------------------------------------------------------------------

# Common adduct masses (monoisotopic)
_ADDUCT_MASSES = {
    "positive": {
        "[M+H]+": 1.007276,
        "[M+Na]+": 22.989218,
        "[M+K]+": 38.963158,
        "[M+NH4]+": 18.033826,
        "[M+H-H2O]+": -17.003280,  # loss of water
        "[M+H+CH3CN]+": 42.033826,  # acetonitrile adduct
        "[M+2H]2+": 2.014552,  # doubly charged
    },
    "negative": {
        "[M-H]-": -1.007276,
        "[M+Cl]-": 34.969402,
        "[M+HCOO]-": 44.998201,
        "[M+CH3COO]-": 59.013853,
        "[M-2H]2-": -2.014552,  # doubly charged
    },
}


def predict_adducts(monoisotopic_mass: float) -> dict[str, list[dict]]:
    """Predict expected m/z values for common ESI adducts.

    Args:
        monoisotopic_mass: Monoisotopic molecular mass (Da).

    Returns:
        {"positive": [{"adduct": "[M+H]+", "mz": 180.1, "charge": 1}, ...],
         "negative": [...]}
    """
    result: dict[str, list[dict]] = {"positive": [], "negative": []}

    for adduct, mass_diff in _ADDUCT_MASSES["positive"].items():
        charge = 2 if "2+" in adduct else 1
        mz = (monoisotopic_mass + mass_diff) / charge
        result["positive"].append({
            "adduct": adduct,
            "mz": round(mz, 4),
            "charge": charge,
        })

    for adduct, mass_diff in _ADDUCT_MASSES["negative"].items():
        charge = 2 if "2-" in adduct else 1
        mz = (monoisotopic_mass + mass_diff) / abs(charge)
        result["negative"].append({
            "adduct": adduct,
            "mz": round(mz, 4),
            "charge": -charge,
        })

    return result
