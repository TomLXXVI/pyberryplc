from time import sleep
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import Device, Servo


Device.pin_factory = PiGPIOFactory()


correction_max = 0.0
correction_min = -0.37

max_pulse_width = (2 + correction_max) / 1000
min_pulse_width = (1 + correction_min) / 1000

frame_width = 20 / 1000


servo = Servo(
    pin=27,
    min_pulse_width=min_pulse_width,
    max_pulse_width=max_pulse_width,
    frame_width=frame_width
)


def duty_cycle(
    value: float, 
    max_pw: float = max_pulse_width, 
    min_pw: float = min_pulse_width, 
    fw: float = frame_width
) -> float:
    """Returns the duty cycle that corresponds with `value`.
    
    Parameters
    ----------
    value:
        Position value between -1 (minimum position) and 1 (maximum position).
    max_pw:
        Maximum pulse width, i.e. the pulse duration that corresponds with the
        maximum position value (1).
    min_pw:
        Minimum pulse width, i.e. the pulse duration that corresponds with the
        minimum position value (-1).
    fw:
        Frame width, i.e. the time between the start of the current pulse and
        the start of the next pulse.
    
    Returns
    -------
    Duty cycle in percent.
    """
    min_value = -1
    value_range = 2
    min_dc = min_pw / fw
    dc_range = (max_pw - min_pw) / fw
    dc = min_dc + (value - min_value) * (dc_range / value_range)
    return dc * 100


def cycle():
    """Runs a movement cycle from minimum position to middle position to maximum 
    position.
    """
    servo.min()
    dc = duty_cycle(servo.value, max_pulse_width, min_pulse_width, frame_width)
    print(f"duty cycle min = {dc} %")
    sleep(2)

    servo.mid()
    dc = duty_cycle(servo.value, max_pulse_width, min_pulse_width, frame_width)
    print(f"duty cycle mid = {dc} %")
    sleep(2)

    servo.max()
    dc = duty_cycle(servo.value, max_pulse_width, min_pulse_width, frame_width)
    print(f"duty cycle max = {dc} %")
    sleep(2)

servo.min()
while True:
    val = input("enter position value between -1 and 1: ")
    val = float(val)
    servo.value = val
