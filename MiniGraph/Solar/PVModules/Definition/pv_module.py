
from math import exp

from PVModules.Definition.config import PVModuleConfig
from PVModules.Definition.state import PVModuleState
from scipy.optimize import brentq

DEBUG = False
BOLTZMANN_CONSTANT = 1.380649e-23
ELEMENTARY_CHARGE = 1.602176634e-19

class PVModule:
    def __init__(self, module_id: str, config: PVModuleConfig):
        assert isinstance(config, PVModuleConfig) , f"invalid config = {config}"
        self.id = module_id
        self.config = config
        self.state = PVModuleState(0)

    @property
    def thermal_voltage_v(self) -> float:
        temperature_k = self.state.cell_temperature_c + 273.15
        return (
            BOLTZMANN_CONSTANT * temperature_k
            / ELEMENTARY_CHARGE
        )

    def update_conditions(
        self,
        irradiance_w_m2: float,
        cell_temperature_c: float,
    ):
        assert irradiance_w_m2 >=0 , f"invalid negative irradiance = {irradiance_w_m2}"
        self.state.irradiance_w_m2 = irradiance_w_m2
        self.state.cell_temperature_c = cell_temperature_c
        self.state.current_a = self.current_at_voltage(self.state.voltage_v)

        


    def absorbed_diode_current(self, voltage_v: float):
        diode = self.config.diode
        a = (
            diode.ideality_factor
            * self.config.series_cells
            * self.thermal_voltage_v
        )

        return lambda current_a: diode.saturation_current_a * (
            exp(
                (voltage_v + current_a * diode.series_resistance_ohm)
                / a
            ) - 1
        )

    def current_lost_through_shunt(self, voltage_v: float):
        diode = self.config.diode

        return lambda current_a: (
            voltage_v + current_a * diode.series_resistance_ohm
        ) / diode.shunt_resistance_ohm


    def compute_photo_current(self):
        irradiance_ratio = (
            self.state.irradiance_w_m2 / self.config.diode.ref_irradiance
        )

        temperature_factor = 1.0 + (
            self.config.diode.alpha_sc
            * (self.state.cell_temperature_c - self.config.diode.T_ref)
        )

        return irradiance_ratio * self.config.diode.isc_ref * temperature_factor

    def current_residual(self, voltage_v: float):
        diode_current = self.absorbed_diode_current(voltage_v)
        shunt_current = self.current_lost_through_shunt(voltage_v)
        photocurrent = self.compute_photo_current()

        

        return lambda current_a: (
            photocurrent
            - diode_current(current_a)
            - shunt_current(current_a)
            - current_a
        )



    
    def current_at_voltage(self, voltage_v: float) -> float:
        global DEBUG
        residual = self.current_residual(voltage_v)

        # The residual is strictly decreasing for physically valid parameters.
        # Start with a current interval around the photocurrent.
        iph = self.compute_photo_current()
        lower = min(0.0, iph) - 1.0
        upper = max(0.0, iph) + 1.0

        f_lower = residual(lower)
        f_upper = residual(upper)

        # Expand the interval only a bounded number of times.
        # Unlike the previous loop, this cannot run away indefinitely.
        for _ in range(20):
            if f_lower >= 0.0 and f_upper <= 0.0:
                current = brentq(residual, lower, upper, xtol=1e-8)
                if DEBUG:
                    print(f"""
    current after diode = {self.absorbed_diode_current(voltage_v)(current)}
    current after shunt = {self.current_lost_through_shunt(voltage_v)(current)}
    """)
                return current

            if f_lower < 0.0:
                lower -= max(1.0, abs(lower))
                f_lower = residual(lower)

            if f_upper > 0.0:
                upper += max(1.0, abs(upper))
                f_upper = residual(upper)

        raise ValueError(
            f"Could not bracket current root at {voltage_v} V "
            f"after 20 bounded expansions. "
            f"Residuals: f({lower})={f_lower}, f({upper})={f_upper}"
        )
