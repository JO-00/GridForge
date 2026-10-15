import csv
from pathlib import Path

import numpy as np

from DCCombiner.Definition import DCCombiner
from PVModules.PVArray import PVArray
from PRNG import cloudy
from Inverter.Definition import SolarInverter
from Sensors.sensor import Sensor, SensorConfig


# ============================================================
# DATASET CONFIGURATION
# ============================================================

SEED = 42
WINDOW_SIZE = 100          # also the plant-simulation length per sample
N_SAMPLES = 20_000

OUTPUT_PATH = Path("dataset.csv")

# Proportions of generated sequences, not individual timestamps.
CLASS_PROPORTIONS = {
    "healthy": 0.20,
    "noise": 0.30,
    "bias": 0.10,
    "drift": 0.10,
    "spikes": 0.10,
    "stuck": 0.10,
    "dropout": 0.10,
}


# ============================================================
# 1. SIMULATE THE REAL SOLAR PLANT
# ============================================================

def simulate_plant(
    seed: int,
    n_steps: int = WINDOW_SIZE,
) -> dict[str, np.ndarray]:
    """
    Run the PV plant forward for `n_steps` and return the
    ground-truth physical trajectories.

    A fresh call produces an independent window: different
    cloudiness realisation, different environmental curve,
    different physical state.
    """

    pv_array = PVArray()
    dc_combiner = DCCombiner(pv_array)
    inverter = SolarInverter()

    time_h, irradiance, cell_temperature = (
        cloudy.generate_solar_curves(
            cloudiness=1,
            seed=seed,
        )
    )

    # `cloudy` may return more than we need; trim to exactly
    # `n_steps` so every batch has the same shape.
    time_h = np.asarray(time_h, dtype=float)[:n_steps]
    irradiance = np.asarray(irradiance, dtype=float)[:n_steps]
    cell_temperature = np.asarray(
        cell_temperature, dtype=float
    )[:n_steps]

    if len(irradiance) < n_steps:
        raise ValueError(
            f"cloudy.generate_solar_curves returned only "
            f"{len(irradiance)} samples; need {n_steps}. "
            f"Lower WINDOW_SIZE or increase curve length."
        )

    voltage = []
    current = []
    dc_power = []
    ac_power = []

    for irradiance_t, temperature_t in zip(
        irradiance, cell_temperature
    ):
        for pv_string in pv_array.pv_strings:
            for pv_module in pv_string.pv_modules:
                pv_module.update_conditions(
                    irradiance_t,
                    temperature_t,
                )

            pv_string.step()

        dc_combiner.step()

        v = dc_combiner.bus_bar.voltage_v
        i = dc_combiner.bus_bar.current_a

        voltage.append(v)
        current.append(i)
        dc_power.append(v * i)

        inverter.step(v, i)
        ac_power.append(inverter.ac_power_w)

    return {
        "time_h": time_h,
        "irradiance": irradiance,
        "cell_temperature": cell_temperature,
        "dc_voltage": np.asarray(voltage, dtype=float),
        "dc_current": np.asarray(current, dtype=float),
        "dc_power": np.asarray(dc_power, dtype=float),
        "ac_power": np.asarray(ac_power, dtype=float),
    }


# ============================================================
# 2. SENSOR CORRUPTION FUNCTIONS
# Each function receives a true physical sequence and returns
# the readings that the sensor would report.
# ============================================================

def generate_healthy(
    truth: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Healthy sensor with small ordinary measurement noise."""

    return truth.copy() + rng.normal(
        loc=0.0,
        scale=0.5,
        size=len(truth),
    )


def generate_noise(
    truth: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sensor with stronger random measurement noise."""

    sensor = Sensor(
        sensor_id="sensor_001",
        component_id="dc_combiner",
        measurement_type="dc_voltage",
        unit="V",
        config=SensorConfig(
            noise_std=18.0,
        ),
    )

    _, readings = sensor.inject_noise(
        seed=int(rng.integers(0, 2**32)),
        time=np.arange(len(truth)),
        curve=truth,
    )
    return readings


def generate_bias(
    truth: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sensor with a persistent calibration offset."""

    bias = rng.uniform(8.0, 25.0)

    sensor = Sensor(
        "sensor_001",
        "dc_combiner",
        "dc_voltage",
        "V",
        SensorConfig(bias=bias),
    )

    _, readings = sensor.inject_noise(
        seed=int(rng.integers(0, 2**32)),
        time=np.arange(len(truth)),
        curve=truth,
    )
    return readings


def generate_drift(
    truth: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sensor whose offset gradually changes over the window."""

    drift_rate = rng.uniform(0.03, 0.15)
    direction = rng.choice([-1.0, 1.0])

    sensor = Sensor(
        "sensor_001",
        "dc_combiner",
        "dc_voltage",
        "V",
        SensorConfig(
            drift_per_step=direction * drift_rate,
            noise_std=0.5,
        ),
    )

    _, readings = sensor.inject_noise(
        seed=int(rng.integers(0, 2**32)),
        time=np.arange(len(truth)),
        curve=truth,
    )
    return readings


def generate_spikes(
    truth: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sensor with occasional large positive or negative spikes."""

    sensor = Sensor(
        "sensor_001",
        "dc_combiner",
        "dc_voltage",
        "V",
        SensorConfig(
            noise_std=0.5,
            spike_probability=0.05,
            spike_magnitude=50.0,
        ),
    )

    _, readings = sensor.inject_noise(
        seed=int(rng.integers(0, 2**32)),
        time=np.arange(len(truth)),
        curve=truth,
    )
    return readings


def generate_stuck(
    truth: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sensor freezes at one value for a continuous interval."""

    readings = truth.copy()

    if len(readings) < 2:
        return readings

    start = int(rng.integers(0, len(readings) - 1))
    duration = int(
        rng.integers(2, max(3, len(readings) // 2 + 1))
    )
    end = min(len(readings), start + duration)

    frozen_value = readings[max(0, start - 1)]
    readings[start:end] = frozen_value

    return readings


def generate_dropout(
    truth: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sensor intermittently fails to report measurements."""

    readings = truth.copy()

    dropout_probability = rng.uniform(0.03, 0.15)
    mask = rng.random(len(readings)) < dropout_probability

    readings[mask] = np.nan
    return readings


# ============================================================
# 3. CLASS DISTRIBUTION
# ============================================================

GENERATORS = {
    "healthy": generate_healthy,
    "noise": generate_noise,
    "bias": generate_bias,
    "drift": generate_drift,
    "spikes": generate_spikes,
    "stuck": generate_stuck,
    "dropout": generate_dropout,
}


def make_class_schedule(
    n_samples: int,
    proportions: dict[str, float],
    rng: np.random.Generator,
) -> list[str]:
    """Create an approximately exact class distribution."""

    if not np.isclose(sum(proportions.values()), 1.0):
        raise ValueError("Class proportions must sum to 1.")

    if any(p < 0 for p in proportions.values()):
        raise ValueError("Class proportions cannot be negative.")

    raw_counts = {
        name: n_samples * proportion
        for name, proportion in proportions.items()
    }

    counts = {
        name: int(np.floor(count))
        for name, count in raw_counts.items()
    }

    remaining = n_samples - sum(counts.values())

    order = sorted(
        proportions,
        key=lambda name: raw_counts[name] - counts[name],
        reverse=True,
    )

    for name in order[:remaining]:
        counts[name] += 1

    schedule = [
        name
        for name, count in counts.items()
        for _ in range(count)
    ]

    rng.shuffle(schedule)
    return schedule


# ============================================================
# 4. BUILD THE WINDOWED DATASET
# ============================================================

def generate_dataset() -> None:
    rng = np.random.default_rng(SEED)

    labels = make_class_schedule(
        N_SAMPLES,
        CLASS_PROPORTIONS,
        rng,
    )

    time_columns = [
        f"t_{i:03d}" for i in range(WINDOW_SIZE)
    ]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "sample_id",
                "signal",
                "sim_seed",
                *time_columns,
                "label",
            ],
        )
        writer.writeheader()

        for sample_id, label in enumerate(labels):

            # One independent plant simulation per sample.
            sim_seed = int(rng.integers(0, 2**32))
            trajectories = simulate_plant(
                seed=sim_seed,
                n_steps=WINDOW_SIZE,
            )

            truth = trajectories["dc_voltage"]

            # Independent deterministic RNG for the corruption
            # stage of this specific sample.
            sample_rng = np.random.default_rng(
                int(rng.integers(0, 2**32))
            )

            readings = GENERATORS[label](truth, sample_rng)

            row = {
                "sample_id": sample_id,
                "signal": "dc_voltage",
                "sim_seed": sim_seed,
                "label": label,
            }

            row.update({
                column: value
                for column, value in zip(time_columns, readings)
            })

            writer.writerow(row)

            if (sample_id + 1) % 500 == 0:
                print(
                    f"  {sample_id + 1:6d}/{N_SAMPLES} "
                    f"samples written"
                )

    print(f"\nDataset written to: {OUTPUT_PATH.resolve()}")
    print(f"Rows: {N_SAMPLES}")
    print(f"Timesteps per row: {WINDOW_SIZE}")

    unique, counts = np.unique(labels, return_counts=True)
    print("\nClass distribution:")
    for name, count in zip(unique, counts):
        print(
            f"  {name:10s}: {count:5d} "
            f"({count / N_SAMPLES:.1%})"
        )


if __name__ == "__main__":
    generate_dataset()