import numpy as np
import matplotlib.pyplot as plt


def generate_solar_curves(
    summer_intensity: float,
    seed: int = 42,
):
    if not 0.0 <= summer_intensity <= 1.0:
        raise ValueError("summer_intensity must be between 0 and 1")

    rng = np.random.default_rng(seed)

    minutes = np.arange(24 * 60)
    time_h = minutes / 60.0

    # --------------------------------------------------
    # 1. Solar irradiance
    # --------------------------------------------------
    sunrise, sunset = 6.0, 18.0

    daylight = np.clip(
        np.sin(np.pi * (time_h - sunrise) / (sunset - sunrise)),
        0.0,
        None,
    )

    # Stronger summer conditions allow a higher peak irradiance.
    peak_irradiance = 1000.0 + 150.0 * summer_intensity
    irradiance = peak_irradiance * daylight**1.5

    # Small correlated fluctuations; std = 0.025
    raw_noise = rng.normal(0.0, 0.025, len(minutes))
    smooth_noise = np.convolve(
        raw_noise,
        np.ones(9) / 9,
        mode="same",
    )

    irradiance *= np.clip(1.0 + smooth_noise, 0.90, 1.10)
    irradiance = np.clip(irradiance, 0.0, None)

    # --------------------------------------------------
    # 2. Ambient temperature
    # --------------------------------------------------
    # Warm summer conditions at 0; scorching conditions at 1.
    daily_mean = 25.0 + 9.0 * summer_intensity
    daily_amplitude = 4.0 + 4.0 * summer_intensity

    temperature = (
        daily_mean
        + daily_amplitude
        * np.sin(2.0 * np.pi * (time_h - 9.0) / 24.0)
    )

    # Smooth background variability; std = 0.4 °C
    raw_temperature_noise = rng.normal(
        0.0, 0.4, len(minutes)
    )
    smooth_temperature_noise = np.convolve(
        raw_temperature_noise,
        np.ones(21) / 21,
        mode="same",
    )
    temperature += smooth_temperature_noise

    # --------------------------------------------------
    # 3. Random extreme-heat events at intensity >= 0.8
    # --------------------------------------------------
    if summer_intensity >= 0.8:
        severity = (summer_intensity - 0.8) / 0.2

        # More events as summer intensity approaches 1.
        n_events = rng.poisson(2.0 + 8.0 * severity)

        for _ in range(n_events):
            # Events are biased toward the warm afternoon.
            center_h = rng.triangular(9.0, 15.0, 20.0)

            # Event width depends on its peak time and varies.
            midday_strength = np.sin(
                np.pi * np.clip((center_h - 6.0) / 12.0, 0.0, 1.0)
            )
            sigma_minutes = rng.uniform(
                10.0 + 10.0 * midday_strength,
                30.0 + 50.0 * midday_strength,
            )
            sigma_hours = sigma_minutes / 60.0

            # Random extra heating: stronger at higher intensity.
            amplitude = rng.uniform(
                2.0,
                4.0 + 4.0 * severity,
            )

            temperature += amplitude * np.exp(
                -0.5 * ((time_h - center_h) / sigma_hours) ** 2
            )

    return time_h, irradiance, temperature


if __name__ == "__main__":
    time_h, irradiance, temperature = generate_solar_curves(
        summer_intensity=1,
        seed=45,
    )

    plt.figure(figsize=(12, 4))
    plt.plot(time_h, irradiance)
    plt.xlabel("Time (hours)")
    plt.ylabel("Irradiance (W/m²)")
    plt.title("Summer Solar Irradiance")
    plt.xlim(0, 24)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(12, 4))
    plt.plot(time_h, temperature)
    plt.xlabel("Time (hours)")
    plt.ylabel("Ambient Temperature (°C)")
    plt.title("Summer Ambient Temperature")
    plt.xlim(0, 24)
    plt.grid(True)
    plt.tight_layout()
    plt.show()