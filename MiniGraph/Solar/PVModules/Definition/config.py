
from dataclasses import dataclass , field
import json

@dataclass
class DiodeConfig:
    saturation_current_a: float
    series_resistance_ohm: float
    shunt_resistance_ohm: float
    ideality_factor: float
    ref_irradiance : float
    isc_ref : float
    alpha_sc: float
    T_ref : float


@dataclass
class PVModuleConfig:
    rated_power_wp: float
    model: str
    voc_v_ref: float # open circuit voltage
    isc_a: float 
    series_cells: int
    diode: DiodeConfig
    calibration: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        diode = DiodeConfig(
            saturation_current_a=data["diode_model"]["saturation_current_a"],
            series_resistance_ohm=data["diode_model"]["series_resistance_ohm"],
            shunt_resistance_ohm=data["diode_model"]["shunt_resistance_ohm"],
            ideality_factor=data["diode_model"]["ideality_factor"],
            alpha_sc= data["diode_model"]["alpha_isc_per_c"],
            T_ref= data["diode_model"]["reference_cell_temperature_c"],
            isc_ref= data["isc_a"],
            ref_irradiance=data["diode_model"]["reference_irradiance_w_m2"]

        )

        return cls(
            rated_power_wp=data["rated_power_wp"],
            model=data["model"],
            voc_v_ref=data["voc_ref_v"],
            isc_a=data["isc_a"],
            series_cells=data["series_cells"],
            diode=diode,
        )
    



    def apply_calibration(self):
        calibration = self.calibration

        if not calibration or not calibration["success"]:
            raise ValueError("No successful calibration available.")

        params = calibration["parameters"]
        diode = self.diode

        diode.saturation_current_a = params["saturation_current_a"]
        diode.series_resistance_ohm = params["series_resistance_ohm"]
        diode.shunt_resistance_ohm = params["shunt_resistance_ohm"]
