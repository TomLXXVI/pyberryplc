"""
GPIO-based stepper motor implementations and speed profiles.
"""

from pyberryplc.stepper.stepper_gpio.base import StepperMotor
from pyberryplc.stepper.stepper_gpio.a4988 import A4988StepperMotor
from pyberryplc.stepper.stepper_gpio.tmc2208 import TMC2208StepperMotor
from pyberryplc.stepper.stepper_gpio.speed_profiles import SpeedProfile, TrapezoidalProfile

__all__ = [
    "StepperMotor",
    "A4988StepperMotor",
    "TMC2208StepperMotor",
    "SpeedProfile",
    "TrapezoidalProfile",
]
