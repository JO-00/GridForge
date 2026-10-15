import numpy as np
import matplotlib.pyplot as plt


def generate_solar_curves(cloudiness: float, seed: int = 42):
    if not 0.0 <= cloudiness <= 1.0:
        raise ValueError("cloudiness must be between 0 and 1")

    rng = np.random.default_rng(seed)

    minutes = np.arange(24 * 60)
    time_h = minutes / 60.0

    sunrise, sunset = 6.0, 18.0
    daylight_duration = sunset - sunrise

    # Clear-sky reference envelope
    daylight = np.clip(
        np.sin(np.pi * (time_h - sunrise) / daylight_duration),
        0.0,
        None,
    )
    clear_sky = 950.0 * daylight**1.5

    # --------------------------------------------------
    # Cloud-event pattern: prominent when partly cloudy
    # --------------------------------------------------
    cloud_factor = np.ones_like(time_h)

    # Fewer visible, distinct cloud events as overcast
    # conditions become more dominant.
    n_clouds = rng.poisson(10)

    for _ in range(n_clouds):
        center_h = rng.triangular(6.0, 13.0, 18.0)

        progress = (center_h - sunrise) / daylight_duration
        midday_strength = np.sin(np.pi * progress)

        # Width depends on peak time
        min_sigma = 3.0 + 7.0 * midday_strength
        max_sigma = 15.0 + 35.0 * midday_strength

        sigma_minutes = rng.uniform(min_sigma, max_sigma)
        sigma_hours = sigma_minutes / 60.0

        # Random attenuation, stronger events more likely near midday
        max_attenuation = 0.15 + 0.75 * midday_strength
        attenuation = rng.uniform(0.10, max_attenuation)

        dip = attenuation * np.exp(
            -0.5 * ((time_h - center_h) / sigma_hours) ** 2
        )

        cloud_factor *= 1.0 - dip

    # Fade distinct cloud dips as the sky becomes overcast.
    # At cloudiness=1, their effect disappears.
    cloud_factor = (
        1.0 - cloudiness
    ) * cloud_factor + cloudiness

    # --------------------------------------------------
    # Persistent overcast attenuation
    # --------------------------------------------------
    # Partly cloudy: baseline near clear-sky envelope.
    # Overcast: persistent diffuse-light approximation.
    overcast_factor = 1.0 - 0.70 * cloudiness

    irradiance = clear_sky * cloud_factor * overcast_factor

    # Smaller fluctuations under overcast conditions.
    noise_std = 0.025 * (1.0 - cloudiness) + 0.005 * cloudiness

    raw_noise = rng.normal(0.0, noise_std, len(minutes))
    smooth_noise = np.convolve(
        raw_noise,
        np.ones(9) / 9,
        mode="same",
    )

    irradiance *= np.clip(1.0 + smooth_noise, 0.90, 1.10)
    irradiance = np.clip(irradiance, 0.0, None)

    # --------------------------------------------------
    # Cell temperature
    # --------------------------------------------------
    ambient_temperature = (
        23.0
        + 5.0 * np.sin(2.0 * np.pi * (time_h - 9.0) / 24.0)
    )

    target_temperature = ambient_temperature + 0.03 * irradiance

    cell_temperature = np.empty_like(time_h)
    cell_temperature[0] = ambient_temperature[0]

    response = 1.0 - np.exp(-1.0 / 20.0)

    for i in range(1, len(minutes)):
        cell_temperature[i] = (
            cell_temperature[i - 1]
            + response * (
                target_temperature[i] - cell_temperature[i - 1]
            )
        )

    # Hardcoded temperature variability: std = 0.3 °C
    cell_temperature += rng.normal(0.0, 0.3, len(minutes))

    return time_h, irradiance, cell_temperature



if __name__ == "__main__":
    time_h, irradiance, cell_temperature = generate_solar_curves(
        cloudiness=0.5,
        seed=42,
    )

    plt.figure(figsize=(12, 4))
    plt.plot(time_h, irradiance)
    plt.xlabel("Time (hours)")
    plt.ylabel("Irradiance (W/m²)")
    plt.title("Solar Irradiance")
    plt.xlim(0, 24)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(12, 4))
    plt.plot(time_h, cell_temperature)
    plt.xlabel("Time (hours)")
    plt.ylabel("Cell Temperature (°C)")
    plt.title("PV Cell Temperature")
    plt.xlim(0, 24)
    plt.grid(True)
    plt.tight_layout()
    plt.show()