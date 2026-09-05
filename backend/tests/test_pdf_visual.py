"""Generate sample PDFs to verify table wrapping and chromatogram label fixes."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.export.pdf import (
    PDFSectionOptions,
    export_method_pdf,
    export_batch_analysis_pdf,
    BatchAnalysisSections,
)


class _MockCompound:
    name = "Caffeine"
    smiles = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
    inchikey = "RYYVLZVUVIJVGH-UHFFFAOYSA-N"
    mw = 194.19
    logp = -0.07
    tpsa = 58.44
    hbd = 0
    hba = 6
    rotatable_bonds = 0
    aromatic_rings = 2
    pka_values = [14.0]
    cas = "58-08-2"


class _MockMethod:
    id = "test"
    name = "Test Method with Long SMILES"
    column_type = "C18"
    column_dims = {"length_mm": 100, "id_mm": 2.1, "particle_um": 1.7}
    mobile_phase_a = "Water + 0.1% Formic Acid"
    mobile_phase_b = "Acetonitrile"
    additive = "0.1% Formic Acid"
    ph = 2.7
    gradient_table = [
        {"time_s": 0, "percent_b": 5},
        {"time_s": 60, "percent_b": 5},
        {"time_s": 1200, "percent_b": 95},
        {"time_s": 1260, "percent_b": 95},
    ]
    flow_rate_ml_min = 0.4
    temperature_c = 30.0
    dwell_volume_ml = 0.5
    dead_volume_ml = 0.15
    # Long SMILES that would overflow old table cells
    compounds_smiles = [
        "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # caffeine
        "CC(=O)OC1=CC=CC=C1C(=O)O",  # aspirin
        "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",  # ibuprofen
        "C1=CC=C(C=C1)C2=CC=C(C=C2)C3=CC=C(C=C3)C4=CC=C(C=C4)C5=CC=C(C=C5)C6=CC=C(C=C6)C7=CC=C(C=C7)C8=CC=C(C=C8)O",  # very long
        "OC(=O)[C@@H]1CCCN1C(=O)[C@@H](Cc2ccccc2)NC(=O)[C@@H](CO)NC(=O)[C@H](C)NC(=O)[C@@H](Cc3ccc(O)cc3)NC(=O)[C@H](CO)NC(=O)[C@@H](CC(C)C)N",  # peptide - very long
    ]
    owner_id = None


def test_method_pdf():
    """Generate a method PDF with long SMILES and chromatogram."""
    method = _MockMethod()
    compound = _MockCompound()
    opts = PDFSectionOptions(
        method_parameters=True,
        gradient_program=True,
        compound_info=True,
        chromatogram=True,
        resolution_matrix=True,
        cover_page=False,
        disclaimer=True,
    )
    pdf = export_method_pdf(method, compound, None, {}, sections=opts)
    out_path = "/tmp/test_method_pdf.pdf"
    with open(out_path, "wb") as f:
        f.write(pdf)
    print(f"Method PDF: {len(pdf)} bytes -> {out_path}")


def test_batch_pdf():
    """Generate a batch analysis PDF with many compounds."""
    results = []
    for i in range(15):
        rt = 60 + i * 50  # close RTs to test label overlap
        results.append({
            "name": f"Compound_with_long_name_{i+1}",
            "rt_s": rt,
            "width_s": 8,
            "status": "OK" if i % 3 != 0 else "Co-elution risk",
        })
    batch_data = {
        "method_params": {"column_type": "C18", "ph": 2.7, "flow_rate_ml_min": 0.4, "temperature_c": 30},
        "compounds": [{"name": r["name"], "smiles": "CCO"} for r in results],
        "results": results,
    }
    opts = BatchAnalysisSections(
        method_parameters=True,
        compound_table=True,
        chromatogram=True,
        flagged_compounds=True,
        disclaimer=True,
    )
    pdf = export_batch_analysis_pdf(batch_data, {}, sections=opts)
    out_path = "/tmp/test_batch_pdf.pdf"
    with open(out_path, "wb") as f:
        f.write(pdf)
    print(f"Batch PDF: {len(pdf)} bytes -> {out_path}")


if __name__ == "__main__":
    test_method_pdf()
    test_batch_pdf()
    print("Done!")
