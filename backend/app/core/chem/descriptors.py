"""Molecular descriptor calculation via RDKit."""
from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors


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
    )
