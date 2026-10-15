
from dataclasses import dataclass
import json

DEBUG = False
with open("Config/SolarMainConfigs.json", "r") as f:
    data = json.load(f)["mppt_config"]


@dataclass
class MPPTController:
    initial_voltage_v: float = data["initial_voltage_v"]
    voltage_step_v: float = data["voltage_step_v"]
    min_voltage_v: float = data["min_voltage_v"]
    max_voltage_v: float = data["max_voltage_v"]

    previous_voltage_v: float | None = None
    previous_power_w: float | None = None
    direction: int = 1

    def step(self, measured_voltage_v: float, measured_power_w: float) -> float:
        global DEBUG
        if DEBUG:
            print("\n========== MPPT STEP ==========")
            print(f"Measured PV voltage : {measured_voltage_v:.3f} V")
            print(f"Measured PV power   : {measured_power_w:.3f} W")
            print(f"Previous voltage    : {self.previous_voltage_v}")
            print(f"Previous power      : {self.previous_power_w}")
            print(f"Direction before    : {self.direction:+d}")

        
        if self.previous_power_w is not None:
            delta_power = measured_power_w - self.previous_power_w

            if DEBUG:
                print(f"Power difference    : {delta_power:+.3f} W")

            # Algorithm: always runs, regardless of DEBUG.
            if delta_power < 0:
                self.direction *= -1

                if DEBUG:
                    print("Power decreased -> reversing direction")
            elif DEBUG:
                print("Power did not decrease -> keeping direction")

        elif DEBUG:
            print("First measurement -> no power comparison yet")

    
        if self.previous_voltage_v is None:
            next_voltage_v = self.initial_voltage_v
            if DEBUG:
                print("Using initial voltage target")
        else:
            next_voltage_v = (
                measured_voltage_v
                + self.direction * self.voltage_step_v
            )

        next_voltage_v = max(
            self.min_voltage_v,
            min(self.max_voltage_v, next_voltage_v),
        )

        # Update history on every step, including at voltage limits.
        self.previous_voltage_v = measured_voltage_v
        self.previous_power_w = measured_power_w
        if DEBUG:
            print(f"Direction after     : {self.direction:+d}")
            print(f"Next voltage target : {next_voltage_v:.3f} V")
            print("===============================")

        return next_voltage_v
