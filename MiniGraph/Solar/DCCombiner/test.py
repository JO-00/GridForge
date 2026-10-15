from DCCombiner.Definition import *
from PVModules.PVArray import PVArray
from PVModules.Definition import pv_module
from PRNG import cloudy, summer




def main():
    pv_array = PVArray()
    dc_combiner = DCCombiner(pv_array)
    time_h, irradiance, cell_temperature = (curve for curve in cloudy.generate_solar_curves(
            cloudiness=1,
            seed=42,
        ))
    
    power , dc_combiner_current , dc_combiner_voltage = [] ,  [], []
    for irradiance_t, cell_temperature_t in zip(irradiance, cell_temperature):
        for pv_string in pv_array.pv_strings:
            for pv_module in pv_string.pv_modules:
                pv_module.update_conditions(
                    irradiance_t,
                    cell_temperature_t,
                )

        dc_combiner.step()

        power.append(
            dc_combiner.bus_bar.voltage_v
            * dc_combiner.bus_bar.current_a
        )
        dc_combiner_current.append(dc_combiner.bus_bar.current_a)
        dc_combiner_voltage.append(dc_combiner.bus_bar.voltage_v)
    import matplotlib.pyplot as plt
    plt.plot(time_h , irradiance)
    plt.xlabel("time")
    plt.ylabel("irradiance(t)")
    plt.show()
    plt.plot(time_h,cell_temperature)
    plt.xlabel("time")
    plt.ylabel("cell temp(t)")
    plt.show()
    plt.plot(time_h,dc_combiner_voltage)
    plt.xlabel("time")
    plt.ylabel("dc voltage(t)")
    plt.ylim(200, 500)
    plt.show()
    plt.plot(dc_combiner_voltage,power)
    plt.xlabel("voltage")
    plt.ylabel("power(t)")
    plt.show()

    plt.plot(time_h,dc_combiner_current)
    plt.xlabel("time")
    plt.ylabel("current(t)")
    plt.show()
    plt.plot(time_h , power)
    plt.xlabel("time")
    plt.ylabel("power(t)")
    plt.show()

def main1():
    
    pv_array = PVArray()
    for voltage_v in [250, 275, 290, 299.5, 300.0, 300.5, 301.0, 325, 350,400,500,600]:
        current_a = pv_array.power_at_voltage(voltage_v) / voltage_v
        power_w = voltage_v * current_a
        print(f"{voltage_v:6.1f} V | {current_a:8.3f} A | {power_w:10.2f} W")
def test_module_iv():
    with open("Config/PVModuleConfig.json", "r") as f:
        module_config = pv_module.PVModuleConfig.from_dict(json.load(f))
    module = pv_module.PVModule("test_module", module_config)

    module.update_conditions(
        irradiance_w_m2=module.config.diode.ref_irradiance,
        cell_temperature_c=module.config.diode.T_ref,
    )

    for voltage_v in [0.0, 40.0, 45.0, 48.6, 50.0, 55.0, 59.12, 60.0]:
        current_a = module.current_at_voltage(voltage_v)
        power_w = voltage_v * current_a
        print(
            f"{voltage_v:6.2f} V | "
            f"{current_a:10.6f} A | "
            f"{power_w:10.3f} W"
        )
        
main()    


