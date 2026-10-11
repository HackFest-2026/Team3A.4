
from machine import Pin, ADC
from time import sleep
import json

# ---------------- SENSOR PINS ----------------
current_sensor = ADC(Pin(34))
voltage_sensor = ADC(Pin(35))

current_sensor.atten(ADC.ATTN_11DB)
voltage_sensor.atten(ADC.ATTN_11DB)

current_sensor.width(ADC.WIDTH_12BIT)
voltage_sensor.width(ADC.WIDTH_12BIT)

# ---------------- OUTPUT PINS ----------------
relay = Pin(21, Pin.OUT)
green_led = Pin(18, Pin.OUT)
red_led = Pin(19, Pin.OUT)
buzzer = Pin(23, Pin.OUT)

# Check whether your relay is active LOW
RELAY_ON = 0
RELAY_OFF = 1

# ---------------- ACS712 SETTINGS ----------------
# 5A module: 0.185 V/A
# 20A module: 0.100 V/A
# 30A module: 0.066 V/A
SENSITIVITY = 0.066

# IMPORTANT:
# Set this to the actual ACS712 output voltage at zero current.
# Measure it with the motor OFF.
ZERO_SENSOR_VOLTAGE = 2.50

# For a divider with 10k from OUT to GPIO34
# and 20k from GPIO34 to GND, this is 1.5.
# Change it if your wiring is diffmoerent.
DIVIDER_FACTOR = 1.5

# ---------------- START SAFE ----------------
relay.value(RELAY_OFF)
green_led.value(0)
red_led.value(0)
buzzer.value(0)

# ---------------- LOAD MOTOR DATA ----------------
try:
    with open("motors.json", "r") as file:
        motors = json.load(file)

    print("Available motors:")
    for motor_name in motors:
        print("-", motor_name)

    selected_motor = input(
        "Type motor name and press Enter: "
    ).strip().lower()

    while selected_motor not in motors:
        print("Motor name not found.")
        print("Available motors:", list(motors.keys()))

        selected_motor = input(
            "Type motor name again: "
        ).strip().lower()

    normal_current = motors[selected_motor]["normal_current"]
    OVER_CURRENT_LIMIT = motors[selected_motor]["over_current_limit"]

    print("Selected motor:", selected_motor)
    print("Normal current:", normal_current, "A")
    print("Overcurrent limit:", OVER_CURRENT_LIMIT, "A")

except Exception as error:
    print("ERROR: motors.json cannot be loaded")
    print(error)

    selected_motor = "none"
    normal_current = 0
    OVER_CURRENT_LIMIT = 0

# ---------------- CURRENT READING ----------------
def read_current():
    total_raw = 0
    samples = 100

    for _ in range(samples):
        total_raw += current_sensor.read()
        sleep(0.005)

    # Average ADC reading
    adc_raw = total_raw / samples

    # ESP32 ADC pin voltage (approximate)
    adc_voltage = (adc_raw / 4095) * 3.3

    # Estimate ACS712 output before the divider
    sensor_voltage = adc_voltage * DIVIDER_FACTOR

    # Calculate current
    current_amp = abs(
        sensor_voltage - ZERO_SENSOR_VOLTAGE
    ) / SENSITIVITY

    return current_amp, adc_raw, sensor_voltage

# ---------------- MAIN PROGRAM ----------------
print("GridGuardian AI started")

while True:
    try:
        current_amp, current_raw, sensor_voltage = read_current()
        voltage_raw = voltage_sensor.read()

        print("Motor:", selected_motor)
        print("Current ADC raw:", round(current_raw, 1))
        print("Estimated sensor voltage:",
              round(sensor_voltage, 3), "V")
        print("Current:", round(current_amp, 3), "A")
        print("Current limit:", OVER_CURRENT_LIMIT, "A")
        print("Voltage sensor ADC:", voltage_raw)

        # ---------------- FAULT CHECK ----------------
        if (
            selected_motor == "none"
            or OVER_CURRENT_LIMIT <= 0
        ):
            relay.value(RELAY_OFF)
            green_led.value(0)
            red_led.value(1)
            buzzer.value(1)

            print("FAULT: Motor profile unavailable")
            print("Motor command: OFF")

        elif current_amp > OVER_CURRENT_LIMIT:
            relay.value(RELAY_OFF)
            green_led.value(0)
            red_led.value(1)
            buzzer.value(1)

            print("FAULT: OVERCURRENT DETECTED")
            print("Motor command: OFF")

        else:
            relay.value(RELAY_ON)
            green_led.value(1)
            red_led.value(0)
            buzzer.value(0)

            print("Status: NORMAL")
            print("Motor command: ON")

        print("----------------------------")
        sleep(1)

    except Exception as error:
        # Fail-safe software response
        relay.value(RELAY_OFF)
        green_led.value(0)
        red_led.value(1)
        buzzer.value(1)

        print("ERROR:", error)
        print("Motor command: OFF")
        sleep(1)

