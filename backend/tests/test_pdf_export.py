"""Tests for section-driven PDF export."""
import pytest
from app.core.export.pdf import (
    PDFSectionOptions,
    ColumnComparisonSections,
    BatchAnalysisSections,
    export_method_pdf,
    export_column_comparison_pdf,
    export_batch_analysis_pdf,
    _get_theme,
    _get_mpl_theme,
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
    id = "00000000-0000-0000-0000-000000000001"
    name = "Test Method"
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
    compounds_smiles = ["CN1C=NC2=C1C(=O)N(C(=O)N2C)C"]
    owner_id = None


class _MockPrediction:
    predicted_rt_s = 480.0
    rt_lower_s = 420.0
    rt_upper_s = 540.0
    confidence = 0.85
    model_version = "test-v1"
    extrapolating = False


# ---------------------------------------------------------------------------
# Section options
# ---------------------------------------------------------------------------

class TestPDFSectionOptions:
    def test_defaults(self):
        opts = PDFSectionOptions()
        assert opts.method_parameters is True
        assert opts.gradient_program is True
        assert opts.compound_info is True
        assert opts.chromatogram is False
        assert opts.resolution_matrix is False
        assert opts.robustness is False
        assert opts.optimization is False
        assert opts.method_transfer is False
        assert opts.cover_page is False
        assert opts.disclaimer is True

    def test_from_dict_all_true(self):
        d = {k: True for k in [
            "method_parameters", "gradient_program", "compound_info",
            "chromatogram", "resolution_matrix", "robustness",
            "optimization", "method_transfer", "cover_page", "disclaimer",
        ]}
        opts = PDFSectionOptions.from_dict(d)
        assert opts.chromatogram is True
        assert opts.robustness is True
        assert opts.cover_page is True

    def test_from_dict_none(self):
        opts = PDFSectionOptions.from_dict(None)
        assert opts.method_parameters is True
        assert opts.chromatogram is False

    def test_from_dict_partial(self):
        opts = PDFSectionOptions.from_dict({"chromatogram": True})
        assert opts.chromatogram is True
        assert opts.method_parameters is True  # default


class TestColumnComparisonSections:
    def test_defaults(self):
        opts = ColumnComparisonSections()
        assert opts.tanaka_table is True
        assert opts.radar_chart is True
        assert opts.similarity_matrix is True
        assert opts.parameter_diffs is True
        assert opts.cover_page is False
        assert opts.disclaimer is True

    def test_from_dict(self):
        opts = ColumnComparisonSections.from_dict({"radar_chart": False})
        assert opts.radar_chart is False
        assert opts.tanaka_table is True


class TestBatchAnalysisSections:
    def test_defaults(self):
        opts = BatchAnalysisSections()
        assert opts.method_parameters is True
        assert opts.compound_table is True
        assert opts.chromatogram is True
        assert opts.flagged_compounds is True
        assert opts.cover_page is False
        assert opts.disclaimer is True

    def test_from_dict(self):
        opts = BatchAnalysisSections.from_dict({"chromatogram": False})
        assert opts.chromatogram is False
        assert opts.compound_table is True


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

class TestThemes:
    def test_default_theme(self):
        t = _get_theme(None)
        assert "accent" in t
        assert "dark" in t

    def test_blue_theme(self):
        t = _get_theme("blue")
        # ReportLab HexColor stores as RGB floats; verify it's the blue accent
        c = t["accent"]
        assert abs(c.red - 0x25 / 255) < 0.01
        assert abs(c.green - 0x63 / 255) < 0.01
        assert abs(c.blue - 0xeb / 255) < 0.01

    def test_green_theme(self):
        t = _get_theme("green")
        assert "accent" in t

    def test_unknown_theme_falls_back(self):
        t = _get_theme("nonexistent")
        assert "accent" in t

    def test_mpl_theme(self):
        t = _get_mpl_theme("blue")
        assert t["accent"] == "#2563eb"

    def test_all_thymes_have_required_keys(self):
        for name in ["blue", "green", "slate", "burgundy"]:
            t = _get_theme(name)
            for key in ["accent", "accent_light", "dark", "muted", "row_alt", "border", "success", "warning"]:
                assert key in t, f"Theme {name} missing {key}"


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

class TestExportMethodPdf:
    def test_basic_pdf_generation(self):
        method = _MockMethod()
        compound = _MockCompound()
        opts = PDFSectionOptions(
            method_parameters=True,
            gradient_program=True,
            compound_info=True,
            chromatogram=False,
            resolution_matrix=False,
            robustness=False,
            optimization=False,
            method_transfer=False,
            cover_page=False,
            disclaimer=True,
        )
        pdf = export_method_pdf(method, compound, None, {}, sections=opts)
        assert pdf is not None
        assert len(pdf) > 100
        assert pdf.startswith(b"%PDF")

    def test_minimal_sections(self):
        """Only disclaimer — should still produce a valid PDF."""
        method = _MockMethod()
        opts = PDFSectionOptions(
            method_parameters=False,
            gradient_program=False,
            compound_info=False,
            chromatogram=False,
            resolution_matrix=False,
            robustness=False,
            optimization=False,
            method_transfer=False,
            cover_page=False,
            disclaimer=True,
        )
        pdf = export_method_pdf(method, None, None, {}, sections=opts)
        assert pdf.startswith(b"%PDF")

    def test_all_sections_enabled(self):
        """All sections enabled — should produce a valid multi-page PDF."""
        method = _MockMethod()
        opts = PDFSectionOptions(
            method_parameters=True,
            gradient_program=True,
            compound_info=True,
            chromatogram=True,
            resolution_matrix=True,
            robustness=True,
            optimization=True,
            method_transfer=True,
            cover_page=True,
            disclaimer=True,
        )
        pdf = export_method_pdf(method, None, None, {}, sections=opts)
        assert pdf.startswith(b"%PDF")
        assert len(pdf) > 5000  # should be substantial

    def test_cover_page(self):
        method = _MockMethod()
        opts = PDFSectionOptions(cover_page=True, method_parameters=False, gradient_program=False, compound_info=False, disclaimer=False)
        settings = {"lab_name": "Test Lab", "cover_page_text": "Custom cover text"}
        pdf = export_method_pdf(method, None, None, settings, sections=opts)
        assert pdf.startswith(b"%PDF")

    def test_theme_applied(self):
        method = _MockMethod()
        opts = PDFSectionOptions()
        for theme in ["blue", "green", "slate", "burgundy"]:
            settings = {"report_theme": theme}
            pdf = export_method_pdf(method, None, None, settings, sections=opts)
            assert pdf.startswith(b"%PDF")

    def test_method_transfer_section(self):
        method = _MockMethod()
        opts = PDFSectionOptions(
            method_parameters=False, gradient_program=False, compound_info=False,
            chromatogram=False, resolution_matrix=False, robustness=False,
            optimization=False, method_transfer=True, cover_page=False, disclaimer=False,
        )
        pdf = export_method_pdf(method, None, None, {}, sections=opts)
        assert pdf.startswith(b"%PDF")

    def test_with_prediction(self):
        method = _MockMethod()
        compound = _MockCompound()
        prediction = _MockPrediction()
        opts = PDFSectionOptions()
        pdf = export_method_pdf(method, compound, prediction, {}, sections=opts)
        assert pdf.startswith(b"%PDF")


class TestExportColumnComparisonPdf:
    def test_basic(self):
        columns = [
            {"label": "Column A", "tanaka": {"k_pb": 3.5, "k_sr": 2.0, "k_tfa": 1.5, "k_ch2": 1.2, "k_amide": 0.5}},
            {"label": "Column B", "tanaka": {"k_pb": 4.0, "k_sr": 1.8, "k_tfa": 1.6, "k_ch2": 1.3, "k_amide": 0.4}},
        ]
        pdf = export_column_comparison_pdf(columns, {})
        assert pdf.startswith(b"%PDF")

    def test_all_sections(self):
        columns = [
            {"label": "Col A", "tanaka": {"k_pb": 3.5, "k_sr": 2.0, "k_tfa": 1.5, "k_ch2": 1.2, "k_amide": 0.5}},
            {"label": "Col B", "tanaka": {"k_pb": 4.0, "k_sr": 1.8, "k_tfa": 1.6, "k_ch2": 1.3, "k_amide": 0.4}},
            {"label": "Col C", "tanaka": {"k_pb": 2.5, "k_sr": 2.5, "k_tfa": 1.0, "k_ch2": 1.0, "k_amide": 0.8}},
        ]
        opts = ColumnComparisonSections(
            tanaka_table=True, radar_chart=True, similarity_matrix=True,
            parameter_diffs=True, cover_page=True, disclaimer=True,
        )
        pdf = export_column_comparison_pdf(columns, {}, sections=opts)
        assert pdf.startswith(b"%PDF")

    def test_no_radar(self):
        columns = [{"label": "Col A", "tanaka": {"k_pb": 3.5, "k_sr": 2.0, "k_tfa": 1.5, "k_ch2": 1.2, "k_amide": 0.5}}]
        opts = ColumnComparisonSections(radar_chart=False)
        pdf = export_column_comparison_pdf(columns, {}, sections=opts)
        assert pdf.startswith(b"%PDF")


class TestExportBatchAnalysisPdf:
    def test_basic(self):
        batch_data = {
            "method_params": {"column_type": "C18", "ph": 2.7, "flow_rate_ml_min": 0.4, "temperature_c": 30},
            "compounds": [{"name": "Caffeine", "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"}],
            "results": [{"name": "Caffeine", "rt_s": 480, "width_s": 10, "status": "OK"}],
        }
        pdf = export_batch_analysis_pdf(batch_data, {})
        assert pdf.startswith(b"%PDF")

    def test_with_flagged(self):
        batch_data = {
            "method_params": {"column_type": "C18"},
            "compounds": [{"name": "A", "smiles": "CCO"}, {"name": "B", "smiles": "CCN"}],
            "results": [
                {"name": "A", "rt_s": 300, "width_s": 8, "status": "OK"},
                {"name": "B", "rt_s": 0, "width_s": 0, "status": "Error: parse failed"},
            ],
        }
        opts = BatchAnalysisSections(flagged_compounds=True)
        pdf = export_batch_analysis_pdf(batch_data, {}, sections=opts)
        assert pdf.startswith(b"%PDF")

    def test_empty_results(self):
        batch_data = {"method_params": {}, "compounds": [], "results": []}
        pdf = export_batch_analysis_pdf(batch_data, {})
        assert pdf.startswith(b"%PDF")
