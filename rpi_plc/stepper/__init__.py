"""
Top-level package for stepper motor control using GPIO or UART.
Provides access to all stepper motor classes and configuration tools.
"""

from rpi_plc.stepper.stepper_gpio.base import StepperMotor
from rpi_plc.stepper.stepper_gpio.a4988 import A4988StepperMotor
from rpi_plc.stepper.stepper_gpio.tmc2208 import TMC2208StepperMotor
from rpi_plc.stepper.stepper_gpio.speed_profiles import SpeedProfile, TrapezoidalProfile
from rpi_plc.stepper.stepper_uart.tmc2208_uart import TMC2208UART

__all__ = [
    "StepperMotor",
    "A4988StepperMotor",
    "TMC2208StepperMotor",
    "SpeedProfile",
    "TrapezoidalProfile",
    "TMC2208UART",
]
