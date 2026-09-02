"""Unit tests for chem.parser."""
from __future__ import annotations

import pytest
from rdkit import Chem

from app.core.chem.parser import ChemParseError, parse_mol, parse_sdf


class TestParser:
    def test_parse_smiles(self):
        result = parse_mol("CCO")
        assert result.smiles == "CCO"
        assert result.inchi.startswith("InChI=")
        assert len(result.inchikey) == 27  # InChIKey is 27 chars (14-0-10-1)
        assert "M  END" in result.molfile

    def test_parse_inchi(self):
        result = parse_mol("InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3")
        assert result.smiles == "CCO"

    def test_parse_molfile(self):
        # Generate a proper molblock from RDKit
        mol = Chem.MolFromSmiles("CCO")
        molblock = Chem.MolToMolBlock(mol)
        result = parse_mol(molblock)
        assert "CCO" in result.smiles

    def test_parse_invalid_smiles(self):
        with pytest.raises(ChemParseError):
            parse_mol("not-a-smiles!!!")

    def test_parse_empty(self):
        with pytest.raises(ChemParseError):
            parse_mol("")

    def test_parse_sdf(self):
        mol = Chem.MolFromSmiles("CCO")
        molblock = Chem.MolToMolBlock(mol)
        sdf = molblock + "$$$$\n"
        results = parse_sdf(sdf)
        assert len(results) == 1
