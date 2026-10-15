
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

# sensors arent aggregated yet, they also need some testing before we fully rely on the fault injections

@dataclass
class SensorConfig:
    noise_std: float = 0.0
    bias: float = 0.0
    drift_per_step: float = 0.0

    stuck_probability: float = 0.0
    spike_probability: float = 0.0
    dropout_probability: float = 0.0

    spike_magnitude: float = 0.0


class Sensor:
    def __init__(
        self,
        sensor_id: str,
        component_id: str,
        measurement_type: str,
        unit: str,
        config: SensorConfig,
    ):
        self.sensor_id = sensor_id
        self.component_id = component_id
        self.measurement_type = measurement_type
        self.unit = unit
        self.config = config

    def inject_noise(
        self,
        seed: int,
        time: npt.ArrayLike,
        curve: npt.ArrayLike,
    ) -> tuple[np.ndarray, np.ndarray]:
        cfg = self.config
        values = np.asarray(curve, dtype=float).copy()
        timestamps = np.asarray(time)

        if values.ndim != 1 or timestamps.ndim != 1:
            raise ValueError("time and curve must be one-dimensional")

        if len(values) != len(timestamps):
            raise ValueError("time and curve must have the same length")

        if not np.all(np.isfinite(values)):
            raise ValueError("curve must contain finite values")

        for name, probability in (
            ("stuck_probability", cfg.stuck_probability),
            ("spike_probability", cfg.spike_probability),
            ("dropout_probability", cfg.dropout_probability),
        ):
            if not 0.0 <= probability <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")

        if cfg.noise_std < 0:
            raise ValueError("noise_std cannot be negative")

        if cfg.spike_magnitude < 0:
            raise ValueError("spike_magnitude cannot be negative")

        rng = np.random.default_rng(seed)
        n = len(values)

        # Persistent bias and gradual drift.
        indices = np.arange(n, dtype=float)
        values += cfg.bias + cfg.drift_per_step * indices

        # Random measurement noise.
        values += rng.normal(0.0, cfg.noise_std, size=n)

        # Stuck readings: hold the previous observed value.
        stuck_mask = rng.random(n) < cfg.stuck_probability
        for i in range(1, n):
            if stuck_mask[i]:
                values[i] = values[i - 1]

        # Spikes: randomly perturb individual measurements.
        spike_mask = rng.random(n) < cfg.spike_probability
        spike_signs = rng.choice([-1.0, 1.0], size=n)
        values[spike_mask] += (
            spike_signs[spike_mask] * cfg.spike_magnitude
        )

        # Dropouts: represent missing measurements with NaN.
        dropout_mask = rng.random(n) < cfg.dropout_probability
        values[dropout_mask] = np.nan

        return timestamps.copy(), values
