
from dataclasses import dataclass, field
import json
with open("Config/PVModuleConfig.json","r") as f:
    init_v = json.load(f)["init_v"]

@dataclass
class PVModuleState:
    current_a: float
    irradiance_w_m2: float = 1000.0
    cell_temperature_c: float = 25.0
    voltage_v: float = init_v
    

    @property
    def power_w(self) -> float:
        return self.voltage_v * self.current_a
    

   

