"""2D molecule depiction using RDKit server-side."""
from __future__ import annotations


def render_2d_svg(smiles: str, width: int = 400, height: int = 300) -> str:
    """Render a 2D SVG depiction of a molecule from SMILES."""
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from rdkit.Chem.Draw import rdMolDraw2D

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    # Compute 2D coordinates if not present
    AllChem.Compute2DCoords(mol)

    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    opts = drawer.drawOptions()
    opts.bondLineWidth = 2
    opts.padding = 0.1
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    return drawer.GetDrawingText().replace("xmlns:svg=", "xmlns=")
