"""Tests for resolution maps and ternary optimization."""
import pytest

from app.core.lss.resolution_map import resolution_map_1d, resolution_map_2d
from app.core.lss.ternary_optimization import ternary_optimize

# Simple, valid SMILES for testing
SMILES_PAIR = ["c1ccccc1", "CC(=O)c1ccccc1"]  # benzene, acetophenone
SMILES_TRIPLE = ["c1ccccc1", "CC(=O)c1ccccc1", "Oc1ccccc1"]  # + phenol


class TestResolutionMap1D:
    def test_gradient_time_variable(self):
        """1D map over gradient time should produce valid results."""
        result = resolution_map_1d(
            SMILES_PAIR,
            variable="gradient_time",
            var_range=(5.0, 60.0),
            steps=10,
        )
        assert len(result.x_values) == 10
        assert len(result.min_rs) == 10
        assert len(result.per_compound_rts) == 2
        assert all(len(rts) == 10 for rts in result.per_compound_rts)
        # min_rs should be non-negative (or inf clamped to 0)
        assert all(rs >= 0.0 for rs in result.min_rs)

    def test_ph_variable(self):
        """1D map over pH should produce valid results."""
        result = resolution_map_1d(
            SMILES_PAIR,
            variable="ph",
            var_range=(2.0, 8.0),
            steps=5,
        )
        assert len(result.x_values) == 5
        assert len(result.min_rs) == 5

    def test_temperature_variable(self):
        """1D map over temperature should produce valid results."""
        result = resolution_map_1d(
            SMILES_PAIR,
            variable="temperature",
            var_range=(20.0, 60.0),
            steps=5,
        )
        assert len(result.x_values) == 5

    def test_invalid_variable_raises(self):
        """Invalid variable name should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid variable"):
            resolution_map_1d(
                SMILES_PAIR,
                variable="invalid_var",
                var_range=(1.0, 10.0),
                steps=5,
            )

    def test_single_compound_raises(self):
        """Single compound should raise ValueError."""
        with pytest.raises(ValueError, match="at least 2"):
            resolution_map_1d(
                ["c1ccccc1"],
                variable="gradient_time",
                var_range=(5.0, 60.0),
                steps=5,
            )

    def test_to_dict_round(self):
        """to_dict should produce rounded, serializable values."""
        result = resolution_map_1d(
            SMILES_PAIR,
            variable="flow_rate",
            var_range=(0.2, 0.8),
            steps=3,
        )
        d = result.to_dict()
        assert "variable" in d
        assert "x_values" in d
        assert "min_rs" in d
        assert "per_compound_rts" in d


class TestResolutionMap2D:
    def test_basic_2d_map(self):
        """2D map should produce a grid of resolution values."""
        result = resolution_map_2d(
            SMILES_PAIR,
            var_x="gradient_time",
            range_x=(5.0, 30.0),
            steps_x=5,
            var_y="temperature",
            range_y=(20.0, 50.0),
            steps_y=4,
        )
        assert len(result.x_values) == 5
        assert len(result.y_values) == 4
        assert len(result.rs_grid) == 4  # rows = y
        assert all(len(row) == 5 for row in result.rs_grid)  # cols = x
        assert "x" in result.optimal_point
        assert "y" in result.optimal_point
        assert "rs" in result.optimal_point

    def test_2d_with_ph_variable(self):
        """2D map with pH as one variable should work."""
        result = resolution_map_2d(
            SMILES_PAIR,
            var_x="ph",
            range_x=(2.0, 8.0),
            steps_x=3,
            var_y="gradient_time",
            range_y=(10.0, 40.0),
            steps_y=3,
        )
        assert len(result.rs_grid) == 3
        assert all(len(row) == 3 for row in result.rs_grid)

    def test_2d_invalid_variable(self):
        """Invalid variable should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid variable"):
            resolution_map_2d(
                SMILES_PAIR,
                var_x="bad",
                range_x=(1.0, 10.0),
                steps_x=3,
                var_y="gradient_time",
                range_y=(5.0, 30.0),
                steps_y=3,
            )


class TestTernaryOptimize:
    def test_ternary_mode(self):
        """Ternary mode should search interior points."""
        result = ternary_optimize(
            SMILES_PAIR,
            solvent_b="acn",
            solvent_c="meoh",
            mode="ternary",
            grid_resolution=5,
        )
        assert result.mode == "ternary"
        assert len(result.points) > 0
        # Should have interior points (all three fractions > 0)
        interior = [p for p in result.points
                    if p.frac_a > 0.01 and p.frac_b > 0.01 and p.frac_c > 0.01]
        assert len(interior) > 0
        assert result.optimal is not None

    def test_binary_mode(self):
        """Binary mode should only search perimeter points."""
        result = ternary_optimize(
            SMILES_PAIR,
            solvent_b="acn",
            solvent_c="meoh",
            mode="binary",
            grid_resolution=5,
        )
        assert result.mode == "binary"
        # No interior points in binary mode
        interior = [p for p in result.points
                    if p.frac_a > 0.01 and p.frac_b > 0.01 and p.frac_c > 0.01]
        assert len(interior) == 0

    def test_to_dict(self):
        """to_dict should produce serializable output."""
        result = ternary_optimize(
            SMILES_PAIR,
            grid_resolution=3,
        )
        d = result.to_dict()
        assert "solvent_a" in d
        assert "points" in d
        assert isinstance(d["points"], list)
        if d["optimal"]:
            assert "frac_a" in d["optimal"]
            assert "min_rs" in d["optimal"]

    def test_single_compound_raises(self):
        """Single compound should raise ValueError."""
        with pytest.raises(ValueError, match="at least 2"):
            ternary_optimize(["c1ccccc1"])

    def test_three_compounds(self):
        """Three compounds should work correctly."""
        result = ternary_optimize(
            SMILES_TRIPLE,
            grid_resolution=4,
        )
        assert len(result.points) > 0
        assert result.optimal is not None
