"""pKa estimation with a pluggable provider interface.

RDKit does not ship a production pKa predictor. We use a documented
heuristic based on functional-group SMARTS with literature-typical pKa
ranges. This is an *estimate* and must be surfaced as such in the UI.

A `PkaProvider` interface allows swapping in ChemAxon / ACD-Labs / pkasolver
later without changing call sites.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass

from rdkit import Chem


@dataclass(frozen=True)
class PkaSite:
    """A single ionizable site estimate."""

    pka: float
    acid_base: str  # "acid" | "base"
    smarts: str
    atom_idx: int


class PkaProvider(abc.ABC):
    @abc.abstractmethod
    def estimate_pka(self, mol: Chem.Mol) -> list[PkaSite]:
        """Return estimated pKa sites for the molecule."""
        raise NotImplementedError


# Functional-group SMARTS -> (typical pKa, acid/base)
# Values are conservative midpoints from common reference tables.
_DEFAULT_RULES: list[tuple[str, float, str]] = [
    # Acids
    ("[CX3](=O)[OX1H0-]", 4.2, "acid"),  # carboxylate (deprotonated form matched loosely)
    ("[CX3](=O)[OX2H1]", 4.2, "acid"),  # carboxylic acid
    ("c1ccccc1[SX3](=O)(=O)[OX2H1]", -2.0, "acid"),  # sulfonic acid
    ("[OX2H1][CX3]=O", 7.0, "acid"),  # enol/phenol-ish carbonyl OH (loose)
    ("[aX2][OX2H1]", 10.0, "acid"),  # phenol
    ("[CX3](=O)[NX3H2]", 15.0, "acid"),  # amide N-H (very weak acid)
    # Bases
    ("[NX3;H2,H1,H0;!$(NC=O)]", 9.5, "base"),  # aliphatic amine
    ("[nX2;H1]", 5.2, "base"),  # aromatic N-H (pyrrole-like, weak base)
    ("[nX2;H0]", 3.0, "base"),  # aromatic N (pyridine-like)
    ("[NX2;H1,H0]", 10.5, "base"),  # imine (loose)
]


class RDKitPkaProvider(PkaProvider):
    """Heuristic pKa estimator using functional-group SMARTS matching."""

    def __init__(self, rules: list[tuple[str, float, str]] | None = None) -> None:
        self._rules = rules or _DEFAULT_RULES

    def estimate_pka(self, mol: Chem.Mol) -> list[PkaSite]:
        sites: list[PkaSite] = []
        for smarts, pka, acid_base in self._rules:
            pattern = Chem.MolFromSmarts(smarts)
            if pattern is None:
                continue
            matches = mol.GetSubstructMatches(pattern)
            for match in matches:
                if not match:
                    continue
                sites.append(
                    PkaSite(pka=pka, acid_base=acid_base, smarts=smarts, atom_idx=int(match[0]))
                )
        # Deduplicate by (pka, acid_base, atom_idx)
        seen: set[tuple[float, str, int]] = set()
        unique: list[PkaSite] = []
        for s in sites:
            key = (s.pka, s.acid_base, s.atom_idx)
            if key in seen:
                continue
            seen.add(key)
            unique.append(s)
        return unique


class ChemAxonPkaProvider(PkaProvider):
    """Stub for ChemAxon pKa (requires license). Not implemented."""

    def estimate_pka(self, mol: Chem.Mol) -> list[PkaSite]:
        raise NotImplementedError("ChemAxon pKa provider requires a license and configuration")


class AcdPkaProvider(PkaProvider):
    """Stub for ACD/Labs pKa (requires license). Not implemented."""

    def estimate_pka(self, mol: Chem.Mol) -> list[PkaSite]:
        raise NotImplementedError("ACD/Labs pKa provider requires a license and configuration")


def get_default_provider() -> PkaProvider:
    return RDKitPkaProvider()


def estimate_pka_sites(
    mol: Chem.Mol, provider: PkaProvider | None = None
) -> list[PkaSite]:
    """Return the list of estimated pKa sites for the molecule."""
    provider = provider or get_default_provider()
    return provider.estimate_pka(mol)


def estimate_pka_values(mol: Chem.Mol, provider: PkaProvider | None = None) -> list[float]:
    """Return a sorted list of estimated pKa values for the molecule."""
    sites = estimate_pka_sites(mol, provider)
    return sorted({round(s.pka, 2) for s in sites})
