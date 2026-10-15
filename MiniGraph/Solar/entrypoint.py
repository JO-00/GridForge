from DCCombiner.Definition import *
from PVModules.PVArray import PVArray
from PRNG import cloudy, summer




def main():
    pv_array = PVArray()
    dc_combiner = DCCombiner(pv_array)
    time_h, irradiance, cell_temperature = (curve for curve in cloudy.generate_solar_curves(
            cloudiness=1,
            seed=42,
        ))
    
    power , dc_combiner_current , dc_combiner_voltage = [] ,  [], []
    for irradiance_t , cell_temperature_t in zip(irradiance,cell_temperature):   
        for pv_string in pv_array.pv_strings:
            for pv_module in pv_string.pv_modules:
                pv_module.update_conditions(irradiance_t , cell_temperature_t)
            pv_string.step()
        power.append(dc_combiner.bus_bar.voltage_v * dc_combiner.bus_bar.current_a)
        dc_combiner.step()
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
    plt.ylim(280, 350)
    plt.show()
    plt.plot(time_h,dc_combiner_current)
    plt.xlabel("time")
    plt.ylabel("current(t)")
    plt.show()
    plt.plot(time_h , power)
    plt.xlabel("time")
    plt.ylabel("power(t)")
    plt.show()
main()
    


