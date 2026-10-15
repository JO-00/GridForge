
import json
import pytest

from Definition.pv_module import PVModule
from Definition.config import PVModuleConfig


@pytest.fixture
def panel():
    with open("Config/PVModuleConfig.json", "r") as f:
        raw_config = json.load(f)

    config = PVModuleConfig.from_dict(raw_config)
    config.calibrate()
    config.apply_calibration()

    return PVModule("test-panel", config)


def test_photocurrent_at_reference_conditions(panel):
    panel.update_conditions(1000, 25)

    iph = panel.compute_photo_current()

    assert iph == pytest.approx(panel.config.isc_a, rel=1e-9)


def test_photocurrent_scales_with_irradiance(panel):
    panel.update_conditions(500, 25)

    iph = panel.compute_photo_current()

    assert iph == pytest.approx(7.0, rel=1e-9)


def test_photocurrent_increases_with_cell_temperature(panel):
    panel.update_conditions(1000, 45)

    iph = panel.compute_photo_current()

    assert iph == pytest.approx(14.14, rel=1e-9)


def test_short_circuit_current(panel):
    panel.update_conditions(1000, 25)

    current = panel.current_at_voltage(0.0)

    assert current == pytest.approx(panel.config.isc_a, rel=0.001)


def test_open_circuit_current(panel):
    panel.update_conditions(1000, 25)

    current = panel.current_at_voltage(panel.config.voc_v)

    assert current == pytest.approx(0.0, abs=1e-6)
def test_current_decreases_with_voltage(panel):
    panel.update_conditions(1000, 25)

    i_low = panel.current_at_voltage(10.0)
    i_mid = panel.current_at_voltage(25.0)
    i_high = panel.current_at_voltage(40.0)

    assert i_low > i_mid > i_high >= 0.0


def test_short_circuit_current(panel):
    panel.update_conditions(1000, 25)

    current = panel.current_at_voltage(0.0)

    assert current == pytest.approx(
        panel.config.isc_a, rel=0.001
    )


def test_open_circuit_current(panel):
    panel.update_conditions(1000, 25)

    current = panel.current_at_voltage(panel.config.voc_v)

    assert current == pytest.approx(0.0, abs=1e-6)


def test_current_root_satisfies_diode_equation(panel):
    panel.update_conditions(1000, 25)

    voltage = 25.0
    current = panel.current_at_voltage(voltage)
    residual = panel.current_residual(voltage)

    assert abs(residual(current)) < 1e-6


def test_zero_irradiance_produces_negligible_current(panel):
    panel.update_conditions(1e-6, 25)

    current = panel.current_at_voltage(10.0)
    print(current)
    assert current == pytest.approx(0.0, abs=0.1)


def test_visualization(panel):
    import matplotlib.pyplot as plt
    import numpy as np
    panel.update_conditions(200,25.0)

    voltages = (40,41,42,43,45)
    for voltage in voltages:
        print(f"current at voltage = {voltage}V = {panel.current_at_voltage(voltage)}A")

