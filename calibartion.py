from machine import Pin, ADC
import time
import json

# ACS712 output connected safely to ESP32 GPIO34
current_adc = ADC(Pin(34))
current_adc.atten(ADC.ATTN_11DB)

CONFIG_FILE = "calibration.json"

# Nominal sensitivity for ACS712-5A.
# This assumes no voltage-divider scaling.
# If you use a divider, adjust this value.
SENSITIVITY = 0.185  # V/A

def read_voltage():
    total = 0.0
    samples = 100

    for _ in range(samples):
        # read_uv() is supported by many ESP32
        # MicroPython builds.
        voltage = current_adc.read_uv() / 1000000
        total += voltage
        time.sleep_ms(10)

    return total / samples


def read_current(zero_voltage):
    voltage = read_voltage()
    current = abs(voltage - zero_voltage) / SENSITIVITY
    return current


def calibrate():
    print("Motor OFF. Keep current through sensor at zero.")
    time.sleep(3)

    zero_voltage = read_voltage()
    print("Zero-current output:", round(zero_voltage, 3), "V")

    input("Press Enter after starting motor normally...")

    print("Measuring normal running current...")
    total_current = 0.0
    samples = 0
    start = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), start) < 10000:
        current = read_current(zero_voltage)
        total_current += current
        samples += 1
        print("Estimated current:", round(current, 3), "A")

    if samples == 0:
        print("No readings collected.")
        return

    normal_current = total_current / samples
    overcurrent_limit = normal_current * 1.3

    config = {
        "zero_voltage": zero_voltage,
        "normal_current_estimate": normal_current,
        "overcurrent_limit_estimate": overcurrent_limit,
        "sensitivity_V_per_A": SENSITIVITY,
        "verified_with_reference_meter": False
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)
        

    print("\nCalibration procedure completed.")
    print("Normal current estimate:",
          round(normal_current, 3), "A")
    print("Provisional threshold:",
          round(overcurrent_limit, 3), "A")
    


calibrate()