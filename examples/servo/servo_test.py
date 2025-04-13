import time
from rpi_plc.core.gpio import PWMOutput
from signal import pause


pwm_output = PWMOutput(
    pin=13,
    label='servo',
    pin_factory=None,
    initial_value=0.0,
    frame_width=20,
    min_pulse_width=1 - 0.37,
    max_pulse_width=2,
    min_value=-60,
    max_value=60
)


for angle in range(-60, 70, 10):
    print(f"angle = {angle}")
    status = pwm_output.read()
    print(status)
    
    pwm_output.write(angle)
    
    status = pwm_output.read()
    print(status)

    time.sleep(1)

    status = pwm_output.read()
    print(status)
    print()


pause()
