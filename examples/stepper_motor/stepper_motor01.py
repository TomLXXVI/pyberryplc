from gpiozero import DigitalOutputDevice
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

factory = PiGPIOFactory()

step = DigitalOutputDevice(27, pin_factory=factory)
direction = DigitalOutputDevice(26, pin_factory=factory)
# ms1 = DigitalOutputDevice(13, pin_factory=factory)
# ms2 = DigitalOutputDevice(21, pin_factory=factory)

direction.on()

steps = 400           
delay = 0.002

# ms1.on()
# ms2.off()

print("Motor start...")
for i in range(steps):
    step.on()
    sleep(delay)
    step.off()
    sleep(delay)

print("Finished!")
