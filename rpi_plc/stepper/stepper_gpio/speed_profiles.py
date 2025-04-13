from abc import ABC, abstractmethod
from typing import List


class SpeedProfile(ABC):
    """
    Abstract base class for a stepper motor speed profile.
    A profile defines the delay (in seconds) between step pulses
    for a given rotation in degrees.
    """

    def __init__(self) -> None:
        self.steps_per_degree: float = 1.0

    def set_conversion_factor(self, steps_per_degree: float) -> None:
        """
        Set the conversion factor from degrees to steps.

        Parameters
        ----------
        steps_per_degree : float
            Number of microsteps per degree.
        """
        self.steps_per_degree = steps_per_degree

    @abstractmethod
    def get_delays(self, total_degrees: float) -> List[float]:
        """
        Compute a list of delays per step for a rotation of given degrees.

        Parameters
        ----------
        total_degrees : float
            Total rotation angle in degrees.

        Returns
        -------
        list of float
            Delay times between step pulses (in seconds).
        """
        pass


class TrapezoidalProfile(SpeedProfile):
    """
    Trapezoidal speed profile with linear acceleration, constant speed,
    and linear deceleration phases.
    All speeds and ramp lengths are expressed in degrees.
    """

    def __init__(
        self,
        min_angular_speed: float = 30.0,
        max_angular_speed: float = 180.0,
        accel_angle: float = 20.0,
        decel_angle: float = 20.0
    ) -> None:
        """
        Initialize the trapezoidal profile.

        Parameters
        ----------
        min_angular_speed : float
            Starting and ending angular speed in degrees per second.
        max_angular_speed : float
            Maximum angular speed reached during constant phase (deg/sec).
        accel_angle : float
            Number of degrees used for acceleration.
        decel_angle : float
            Number of degrees used for deceleration.
        """
        super().__init__()
        self.min_angular_speed = min_angular_speed
        self.max_angular_speed = max_angular_speed
        self.accel_angle = accel_angle
        self.decel_angle = decel_angle

    def get_delays(self, total_degrees: float) -> List[float]:
        delays: List[float] = []

        accel_steps = int(self.accel_angle * self.steps_per_degree)
        decel_steps = int(self.decel_angle * self.steps_per_degree)
        total_steps = int(total_degrees * self.steps_per_degree)
        flat_steps = max(0, total_steps - accel_steps - decel_steps)

        # Acceleration phase
        for i in range(accel_steps):
            ang_speed = (
                self.min_angular_speed 
                + (self.max_angular_speed - self.min_angular_speed) 
                * (i / accel_steps)
            )
            delay = 1.0 / (ang_speed * self.steps_per_degree) / 2
            delays.append(delay)

        # Constant speed phase
        if flat_steps > 0:
            delay = 1.0 / (self.max_angular_speed * self.steps_per_degree) / 2
            delays.extend([delay] * flat_steps)

        # Deceleration phase
        for i in range(decel_steps):
            ang_speed = (
                self.max_angular_speed 
                - (self.max_angular_speed - self.min_angular_speed) 
                * (i / decel_steps)
            )
            delay = 1.0 / (ang_speed * self.steps_per_degree) / 2
            delays.append(delay)

        # Trim or pad to match exact step count
        if len(delays) > total_steps:
            delays = delays[:total_steps]
        elif len(delays) < total_steps:
            fallback_delay = 1.0 / (self.min_angular_speed * self.steps_per_degree) / 2
            delays.extend([fallback_delay] * (total_steps - len(delays)))

        return delays
