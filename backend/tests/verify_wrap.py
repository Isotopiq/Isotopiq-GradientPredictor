"""Verify that long SMILES text wraps within table column widths."""
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.units import mm

smiles = "C1=CC=C(C=C1)C2=CC=C(C=C2)C3=CC=C(C=C3)C4=CC=C(C=C4)C5=CC=C(C=C5)C6=CC=C(C=C6)C7=CC=C(C=C7)C8=CC=C(C=C8)O"
col_width = 120 * mm
font_size = 7.5

full_width = stringWidth(smiles, "Courier", font_size)
print(f"SMILES length: {len(smiles)} chars")
print(f"Full string width: {full_width:.1f} pts")
print(f"Column width: {col_width:.1f} pts")
print(f"Fits in one line: {full_width <= col_width}")
print(f"Would need ~{int(full_width / col_width) + 1} lines to wrap")
print()
print("With Paragraph wrapping, the SMILES will wrap within the cell.")
