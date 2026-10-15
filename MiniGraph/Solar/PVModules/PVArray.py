import json
from dataclasses import dataclass
from PVModules.Definition.pv_module import PVModule
from PVModules.Definition.config import PVModuleConfig

with open("Config/SolarMainConfigs.json","r") as f:
    SAMPLING_FREQUENCY = json.load(f)["sampling_frequency"]


@dataclass
class PVString:
    string_id: str
    pv_modules: list[PVModule]
    n_pv_modules : int
    voltage : float = 0
    current : float = 0

    def __init__(
        self,
        string_id: str,
        n_pv_modules: int,
        module_config: PVModuleConfig,
    ):
        self.string_id = string_id
        self.n_pv_modules = n_pv_modules
        self.pv_modules = [
            PVModule(
                module_id=f"{string_id}_module_{i}",
                config=module_config,
            )
            for i in range(n_pv_modules)
        ]
        self.step()

    def get_state(self):
        return self.current , self.voltage

    
    def step(self):
        self.voltage = self.pv_modules[0].state.voltage_v * self.n_pv_modules
        self.current = self.pv_modules[0].state.current_a

    def evaluate_at_voltage(self, string_voltage_v: float) -> float:
        if string_voltage_v < 0:
            raise ValueError("String voltage cannot be negative.")

        module_voltage_v = string_voltage_v / self.n_pv_modules
        module_currents = []

        for module in self.pv_modules:
            current_a = module.current_at_voltage(module_voltage_v)

            # Store the operating point, not just calculate the current.
            module.state.voltage_v = module_voltage_v
            module.state.current_a = current_a

            module_currents.append(current_a)

        # Assumes identical modules with equal voltage sharing.
        self.voltage = string_voltage_v
        self.current = sum(module_currents) / len(module_currents)

        return self.current


  



@dataclass
class PVArray:
    pv_strings: list[PVString]
    voltage: float = 0.0
    current: float = 0.0

    def __init__(self):
        with open("Config/SolarMainConfigs.json", "r") as f:
            solar_config = json.load(f)

        with open("Config/PVModuleConfig.json", "r") as f:
            module_config = PVModuleConfig.from_dict(json.load(f))

        n_pv_strings = solar_config.get("n_pv_strings", 4)
        n_pv_modules = solar_config.get(
            "n_pv_modules_per_pv_string", 10
        )

        self.pv_strings = [
            PVString(
                string_id=f"pv_string_{i}",
                n_pv_modules=n_pv_modules,
                module_config=module_config,
            )
            for i in range(n_pv_strings)
        ]

        self.voltage = 0.0
        self.current = 0.0

    def evaluate_at_voltage(self, array_voltage_v: float) -> float:
        if array_voltage_v < 0:
            raise ValueError("Array voltage cannot be negative.")

        # Parallel strings share the same voltage.
        self.current = sum(
            pv_string.evaluate_at_voltage(array_voltage_v)
            for pv_string in self.pv_strings
        )

        self.voltage = array_voltage_v
        return self.current

    def power_at_voltage(self, array_voltage_v: float) -> float:
        current_a = self.evaluate_at_voltage(array_voltage_v)
        return array_voltage_v * current_a


