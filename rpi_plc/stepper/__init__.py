"""
Unified interface for stepper motor control using GPIO or UART.

- GPIO drivers are available via: stepper.stepper_gpio
- UART tools are available via: stepper.stepper_uart
"""

from .stepper_gpio.base import StepperMotor
from .stepper_gpio.a4988 import A4988StepperMotor
from .stepper_gpio.tmc2208 import TMC2208StepperMotor
from .stepper_gpio.speed_profiles import SpeedProfile, TrapezoidalProfile

from .stepper_uart.tmc2208_uart import TMC2208UART

__all__ = [
    "StepperMotor",
    "A4988StepperMotor",
    "TMC2208StepperMotor",
    "SpeedProfile",
    "TrapezoidalProfile",
    "TMC2208UART",
]
