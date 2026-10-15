
import numpy as np
import matplotlib.pyplot as plt
from Solar.Sensors.sensor import SensorConfig , Sensor


def test_sensor_corruption():
    # Simulated 24-hour irradiance curve
    time = np.linspace(0, 24, 500)

    daylight = np.maximum(
        0.0,
        np.sin(np.pi * (time - 6) / 12),
    )
    true_curve = 800.0 * daylight

    # Configure a deliberately imperfect sensor
    config1 = SensorConfig(
        noise_std=18.0,
        bias=12.0,
        drift_per_step=0.02,
        stuck_probability=0.0,
        spike_probability=0.012,
        dropout_probability=0.0,
        spike_magnitude=100.0,
    )

    sensor1 = Sensor(
        sensor_id="irradiance_001",
        component_id="solar_array_001",
        measurement_type="irradiance",
        unit="W/m2",
        config=config1,
    )
    config2 = SensorConfig(
            noise_std=18.0,
            bias=12.0,
            drift_per_step=0.02,
            stuck_probability=0.0,
            spike_probability=0,
            dropout_probability=0.0,
            spike_magnitude=0,
        )
    
    sensor2 = Sensor(
        sensor_id="irradiance_001",
        component_id="solar_array_001",
        measurement_type="irradiance",
        unit="W/m2",
        config=config2,
    )

    # Transform the complete curve
    timestamps, measured_curve_sensor1 = sensor1.inject_noise(
        seed=42,
        time=time,
        curve=true_curve,
    )
    timestamps, measured_curve_sensor2 = sensor2.inject_noise(
            seed=42,
            time=time,
            curve=true_curve,
        )
    # Plot both curves
    plt.figure(figsize=(12, 5))

    plt.plot(
        time,
        true_curve,
        label="True irradiance",
        linewidth=2,
    )

    plt.plot(
        timestamps,
        measured_curve_sensor1,
        label="High Spikes",
        linewidth=1,
        alpha=0.8,
    )
    plt.plot(
        timestamps,
        measured_curve_sensor2,
        label="Low Spikes",
        linewidth=1,
        alpha=0.8,
    )

    plt.xlabel("Time (hours)")
    plt.ylabel("Irradiance (W/m²)")
    plt.title("True vs. Sensor-Measured Irradiance")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

    # Basic assertions
    assert np.array_equal(
        true_curve,
        800.0 * daylight,
    ), "The original curve was modified"

    assert not np.allclose(
        measured_curve,
        true_curve,
        equal_nan=True,
    ), "The sensor did not modify the curve"

    # Same seed + same input = same measurements
    _, repeated_curve = sensor.inject_noise(
        seed=42,
        time=time,
        curve=true_curve,
    )

    np.testing.assert_array_equal(
        measured_curve,
        repeated_curve,
    )

    print("Sensor corruption test passed!")


if __name__ == "__main__":
    test_sensor_corruption()
