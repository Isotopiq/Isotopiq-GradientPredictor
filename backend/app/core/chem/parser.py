"""Molecule parsing: SMILES / InChI / molfile / SDF -> RDKit Mol."""
from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem
from rdkit.Chem import AllChem


class ChemParseError(ValueError):
    """Raised when a molecule cannot be parsed."""


@dataclass(frozen=True)
class ParsedMolecule:
    mol: Chem.Mol
    smiles: str
    inchi: str
    inchikey: str
    molfile: str


def parse_mol(input_str: str) -> ParsedMolecule:
    """Parse a SMILES, InChI, or molfile string into a ParsedMolecule.

    Raises ChemParseError on failure.
    """
    s = input_str.strip()
    if not s:
        raise ChemParseError("Empty input")

    mol: Chem.Mol | None = None

    # Try InChI first (unambiguous prefix)
    if s.startswith("InChI="):
        mol = Chem.MolFromInchi(s)
        if mol is None:
            raise ChemParseError("Invalid InChI")
    # molfile: contains "M  END" or V2000/V3000 marker
    elif "M  END" in s or "V2000" in s or "V3000" in s:
        # Use the original (unstripped) input for molblock parsing —
        # strip() can corrupt the fixed-width counts line.
        mol = Chem.MolFromMolBlock(input_str)
        if mol is None:
            # Try stripped version as fallback
            mol = Chem.MolFromMolBlock(s)
        if mol is None:
            raise ChemParseError("Invalid molfile")
    else:
        # Treat as SMILES
        mol = Chem.MolFromSmiles(s)
        if mol is None:
            raise ChemParseError("Invalid SMILES")

    return _build_parsed(mol)


def parse_sdf(sdf_text: str) -> list[ParsedMolecule]:
    """Parse an SDF text block into a list of ParsedMolecule."""
    supplier = Chem.SDMolSupplier()
    supplier.SetData(sdf_text)
    results: list[ParsedMolecule] = []
    for mol in supplier:
        if mol is None:
            continue
        results.append(_build_parsed(mol))
    if not results:
        raise ChemParseError("No valid molecules in SDF")
    return results


def _build_parsed(mol: Chem.Mol) -> ParsedMolecule:
    # Ensure 2D coords for depiction
    try:
        AllChem.Compute2DCoords(mol)
    except Exception:
        pass
    smiles = Chem.MolToSmiles(mol)
    inchi = Chem.MolToInchi(mol)
    inchikey = Chem.InchiToInchiKey(inchi) if inchi else ""
    molfile = Chem.MolToMolBlock(mol)
    return ParsedMolecule(mol=mol, smiles=smiles, inchi=inchi, inchikey=inchikey, molfile=molfile)
