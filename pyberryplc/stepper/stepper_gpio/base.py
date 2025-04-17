import time
import logging
from abc import ABC, abstractmethod
from collections import deque
from pyberryplc.core.gpio import DigitalOutput
from .speed_profiles import SpeedProfile


class StepperMotor(ABC):
    """
    Abstract base class for a stepper motor controlled via GPIO, with 
    non-blocking motion control.

    This class provides the foundation for implementing stepper motor drivers
    that execute rotations asynchronously using periodic update calls.
    """

    MICROSTEP_FACTORS: dict[str, int] = {
        "full": 1,
        "1/2": 2,
        "1/4": 4,
        "1/8": 8,
        "1/16": 16,
        "1/32": 32,
        "1/64": 64,
        "1/128": 128,
        "1/256": 256
    }

    def __init__(
        self,
        step_pin: int,
        dir_pin: int,
        enable_pin: int | None = None,
        steps_per_revolution: int = 200,
        logger: logging.Logger | None = None
    ) -> None:
        """
        Initialize the StepperMotor instance.

        Parameters
        ----------
        step_pin : int
            GPIO pin connected to the STEP input of the driver.
        dir_pin : int
            GPIO pin connected to the DIR input of the driver.
        enable_pin : int | None, optional
            GPIO pin connected to the EN input of the driver (active low).
        steps_per_revolution : int
            Number of full steps per revolution.
        logger : logging.Logger | None, optional
            Logger for debug output.
        """
        self.step = DigitalOutput(step_pin, label="STEP", active_high=True)
        self.dir = DigitalOutput(dir_pin, label="DIR", active_high=True)
        self._enable = DigitalOutput(enable_pin, label="EN", active_high=False) if enable_pin is not None else None
        self.steps_per_revolution = steps_per_revolution
        self.logger = logger or logging.getLogger(__name__)
        self.microstep_mode: str = "full"

        # State for non-blocking motion control
        self._busy = False
        self._next_step_time = 0.0
        self._delays = deque()

    def enable(self) -> None:
        """Enable the stepper driver (if EN pin is defined)."""
        if self._enable:
            self._enable.write(True)
            self.logger.debug("Driver enabled")

    def disable(self) -> None:
        """Disable the stepper driver (if EN pin is defined)."""
        if self._enable:
            self._enable.write(False)
            self.logger.debug("Driver disabled")

    @property
    def busy(self) -> bool:
        """Return whether the motor is currently executing a motion."""
        return self._busy

    @abstractmethod
    def set_microstepping(self, mode: str) -> None:
        """
        Set the microstepping mode.

        Parameters
        ----------
        mode : str
            Microstepping mode (e.g., "full", "1/8", "1/16", etc.)
        """
        pass

    def start_rotation(
        self,
        degrees: float,
        direction: str = "forward",
        angular_speed: float = 90.0,
        profile: SpeedProfile | None = None
    ) -> None:
        """
        Start a new rotation asynchronously.

        Parameters
        ----------
        degrees : float
            Target rotation angle in degrees.
        direction : str, optional
            Either "forward" or "backward". Default is "forward".
        angular_speed : float, optional
            Constant angular speed (deg/s) if no profile is given.
        profile : SpeedProfile | None, optional
            Speed profile to define step delays.
        """
        if self.busy:
            self.logger.warning("Motor is busy — rotation ignored.")
            return

        self._set_direction(direction)
        total_steps = int((degrees / 360.0) * self.steps_per_revolution * self._microstep_factor())

        if profile:
            delays = profile.get_delays(degrees)
            if len(delays) != total_steps:
                raise ValueError("Mismatch between number of steps and number of delays")
            self._delays = deque(delays)
        else:
            step_delay = 1.0 / (angular_speed * self._microstep_factor() / 360.0)
            self._delays = deque([step_delay] * total_steps)

        self._next_step_time = time.time()
        self._busy = True

    def update(self) -> None:
        """
        Perform a single step if the time is right.
        Should be called regularly within the PLC scan cycle.
        """
        if not self._busy:
            return

        now = time.time()
        if now >= self._next_step_time and self._delays:
            self._pulse_step_pin()
            if self._delays:
                self._next_step_time = now + self._delays.popleft()
            if not self._delays:
                self._busy = False

    def _pulse_step_pin(self) -> None:
        """Generate a short pulse on the STEP pin (10 microseconds)."""
        self.step.write(True)
        time.sleep(0.00001)  # 10 µs pulse
        self.step.write(False)

    def _set_direction(self, direction: str) -> None:
        """
        Set motor direction.

        Parameters
        ----------
        direction : str
            Either "forward" or "backward"
        """
        if direction not in ("forward", "backward"):
            raise ValueError("Direction must be 'forward' or 'backward'")
        self.dir.write(direction == "forward")

    def _microstep_factor(self) -> int:
        """Return the integer microstepping factor based on current mode."""
        return self.MICROSTEP_FACTORS.get(self.microstep_mode, 1)
