
from dataclasses import dataclass, field
from typing import Optional
import math,json
from PVModules.PVArray import PVString , PVArray, SAMPLING_FREQUENCY
from DCCombiner.protection_mechanisms import SurgeProtectionDevice, DCBusbar, SPDState
from DCCombiner.mppt import MPPTController


@dataclass
class StringFuse:
    pv_string: PVString
    rated_current_a: float
    pre_arcing_i2t_a2s: float
    cooling_time_constant_s: float
    overload_exposure_a2s: float = 0.0
    blown: bool = False
    


    def __post_init__(self) -> None:
        if self.rated_current_a <= 0:
            raise ValueError("Rated current must be positive.")
        if self.pre_arcing_i2t_a2s <= 0:
            raise ValueError("Pre-arcing I²t must be positive.")
        if self.cooling_time_constant_s <= 0:
            raise ValueError("Cooling time constant must be positive.")

    def step(self) -> None:
        if self.blown:
            return  0.0 , self.pv_string.voltage
        if self.pv_string.current >= self.rated_current_a:
            self.overload_exposure_a2s += self.pv_string.current**2  / SAMPLING_FREQUENCY
        else:
            self.cool()
        
        if self.overload_exposure_a2s >= self.pre_arcing_i2t_a2s:
            self.blow()
            return 0.0 , self.pv_string.voltage

        return self.pv_string.current , self.pv_string.voltage
        

    def blow(self) -> None:
        self.blown = True


    def cool(self):
        dt_s = 1/SAMPLING_FREQUENCY
        self.overload_exposure_a2s *= math.exp(
            -dt_s / self.cooling_time_constant_s
        )


    def maintenance(self):
        self.blown = False
        self.overload_exposure_a2s = 0.0








@dataclass
class DCCombiner:
    bus_bar : DCBusbar
    surge_protection_device : SurgeProtectionDevice
    pv_array : PVArray
    mppt : Optional[MPPTController]
    string_fuses: list[StringFuse] = field(default_factory=list)
    n_pv_strings : int = 0



    def __init__(self, pv_array : PVArray):


        self.pv_array = pv_array
        with open("Config/SolarMainConfigs.json","r" ) as f:
            configs = json.load(f)
        cooling_time_constant_s = configs["dc_combiner"]["string_fuse"]["cooling_time_constant_s"]
        rated_current_a = configs["dc_combiner"]["string_fuse"]["rated_current_a"]
        threshold_surge_SPD_voltage = configs["dc_combiner"]["threshold_surge_SPD_voltage"]
        clamp_SPD_voltage = configs["dc_combiner"]["clamp_SPD_voltage"]
        pre_arcing_i2t_a2s=configs["dc_combiner"]["string_fuse"]["pre_arcing_i2t_a2s"]
        self.n_pv_strings = len(pv_array.pv_strings)

        self.string_fuses = [StringFuse(
            overload_exposure_a2s= 0,
            blown= False,
            pv_string= pv_string,
            rated_current_a=rated_current_a,
            cooling_time_constant_s=cooling_time_constant_s,
            pre_arcing_i2t_a2s=pre_arcing_i2t_a2s
        ) for pv_string in pv_array.pv_strings]

        self.surge_protection_device = SurgeProtectionDevice(
            surge_threshold_v=threshold_surge_SPD_voltage,
            clamp_SPD_voltage=clamp_SPD_voltage
        )
        self.bus_bar = DCBusbar()
        self.mppt = MPPTController()


    def step(self): # assuming they're arranged in parallel
        
        # 1. Measure the current PV operating point.
        measured_voltage_v = self.pv_array.voltage
        measured_power_w = measured_voltage_v * self.pv_array.current

        # 2. MPPT chooses the next target.
        target_voltage_v = self.mppt.step(
            measured_voltage_v=measured_voltage_v,
            measured_power_w=measured_power_w,
        )

        # 3. Apply the target to the PV array.
        self.pv_array.evaluate_at_voltage(target_voltage_v)

        # 4. Fuses process the newly evaluated string currents.
        total_current_a = 0.0

        for string_fuse in self.string_fuses:
            fuse_current_a, _ = string_fuse.step()
            total_current_a += fuse_current_a

        # 5. Aggregate the surviving current.
        self.bus_bar.voltage_v = target_voltage_v
        self.bus_bar.current_a = total_current_a
        
            
                


    
    def get_blown_fuses(self):
        return [string_fuse for string_fuse in self.string_fuses if string_fuse.blown]