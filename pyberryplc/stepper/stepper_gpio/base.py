import time
import logging
from abc import ABC, abstractmethod
from collections import deque

import numpy as np

from pyberryplc.core.gpio import DigitalOutput
from pyberryplc.motion_profiles import MotionProfile, Quantity

Q_ = Quantity


class StepperMotor(ABC):
    """
    Abstract base class for a stepper motor controlled via GPIO, with 
    non-blocking or blocking motion control.

    This class provides the foundation for implementing stepper motor drivers
    that execute rotations asynchronously using periodic do_single_step calls.
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
        full_steps_per_rev: int = 200,
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
        full_steps_per_rev : int
            Number of full steps per revolution (i.e. at full step mode).
        logger : logging.Logger | None, optional
            Logger for debug output.
        """
        self.step = DigitalOutput(step_pin, label="STEP", active_high=True)
        self.dir = DigitalOutput(dir_pin, label="DIR", active_high=True)
        self._enable = DigitalOutput(enable_pin, label="EN", active_high=False) if enable_pin is not None else None
        self.full_steps_per_rev = full_steps_per_rev
        self.logger = logger or logging.getLogger(__name__)
        self.microstep_mode: str = "full"
        self._step_width = Q_(10, 'µs')  # time duration of single step pulse

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
        degrees: float | None,
        angular_speed: float = 90.0,
        profile: MotionProfile | None = None,
        direction: str = "forward",
    ) -> None:
        """
        Start a new rotation asynchronously (non-blocking).
        
        Use this method together with method `do_single_step()`.

        Parameters
        ----------
        degrees : float, optional
            Target rotation angle in degrees.
        angular_speed : float, optional
            Constant angular speed (deg/s) if no profile is given.
        profile : MotionProfile | None, optional
            Speed profile to define step delays.
        direction : str, optional
            Either "forward" or "backward". Default is "forward".
        """
        if self.busy:
            self.logger.warning("Motor is busy — rotation ignored.")
            return
        self._set_direction(direction)
        self._delays = self._get_delays(degrees, angular_speed, profile)
        self._next_step_time = time.time()
        self._busy = True

    def do_single_step(self) -> None:
        """
        Perform a single step if the time is right.
        
        Before calling this method, call method `start_rotation()` first to
        define the complete rotation movement.
        
        Should be called regularly within the PLC scan cycle.
        """
        if not self._busy: return
        now = time.time()
        if now >= self._next_step_time and self._delays:
            self._pulse_step_pin()
            if self._delays:
                self._next_step_time = now + 2 * self._delays.popleft()
            if not self._delays:
                self._busy = False
    
    def rotate(
        self,
        degrees: float,
        angular_speed: float = 90.0,
        profile: MotionProfile | None = None,
        direction: str = "forward",
    ) -> None:
        """
        Rotate the motor a specified number of degrees.
        
        Note that is a blocking function: the method won't return until the
        rotation is completely finished.

        Parameters
        ----------
        degrees : float
            The rotation angle in degrees.
        angular_speed : float, optional
            Constant angular speed in degrees per second (used if no profile is 
            given). Default is 90.0.
        profile : MotionProfile, optional
            Speed profile that defines the delay between step pulses.  
            If provided, it overrides the default fixed-speed behavior and 
            enables acceleration and deceleration during the motion.
        direction : str, optional
            Either "forward" or "backward". Default is "forward".
        """
        if self.busy:
            self.logger.warning("Motor is busy — rotation ignored.")
            return
        self._set_direction(direction)
        self._delays = self._get_delays(degrees, angular_speed, profile)
        total_steps = len(self._delays)

        self.logger.info(
            f"Rotating {direction}: {total_steps} steps over {degrees:.1f}° at "
            f"{'profiled speed' if profile else f'{angular_speed:.1f}°/s'}"
        )
   
        for delay in self._delays:
            self.step.write(True)
            time.sleep(delay)
            self.step.write(False)
            time.sleep(delay)
    
    def _get_delays(
        self, 
        degrees: float, 
        angular_speed: float | None, 
        profile: MotionProfile | None
    ) -> deque[float]:
        """Get the delays between successive steps in a deque."""
        steps_per_degree = self.full_steps_per_rev * self._microstep_factor() / 360
        if profile:
            step_angle = 1 / steps_per_degree
            start_angle = 0.0
            final_angle = profile.ds_tot.to('deg').m + step_angle
            angles = Q_(np.arange(start_angle, final_angle, step_angle), 'deg')
            times = Quantity.from_list(list(map(profile.time_from_position_fn(), angles)))
            delays = np.diff(times) - self._step_width
            delays = delays.to('s').m.tolist()
            return deque(delays)
        else:
            total_steps = int(degrees * steps_per_degree)
            step_rate = angular_speed * steps_per_degree  # in steps/sec
            delay = 1.0 / step_rate / 2  # seconds per 1/2 step
            delays = [delay] * total_steps
            return deque(delays)
    
    def _pulse_step_pin(self) -> None:
        """Generate a short pulse on the STEP pin (10 microseconds)."""
        self.step.write(True)
        time.sleep(self._step_width.to('s').m)  # default 10 µs pulse
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
