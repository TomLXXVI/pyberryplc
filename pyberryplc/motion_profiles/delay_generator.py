from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np

from .motion_profile import MotionProfile

if TYPE_CHECKING:
    from pyberryplc.stepper import StepperMotor


class StepDelayGenerator:
    """
    Class that takes a stepper motor and a motion profile. From the motion 
    profile a list of step pulse delays is determined to drive the stepper motor
    according to this motion profile.
    
    The list of delays is accessible through attribute `delays`.
    """
    
    def __init__(
        self,
        stepper: StepperMotor,
        profile: MotionProfile,
    ) -> None:
        self.stepper = stepper
        self.profile = profile
        self.delays: list[float] = self._generate_delays()
        self._index = 0
    
    def _generate_delays(self) -> list[float]:
        start_angle = 0.0
        final_angle = self.profile.ds_tot + self.stepper.step_angle
        angles = np.arange(start_angle, final_angle, self.stepper.step_angle)
        times = list(map(self.profile.time_from_position_fn(), angles))
        delays = np.diff(times) - self.stepper.step_width
        return delays.tolist()
