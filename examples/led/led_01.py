from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import Device, Button, LED
from signal import pause

Device.pin_factory = PiGPIOFactory()

led = LED(27)
button = Button(4, pull_up=False)

button.when_pressed = led.on
button.when_released = led.off

pause()
