from __future__ import annotations
from typing import TYPE_CHECKING

from .motion_profile import MotionProfile

if TYPE_CHECKING:
    from pyberryplc.stepper import StepperMotor


class DynamicDelayGenerator:

    def __init__(
        self,
        stepper: StepperMotor,
        profile: MotionProfile
    ) -> None:
        self.profile = profile
        self.step_angle = stepper.step_angle

        self.t = 0.0
        self.s = 0.0
        self.step_index = 0

        self.velocity_up_fn = profile.ramp_up_fn()
        self.accel_duration = profile.dt_acc

        self.state = "accel"
        self.cruise_velocity = None
        self.decel_triggered = False
        self.decel_start_velocity = None
        self.velocity_down_fn = None

    def trigger_decel(self):
        self.state = "decel"
        self.decel_triggered = True
        self.decel_start_velocity = self.velocity_up_fn(self.t)
        self.velocity_down_fn = self.profile.ramp_down_fn(self.t, self.decel_start_velocity)

    def next_delay(self) -> float:
        if self.state == "done":
            raise StopIteration
        
        v = 0.0
        if self.state == "accel":
            v = self.velocity_up_fn(self.t)
            if self.t >= self.accel_duration:
                self.state = "cruise"
                self.cruise_velocity = v
        elif self.state == "cruise":
            v = self.cruise_velocity
            if self.decel_triggered:
                self.decel_triggered = False
        elif self.state == "decel":
            v = self.velocity_down_fn(self.t)
            if v <= 0.0:
                self.state = "done"
                raise StopIteration

        delay = abs(self.step_angle / v)
        self.t += delay
        self.s += self.step_angle
        self.step_index += 1

        return delay
