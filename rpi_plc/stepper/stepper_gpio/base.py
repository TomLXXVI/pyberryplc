import time
import logging
from abc import ABC, abstractmethod
from rpi_plc.core.gpio import DigitalOutput
from .speed_profiles import SpeedProfile


class StepperMotor(ABC):
    """
    Abstract base class for a stepper motor controlled via GPIO.
    """

    MICROSTEP_FACTORS: dict[str, int] = {
        "full": 1,
        "1/2": 2,
        "1/4": 4,
        "1/8": 8,
        "1/16": 16,
    }

    def __init__(
        self,
        steps_per_revolution: int = 200,
        logger: logging.Logger | None = None
    ) -> None:
        """
        Initialize the abstract StepperMotor.

        Parameters
        ----------
        steps_per_revolution : int, optional
            Number of full steps per motor revolution. Default is 200.
        logger : logging.Logger | None, optional
            Logger instance for debug/info output.
        """
        self.steps_per_revolution = steps_per_revolution
        self.step: DigitalOutput | None = None
        self.dir: DigitalOutput | None = None
        self.enable: DigitalOutput | None = None
        self.microstep_mode: str = "full"
        self.logger = logger or logging.getLogger(__name__)

    @abstractmethod
    def set_microstepping(self, mode: str) -> None:
        pass

    def rotate(
        self,
        degrees: float,
        direction: str = "forward",
        angular_speed: float = 90.0,
        profile: SpeedProfile | None = None
    ) -> None:
        """
        Rotate the motor a specified number of degrees.

        Parameters
        ----------
        degrees : float
            The rotation angle in degrees.
        direction : str, optional
            Either "forward" or "backward". Default is "forward".
        angular_speed : float, optional
            Constant angular speed in degrees per second (used if no profile is 
            given). Default is 90.0.
        profile : SpeedProfile, optional
            Speed profile that defines the delay between step pulses.  
            If provided, it overrides the default fixed-speed behavior and 
            enables acceleration and deceleration during the motion. 
        """
        factor = self.MICROSTEP_FACTORS.get(self.microstep_mode, 1)
        steps_per_degree = self.steps_per_revolution * factor / 360
        steps = int(degrees * steps_per_degree)
        step_rate = angular_speed * steps_per_degree  # in steps/sec
        
        self.dir.write(direction == "forward")

        if profile:
            profile.set_conversion_factor(steps_per_degree)
            delays = profile.get_delays(degrees)
        else:
            # constant speed = constant delay
            delay = 1.0 / step_rate / 2
            delays = [delay] * steps

        self.logger.info(
            f"[{self.__class__.__name__}] Rotating {direction}: {steps} steps "
            f"over {degrees:.1f}° at "
            f"{'profiled speed' if profile else f'{angular_speed:.1f}°/s'}"
        )

        for delay in delays:
            self.step.write(True)
            time.sleep(delay)
            self.step.write(False)
            time.sleep(delay)

    def disable(self) -> None:
        """Disable the stepper driver (if enable pin is configured)."""
        if self.enable:
            self.enable.write(False)
            self.logger.info(f"[{self.__class__.__name__}] Driver disabled")
