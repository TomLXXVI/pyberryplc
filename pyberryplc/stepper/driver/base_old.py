import time
import logging
from abc import ABC, abstractmethod
from collections import deque

import numpy as np

from pyberryplc.core.gpio import DigitalOutput
from pyberryplc.motion_profiles import MotionProfile


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
        microstep_resolution: str = "full",
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
        full_steps_per_rev : int, optional
            Number of full steps per revolution (i.e. at full step mode).
            Default is 200. However, this is a characteristic of the actual
            stepper motor.
        microstep_resolution : str, optional
            The microstep resolution to be used. Default is full-step mode.
            Valid microstep resolutions are defined in class attribute 
            MICROSTEP_FACTORS. However, it is possible that the actual driver
            does not support all of these. This should be checked in advance. 
        logger : logging.Logger | None, optional
            Logger for debug output.
        """
        self.step = DigitalOutput(step_pin, label="STEP", active_high=True)
        self.dir = DigitalOutput(dir_pin, label="DIR", active_high=True)
        self._enable = (
            DigitalOutput(enable_pin, label="EN", active_high=False) 
            if enable_pin is not None 
            else None
        )
        self.full_steps_per_rev = full_steps_per_rev
        res = self._validate_microstepping(microstep_resolution)
        self.microstep_resolution = res[0]
        self.microstep_factor = res[1]
        self.logger = logger or logging.getLogger(__name__)
        self.step_width = 10e-6  # time duration (sec) of single step pulse
        
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
    def _validate_microstepping(self, microstep_resolution: str) -> tuple[str, int]:
        """
        Check whether the microstep resolution is valid for the driver. 
        
        Returns
        -------
        microstep_resolution : str
            The microstep resolution if valid.
        microstep_factor: int
            The microstep factor used for calculating the steps per degree and 
            the step angle.
        
        Raises
        ------
        ValueError :
            If the microstep resolution is unavailable on the driver.
        """
        pass

    @property
    def steps_per_degree(self) -> float:
        """Return the number of steps per degree of rotation."""
        return self.full_steps_per_rev * self.microstep_factor / 360
    
    @property
    def step_angle(self) -> float:
        """Return the rotation angle in degrees that corresponds with a single 
        step pulse.
        """
        return 1 / self.steps_per_degree
    
    @abstractmethod
    def set_microstepping(self) -> None:
        """
        Configure microstepping on the driver.
        """
        pass

    def start_rotation(
        self,
        angle: float | None = None,
        angular_speed: float = 90.0,
        profile: MotionProfile | None = None,
        direction: str = "forward",
    ) -> None:
        """
        Start a new rotation asynchronously (non-blocking).
        
        Either specify the rotation angle in degrees together with a fixed
        angular speed in deg/sec or use a motion profile to determine the
        rotational movement the motor must execute.
        
        Use this method together with method `do_single_step()`.

        Parameters
        ----------
        angle : float, optional
            Target rotation angle in degrees.
        angular_speed : float, optional
            Constant angular speed (deg/s) if no profile is given.
        profile : MotionProfile, optional
            Motion profile for the rotational movement.
            If provided, it overrides the default fixed-speed behavior and 
            enables acceleration and deceleration during the motion.
        direction : str, optional
            Either "forward" or "backward". Default is "forward".
        """
        if self.busy:
            self.logger.warning("Motor is busy — rotation ignored.")
            return
        self._set_direction(direction)
        self._delays = self._process_motion_profile(profile, angle, angular_speed)
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
                self._next_step_time = now + self._delays.popleft()
            if not self._delays:
                self._busy = False
    
    def rotate(
        self,
        angle: float | None = None,
        angular_speed: float = 90.0,
        profile: MotionProfile | None = None,
        direction: str = "forward",
    ) -> None:
        """
        Either rotate the motor a specified number of degrees at a given constant
        angular speed (in deg/sec), or pass a motion profile to rotate the motor.
        
        Note that is a blocking function: the method won't return until the
        rotation is completely finished.

        Parameters
        ----------
        angle : float
            The rotation angle in degrees.
        angular_speed : float, optional
            Constant angular speed in degrees per second (used if no profile is 
            given). Default is 90.0.
        profile : StepDelayGenerator, optional
            Motion profile of the rotational movement.
            If provided, it overrides the default fixed-speed behavior and 
            enables acceleration and deceleration during the motion.  
        direction : str, optional
            Either "forward" or "backward". Default is "forward".
        """
        if self.busy:
            self.logger.warning("Motor is busy — rotation ignored.")
            return
        self._set_direction(direction)
        
        self._delays = self._process_motion_profile(profile, angle, angular_speed)
   
        for delay in self._delays:
            self.step.write(True)
            time.sleep(delay / 2)
            self.step.write(False)
            time.sleep(delay / 2)
    
    def _process_motion_profile(
        self, 
        profile: MotionProfile | None,
        angle: float | None,
        angular_speed: float | None
    ) -> deque[float]:
        """Processes the motion profile. Calculates the delays between 
        successive step pulses and returns them in a deque.
        
        Either `profile` must be given a `MotionProfile` object, or `angle` and 
        `angular_speed` must be specified. If `profile` is `None`, the motor 
        will be rotated `angle` degrees at fixed `angular_speed` (deg/s).
        """
        if profile:
            start_angle = 0.0
            final_angle = profile.ds_tot + self.step_angle
            angles = np.arange(start_angle, final_angle, self.step_angle)
            times = list(map(profile.time_from_position_fn(), angles))
            delays = np.diff(times) - self.step_width
            return deque(delays)
        else:
            steps_per_degree = self.steps_per_degree
            total_steps = int(angle * steps_per_degree)
            step_rate = angular_speed * steps_per_degree  # in steps/sec
            delay = 1.0 / step_rate
            delays = [delay] * total_steps
            return deque(delays)
    
    def _pulse_step_pin(self) -> None:
        """Generate a short pulse on the STEP pin (10 microseconds)."""
        self.step.write(True)
        time.sleep(self.step_width)  # default 10 µs pulse
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
