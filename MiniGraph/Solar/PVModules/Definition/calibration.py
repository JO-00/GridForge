
import json
from math import log10

import numpy as np
from scipy.optimize import minimize_scalar

from PVModules.Definition import pv_module


# Datasheet values at Standard Test Conditions (STC).
ISC = 10.44
VOC = 59.12
VMP = 48.6
IMP = 10.29

IRRADIANCE = 1000.0
CELL_TEMPERATURE = 25.0
PMP = VMP * IMP


# Normalization scales: each constraint is scored relative to
# an explicit, meaningful tolerance scale.
ISC_SCALE_A = 0.02
VOC_CURRENT_SCALE_A = 0.02
IMP_SCALE_A = 0.02
MPP_VOLTAGE_SCALE_V = 0.2


# Bounds in optimizer coordinates:
# x = [log10(I0), Rs, log10(Rsh), n]
LOWER_BOUNDS = np.array([
    -12.0,
    0.001,
    log10(50.0),
    0.8,
])

UPPER_BOUNDS = np.array([
    -6.0,
    2.0,
    log10(100_000.0),
    2.0,
])

# Initial exploration steps in the same coordinates as x.
INITIAL_STEPS = np.array([
    0.5,   # log10(I0): multiplicative changes
    0.1,   # Rs, ohms
    0.5,   # log10(Rsh): multiplicative changes
    0.1,   # ideality factor
])

MIN_STEPS = np.array([
    0.01,
    0.001,
    0.01,
    0.002,
])

MAX_CYCLES = 200
MIN_SCORE_IMPROVEMENT = 1e-8


def calibrate_diode(module: pv_module.PVModule) -> dict:
    diode = module.config.diode

    # These are reference inputs, not optimization variables.
    # Fix the configuration itself if this check fails.
    if not np.isclose(diode.isc_ref, ISC, rtol=0.0, atol=1e-6):
        raise ValueError(
            f"diode.isc_ref is {diode.isc_ref}, but the datasheet "
            f"reference Isc is {ISC} A. Update the module config first."
        )

    if not np.isclose(
        diode.ref_irradiance, IRRADIANCE, rtol=0.0, atol=1e-6
    ):
        raise ValueError(
            f"diode.ref_irradiance must be {IRRADIANCE} W/m² "
            "for this STC calibration."
        )

    if not np.isclose(
        diode.T_ref, CELL_TEMPERATURE, rtol=0.0, atol=1e-6
    ):
        raise ValueError(
            f"diode.T_ref must be {CELL_TEMPERATURE} °C "
            "for this STC calibration."
        )

    if module.config.series_cells <= 0:
        raise ValueError("series_cells must be positive.")

    # Evaluate every candidate at the same reference conditions.
    module.state.irradiance_w_m2 = IRRADIANCE
    module.state.cell_temperature_c = CELL_TEMPERATURE

    # Preserve the module's existing parameter values as our starting point.
    x = np.array([
        log10(diode.saturation_current_a),
        diode.series_resistance_ohm,
        log10(diode.shunt_resistance_ohm),
        diode.ideality_factor,
    ], dtype=float)

    x = np.clip(
        x,
        LOWER_BOUNDS + 1e-12,
        UPPER_BOUNDS - 1e-12,
    )

    def apply_parameters(candidate: np.ndarray) -> None:
        diode.saturation_current_a = 10.0 ** candidate[0]
        diode.series_resistance_ohm = float(candidate[1])
        diode.shunt_resistance_ohm = 10.0 ** candidate[2]
        diode.ideality_factor = float(candidate[3])

    def find_peak() -> tuple[float, float, float]:
        """
        Find the natural maximum of P(V) = V * I(V).

        Returns:
            peak_voltage, peak_current, peak_power

        This stage locates the peak. It does not force the peak
        to occur at the datasheet VMP.
        """
        def negative_power(voltage_v: float) -> float:
            current_a = module.current_at_voltage(voltage_v)
            return -(voltage_v * current_a)

        result = minimize_scalar(
            negative_power,
            bounds=(0.0, VOC),
            method="bounded",
            options={
                "xatol": 0.005,
                "maxiter": 100,
            },
        )

        if not result.success or not np.isfinite(result.fun):
            raise ValueError("Could not locate the power maximum.")

        peak_voltage = float(result.x)
        peak_current = module.current_at_voltage(peak_voltage)
        peak_power = peak_voltage * peak_current

        # A valid generating-curve maximum should be interior.
        if not (0.0 < peak_voltage < VOC):
            raise ValueError("The power maximum is not interior.")

        if peak_current <= 0.0 or peak_power <= 0.0:
            raise ValueError("The power maximum is not generating.")

        return peak_voltage, peak_current, peak_power

    def evaluate(candidate: np.ndarray) -> tuple[float, dict]:
        """
        Evaluate the four calibration constraints independently:
        1. Short-circuit current
        2. Open-circuit current
        3. Current at the datasheet VMP
        4. Location of the simulated power peak
        """
        apply_parameters(candidate)

        try:
            isc_simulated = module.current_at_voltage(0.0)
            current_at_voc = module.current_at_voltage(VOC)
            current_at_vmp = module.current_at_voltage(VMP)

            peak_voltage, peak_current, peak_power = find_peak()

            # Normalize errors so their units and magnitudes do not
            # accidentally determine which constraints dominate.
            errors = {
                "isc": (isc_simulated - ISC) / ISC_SCALE_A,
                "voc_current": current_at_voc / VOC_CURRENT_SCALE_A,
                "imp": (current_at_vmp - IMP) / IMP_SCALE_A,
                "mpp_voltage": (
                    peak_voltage - VMP
                ) / MPP_VOLTAGE_SCALE_V,
            }

            score = float(sum(error**2 for error in errors.values()))

            details = {
                "score": score,
                "isc_a": isc_simulated,
                "current_at_voc_a": current_at_voc,
                "current_at_vmp_a": current_at_vmp,
                "power_at_vmp_w": VMP * current_at_vmp,
                "peak_voltage_v": peak_voltage,
                "peak_current_a": peak_current,
                "peak_power_w": peak_power,
                "errors": errors,
            }

            if not np.isfinite(score):
                raise ValueError("Non-finite calibration score.")

            return score, details

        except (
            ValueError,
            OverflowError,
            FloatingPointError,
            ZeroDivisionError,
        ):
            return float("inf"), {}

    # Ensure the starting candidate is valid.
    current_score, current_details = evaluate(x)

    if not np.isfinite(current_score):
        raise ValueError(
            "The initial diode parameters could not produce a valid "
            "calibration curve. Check the configuration and bounds."
        )

    steps = INITIAL_STEPS.copy()
    history = []
    converged = False

    print("Starting bounded round-robin calibration")
    print(f"Initial objective score: {current_score:.8g}")

    for cycle in range(1, MAX_CYCLES + 1):
        score_at_cycle_start = current_score

        # Visit every parameter in a fixed, deterministic order.
        for parameter_index in range(len(x)):
            best_x = x.copy()
            best_score = current_score
            best_details = current_details

            # Explore one step in each direction, without changing
            # any other parameter.
            for direction in (-1.0, 1.0):
                candidate = x.copy()

                candidate[parameter_index] += (
                    direction * steps[parameter_index]
                )

                # Do not leave the physical/search bounds.
                candidate = np.clip(
                    candidate,
                    LOWER_BOUNDS,
                    UPPER_BOUNDS,
                )

                candidate_score, candidate_details = evaluate(candidate)

                if candidate_score < best_score:
                    best_x = candidate
                    best_score = candidate_score
                    best_details = candidate_details

            # Commit only the best improving candidate.
            if best_score < current_score:
                x = best_x
                current_score = best_score
                current_details = best_details

                # Restore the committed parameters after evaluating
                # alternative candidates.
                apply_parameters(x)

        cycle_improvement = score_at_cycle_start - current_score

        history.append({
            "cycle": cycle,
            "score": current_score,
            "improvement": cycle_improvement,
            "steps": steps.copy(),
        })

        print(
            f"Cycle {cycle:3d} | "
            f"score={current_score:.8g} | "
            f"improvement={cycle_improvement:.4g} | "
            f"steps={np.array2string(steps, precision=4)}"
        )

        # If the entire round has stalled, progressively explore
        # smaller changes around the current best solution.
        if cycle_improvement <= MIN_SCORE_IMPROVEMENT:
            steps *= 0.5

            if np.all(steps <= MIN_STEPS):
                converged = True
                break

    # Ensure the final model holds the best parameters.
    apply_parameters(x)

    # Re-evaluate the final candidate from scratch.
    final_score, final = evaluate(x)
    apply_parameters(x)

    print("\n========== Calibration result ==========")
    print(f"Converged by step-size criterion: {converged}")
    print(f"Cycles completed: {cycle}")
    print(f"Final objective score: {final_score:.8g}")

    print("\nFitted diode parameters:")
    print(f"  Saturation current I0: {diode.saturation_current_a:.10g} A")
    print(f"  Series resistance Rs:  {diode.series_resistance_ohm:.10g} ohm")
    print(f"  Shunt resistance Rsh:  {diode.shunt_resistance_ohm:.10g} ohm")
    print(f"  Ideality factor n:     {diode.ideality_factor:.10g}")

    print("\nIndividual constraints:")
    print(f"  Isc: {final['isc_a']:.6f} A (target {ISC:.6f} A)")
    print(
        f"  I(Voc): {final['current_at_voc_a']:.6f} A "
        "(target 0 A)"
    )
    print(
        f"  I(Vmp): {final['current_at_vmp_a']:.6f} A "
        f"(target {IMP:.6f} A)"
    )
    print(
        f"  P(Vmp): {final['power_at_vmp_w']:.6f} W "
        f"(target {PMP:.6f} W)"
    )
    print(
        f"  Simulated peak voltage: {final['peak_voltage_v']:.6f} V "
        f"(target {VMP:.6f} V)"
    )
    print(
        f"  Simulated peak current: {final['peak_current_a']:.6f} A"
    )
    print(
        f"  Simulated peak power: {final['peak_power_w']:.6f} W "
        f"(target {PMP:.6f} W)"
    )

    print("\nNormalized residuals:")
    for name, error in final["errors"].items():
        print(f"  {name}: {error:+.6f}")

    return {
        "parameters": {
            "saturation_current_a": diode.saturation_current_a,
            "series_resistance_ohm": diode.series_resistance_ohm,
            "shunt_resistance_ohm": diode.shunt_resistance_ohm,
            "ideality_factor": diode.ideality_factor,
        },
        "score": final_score,
        "converged": converged,
        "cycles": cycle,
        "peak": {
            "voltage_v": final["peak_voltage_v"],
            "current_a": final["peak_current_a"],
            "power_w": final["peak_power_w"],
        },
        "constraints": final,
        "history": history,
    }


def calibrate_pv_module() -> dict:
    with open("Config/PVModuleConfig.json", "r", encoding="utf-8") as file:
        raw_config = json.load(file)

    config = pv_module.PVModuleConfig.from_dict(raw_config)
    module = pv_module.PVModule("1", config)

    result = calibrate_diode(module)

    # The fitted values can be copied back into your JSON config.
    print("\nUse these fitted values in the diode configuration:")
    print(json.dumps(result["parameters"], indent=2))

    return result


if __name__ == "__main__":
    calibrate_pv_module()
