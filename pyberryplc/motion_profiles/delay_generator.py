from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np

from .motion_profile import MotionProfile

if TYPE_CHECKING:
    from pyberryplc.stepper import StepperMotor


class StepDelayGenerator:
    
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
