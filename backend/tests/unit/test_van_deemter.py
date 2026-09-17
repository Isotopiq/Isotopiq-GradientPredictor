"""Unit tests for lss.van_deemter — Van Deemter flow optimization.

Reference values hand-checked against:
- u = F*1000/(60*A*eps) conversions
- nu_opt = sqrt(b/c) closed form
- Kozeny-Carman pressure (~910 bar for 1.7um/2.1x100mm/0.6mL-min/0.9cP)
- Snyder & Dolan App. IV Table IV.1(b) viscosities
"""
from __future__ import annotations

import math

import pytest

from app.core.lss import van_deemter as vd


@pytest.fixture
def uhplc_col() -> vd.ColumnGeometry:
    # 2.1 x 100 mm, 1.7 um fully porous (BEH-class)
    return vd.ColumnGeometry(
        length_mm=100.0, inner_diameter_mm=2.1,
        particle_size_um=1.7, particle_type="fully_porous",
    )


@pytest.fixture
def hplc_col() -> vd.ColumnGeometry:
    # 4.6 x 150 mm, 5 um fully porous (classic HPLC)
    return vd.ColumnGeometry(
        length_mm=150.0, inner_diameter_mm=4.6,
        particle_size_um=5.0, particle_type="fully_porous",
    )


@pytest.fixture
def cs_col() -> vd.ColumnGeometry:
    # 2.1 x 100 mm, 2.7 um core-shell (Kinetex/Poroshell-class)
    return vd.ColumnGeometry(
        length_mm=100.0, inner_diameter_mm=2.1,
        particle_size_um=2.7, particle_type="core_shell",
    )


class TestViscosity:
    def test_pure_water_25c(self):
        eta = vd.mobile_phase_viscosity_cp("acetonitrile", 0.0, 25.0)
        assert eta == pytest.approx(0.89, abs=0.01)

    def test_pure_acn_25c(self):
        eta = vd.mobile_phase_viscosity_cp("acetonitrile", 1.0, 25.0)
        assert eta == pytest.approx(0.35, abs=0.01)

    def test_pure_meoh_25c(self):
        eta = vd.mobile_phase_viscosity_cp("methanol", 1.0, 25.0)
        assert eta == pytest.approx(0.56, abs=0.01)

    def test_meoh_water_nonideal_max(self):
        # MeOH-water peaks ~1.6 cP near 50% v/v — must exceed pure water
        eta_mix = vd.mobile_phase_viscosity_cp("methanol", 0.5, 25.0)
        eta_w = vd.mobile_phase_viscosity_cp("methanol", 0.0, 25.0)
        assert eta_mix > 1.5 * eta_w * 0.9  # clearly non-ideal
        assert eta_mix == pytest.approx(1.62, abs=0.02)

    def test_viscosity_decreases_with_temperature(self):
        e20 = vd.mobile_phase_viscosity_cp("acetonitrile", 0.3, 20.0)
        e40 = vd.mobile_phase_viscosity_cp("acetonitrile", 0.3, 40.0)
        e60 = vd.mobile_phase_viscosity_cp("acetonitrile", 0.3, 60.0)
        assert e20 > e40 > e60

    def test_extrapolation_beyond_grid(self):
        # Arrhenius scaling below 15 C should raise viscosity
        e10 = vd.mobile_phase_viscosity_cp("acetonitrile", 0.5, 10.0)
        e15 = vd.mobile_phase_viscosity_cp("acetonitrile", 0.5, 15.0)
        assert e10 > e15

    def test_unknown_solvent_rejected(self):
        with pytest.raises(ValueError):
            vd.mobile_phase_viscosity_cp("thf", 0.5, 25.0)


class TestDiffusion:
    def test_wilke_chang_small_molecule(self):
        eta = vd.mobile_phase_viscosity_cp("acetonitrile", 0.5, 40.0)
        dm = vd.wilke_chang_dm_m2_s(300.0, "acetonitrile", 0.5, 40.0, eta)
        # Small molecule in ACN/water: expect ~5e-10 .. 2e-9 m^2/s
        assert 4e-10 < dm < 3e-9

    def test_dm_increases_with_temperature(self):
        e25 = vd.mobile_phase_viscosity_cp("acetonitrile", 0.5, 25.0)
        e60 = vd.mobile_phase_viscosity_cp("acetonitrile", 0.5, 60.0)
        d25 = vd.wilke_chang_dm_m2_s(300.0, "acetonitrile", 0.5, 25.0, e25)
        d60 = vd.wilke_chang_dm_m2_s(300.0, "acetonitrile", 0.5, 60.0, e60)
        assert d60 > d25


class TestVelocityFlow:
    def test_roundtrip(self):
        f = 0.42
        u = vd.flow_to_linear_velocity(f, 2.1, 0.68)
        assert vd.linear_velocity_to_flow(u, 2.1, 0.68) == pytest.approx(f)

    def test_known_value_21mm(self):
        # dc=2.1 mm, eps=0.68, F=0.4 -> u = 400uL/min / (pi*1.05^2*0.68 mm2)
        u = vd.flow_to_linear_velocity(0.4, 2.1, 0.68)
        assert u == pytest.approx(2.83, abs=0.05)

    def test_diameter_scaling_preserves_velocity(self):
        # F2 = F1*(dc2/dc1)^2 keeps u constant
        u1 = vd.flow_to_linear_velocity(1.0, 4.6, 0.68)
        f2 = vd.linear_velocity_to_flow(u1, 2.1, 0.68)
        assert f2 == pytest.approx(1.0 * (2.1 / 4.6) ** 2, rel=1e-6)

    def test_holdup(self):
        col = vd.ColumnGeometry(100.0, 2.1, 1.7, "fully_porous")
        v0 = vd.holdup_volume_ml(2.1, 100.0, col.resolved_eps_t())
        # A=3.46mm2 *100mm*0.68 = 235mm3 = 0.235 mL
        assert v0 == pytest.approx(0.235, abs=0.005)


class TestVanDeemter:
    def test_optimum_closed_form(self):
        # nu_opt = sqrt(b/c) = sqrt(2/0.05) = 6.32
        u = vd.optimal_velocity_mm_s(1.7, 1e-9, 1.0, 2.0, 0.05)
        assert u == pytest.approx(6.32 * 1e-3 / 1.7e-3, rel=1e-3)

    def test_optimum_matches_curve_minimum(self, uhplc_col):
        dm, eta = 1e-9, 0.7
        opt = vd.optimize_efficiency(uhplc_col, dm, eta, 2000.0)
        # Scan the curve: no point may beat the closed-form optimum
        curve = vd.van_deemter_curve(uhplc_col, dm, eta, 0.02, 2.0, 200)
        assert all(p.h_um >= opt.h_um - 1e-9 for p in curve)
        assert opt.h_um == pytest.approx(
            uhplc_col.particle_size_um * (1.0 + 2 * math.sqrt(2.0 * 0.05)),
            rel=1e-6)

    def test_smaller_particles_shift_optimum_higher(self):
        dm = 1e-9
        u5 = vd.optimal_velocity_mm_s(5.0, dm, *vd.VD_COEFFICIENTS["fully_porous"])
        u17 = vd.optimal_velocity_mm_s(1.7, dm, *vd.VD_COEFFICIENTS["fully_porous"])
        assert u17 / u5 == pytest.approx(5.0 / 1.7, rel=1e-9)

    def test_realistic_optimal_flows(self):
        dm = 1e-9
        eta = vd.mobile_phase_viscosity_cp("acetonitrile", 0.5, 40.0)
        # 4.6x150, 5um FPP -> ~0.8-1.2 mL/min
        col46 = vd.ColumnGeometry(150.0, 4.6, 5.0, "fully_porous")
        o46 = vd.optimize_efficiency(col46, dm, eta, 400.0)
        assert 0.6 < o46.flow_ml_min < 1.5
        # 2.1x100, 1.7um FPP -> ~0.4-0.7 mL/min
        col21 = vd.ColumnGeometry(100.0, 2.1, 1.7, "fully_porous")
        o21 = vd.optimize_efficiency(col21, dm, eta, 1500.0)
        assert 0.3 < o21.flow_ml_min < 0.8

    def test_h_min_realistic(self, uhplc_col):
        h = vd.plate_height_um(3.7, 1.7, 1e-9, 1.0, 2.0, 0.05)
        assert 2.0 < h < 4.0  # H ~2.8 um for 1.7 um particles
        n = vd.plate_count(100.0, h)
        assert 25000 < n < 50000


class TestPressure:
    def test_kozeny_reference_case(self):
        # 1.7um, 100mm, 2.1mm ID, 0.6 mL/min, eta=0.9cP -> ~900 bar
        p = vd.backpressure_bar(0.6, 2.1, 100.0, 1.7, 0.9)
        assert 800 < p < 1100

    def test_pressure_quadratic_in_particles(self):
        p17 = vd.backpressure_bar(0.4, 2.1, 100.0, 1.7, 0.9)
        p34 = vd.backpressure_bar(0.4, 2.1, 100.0, 3.4, 0.9)
        assert p17 / p34 == pytest.approx(4.0, rel=1e-9)

    def test_pressure_linear_in_flow_and_length(self):
        p1 = vd.backpressure_bar(0.4, 2.1, 100.0, 1.7, 0.9)
        p2 = vd.backpressure_bar(0.8, 2.1, 100.0, 1.7, 0.9)
        p3 = vd.backpressure_bar(0.4, 2.1, 200.0, 1.7, 0.9)
        assert p2 / p1 == pytest.approx(2.0, rel=1e-9)
        assert p3 / p1 == pytest.approx(2.0, rel=1e-9)


class TestOptimizer:
    def test_pressure_capped_optimum(self, uhplc_col):
        # Very low limit forces capping
        opt = vd.optimize_efficiency(uhplc_col, 1e-9, 0.9, 100.0)
        assert opt.pressure_limited
        assert opt.pressure_bar <= 100.0 + 1e-6
        assert opt.notes

    def test_speed_mode_binds_pressure(self, cs_col):
        opt = vd.optimize_speed(cs_col, 1e-9, 0.7, 10000, 600.0)
        assert opt.mode == "speed_at_plates"
        assert opt.pressure_bar == pytest.approx(600.0)
        assert opt.required_length_mm is not None and opt.required_length_mm > 0
        # Length is self-consistent: N = L/H
        assert opt.required_length_mm * 1000 / opt.h_um == pytest.approx(10000, rel=1e-6)
        # t0 = L/u
        assert opt.t0_s == pytest.approx(
            opt.required_length_mm / opt.u_mm_s, rel=1e-3)

    def test_speed_mode_infeasible_target(self, hplc_col):
        # Enormous N at tiny pressure on 5um -> infeasible
        opt = vd.optimize_speed(hplc_col, 1e-9, 0.9, 500000, 50.0)
        assert opt.n == 0.0
        assert any("infeasible" in n.lower() for n in opt.notes)

    def test_speed_beats_efficiency_time(self, cs_col):
        # At the kinetic optimum the same N arrives faster than running
        # the fixed column at its Van Deemter optimum would deliver N
        eta, dm = 0.7, 1e-9
        eff = vd.optimize_efficiency(cs_col, dm, eta, 600.0)
        spd = vd.optimize_speed(cs_col, dm, eta, eff.n, 600.0)
        assert spd.u_mm_s > eff.u_mm_s
        assert spd.t0_s < eff.t0_s or spd.required_length_mm <= cs_col.length_mm


class TestDiameterMap:
    def test_map_scaling(self, uhplc_col):
        dm, eta = 1e-9, 0.7
        rows = vd.diameter_map(uhplc_col, dm, eta, current_flow_ml_min=0.4)
        by_id = {r.inner_diameter_mm: r for r in rows}
        # F_opt ∝ dc^2 at fixed u
        f21 = by_id[2.1].optimal_flow_ml_min
        f46 = by_id[4.6].optimal_flow_ml_min
        assert f46 / f21 == pytest.approx((4.6 / 2.1) ** 2, rel=1e-9)
        # Geometric rescale of current flow
        assert by_id[1.0].scaled_flow_ml_min == pytest.approx(
            0.4 * (1.0 / 2.1) ** 2, rel=1e-9)
        # Same u and N everywhere
        assert all(r.u_mm_s == pytest.approx(by_id[2.1].u_mm_s) for r in rows)
        assert all(r.n == pytest.approx(by_id[2.1].n) for r in rows)
        # Pressure falls with ID^2 at fixed u (u_sup ∝ u*eps same; wait:
        # u_sup = u*eps_T is ID-independent -> same F/A? no:
        # at fixed u, u_sup = u*eps_T identical for all IDs -> dP equal)
        assert all(r.pressure_bar == pytest.approx(by_id[2.1].pressure_bar)
                   for r in rows)


class TestAssessFlow:
    def test_verdicts(self, uhplc_col):
        dm, eta = 1e-9, 0.7
        opt = vd.optimize_efficiency(uhplc_col, dm, eta, 2000.0)
        good = vd.assess_flow(uhplc_col, dm, eta, opt.flow_ml_min)
        assert good["verdict"] == "optimal"
        assert good["efficiency_vs_optimum_pct"] == pytest.approx(100.0, abs=0.5)
        low = vd.assess_flow(uhplc_col, dm, eta, opt.flow_ml_min * 0.3)
        assert low["verdict"].startswith("below")
        high = vd.assess_flow(uhplc_col, dm, eta, opt.flow_ml_min * 3.0)
        assert high["verdict"].startswith("above")
