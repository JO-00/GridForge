from dataclasses import dataclass



# a very simplified inverter, will add a ton of stuff here, this is just a mock class for now

@dataclass
class SolarInverter:
    rated_power_w: float = 20000.0
    efficiency: float = 0.97

    dc_voltage_v: float = 0.0
    dc_current_a: float = 0.0
    dc_power_w: float = 0.0
    ac_power_w: float = 0.0
    losses_w: float = 0.0
    status: str = "OFF"

    def step(self, dc_voltage_v: float, dc_current_a: float) -> None:
        self.dc_voltage_v = max(0.0, dc_voltage_v)
        self.dc_current_a = max(0.0, dc_current_a)
        self.dc_power_w = self.dc_voltage_v * self.dc_current_a

        if self.dc_power_w <= 0:
            self.status = "OFF"
            self.ac_power_w = 0.0
            self.losses_w = 0.0
            return

        self.status = "RUNNING"
        self.ac_power_w = min(
            self.dc_power_w * self.efficiency,
            self.rated_power_w,
        )
        self.losses_w = self.dc_power_w - self.ac_power_w