from DCCombiner.Definition import *
from PVModules.PVArray import PVArray
from PRNG import cloudy, summer
from Inverter.Definition import SolarInverter
from Sensors.sensor import Sensor , SensorConfig




def main():
    pv_array = PVArray()
    dc_combiner = DCCombiner(pv_array)
    inverter = SolarInverter()
    time_h, irradiance, cell_temperature = cloudy.generate_solar_curves(
            cloudiness=1,
            seed=42,
        )
    corrupt_config = SensorConfig(
            noise_std=18.0,
            bias=12.0,
            drift_per_step=0.02,
            stuck_probability=0.0,
            spike_probability=0.012,
            dropout_probability=0.0,
            spike_magnitude=100.0,
        )
    corrupt = Sensor("1", "2" , "a" ,"b",corrupt_config)

    
    power , dc_combiner_current , dc_combiner_voltage, ac_power = [] ,  [], [] , []
    for irradiance_t , cell_temperature_t in zip(irradiance,cell_temperature):   
        for pv_string in pv_array.pv_strings:
            for pv_module in pv_string.pv_modules:
                pv_module.update_conditions(irradiance_t , cell_temperature_t)
            pv_string.step()
        power.append(dc_combiner.bus_bar.voltage_v * dc_combiner.bus_bar.current_a)
        dc_combiner.step()
        dc_combiner_current.append(dc_combiner.bus_bar.current_a)
        dc_combiner_voltage.append(dc_combiner.bus_bar.voltage_v)
        inverter.step(dc_combiner.bus_bar.voltage_v , dc_combiner.bus_bar.current_a)
        ac_power.append(inverter.ac_power_w)
    with open("dataset.csv","r")
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
    plt.show()
    plt.plot(time_h,dc_combiner_current)
    plt.xlabel("time")
    plt.ylabel("current(t)")
    plt.show()
    plt.plot(time_h , power)
    plt.xlabel("time")
    plt.ylabel("power(t)")
    plt.show()
    plt.plot(time_h , ac_power)
    plt.xlabel("time")
    plt.ylabel("AC power(t)")
    plt.show()

    
main()
    


