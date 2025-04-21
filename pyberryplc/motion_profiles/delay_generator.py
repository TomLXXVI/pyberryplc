from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np

from .motion_profile import MotionProfile, Quantity

if TYPE_CHECKING:
    from pyberryplc.stepper import StepperMotor


Q_ = Quantity


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
        step_angle = self.stepper.step_angle
        step_width = Q_(self.stepper.step_width, 's')
        
        start_angle = 0.0
        final_angle = self.profile.ds_tot.to('deg').m + step_angle
        
        angles = Q_(np.arange(start_angle, final_angle, step_angle), 'deg')
        times = Quantity.from_list(list(map(self.profile.time_from_position_fn(), angles)))
        delays = np.diff(times) - step_width
        delays = delays.to('s').m.tolist()
        return delays
    