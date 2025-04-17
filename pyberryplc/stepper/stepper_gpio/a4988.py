import logging
from pyberryplc.core.gpio import DigitalOutput
from pyberryplc.stepper.stepper_gpio.base import StepperMotor


class A4988StepperMotor(StepperMotor):
    """
    Stepper motor controlled via an A4988 driver and GPIO.
    Supports microstepping configuration via MS1, MS2, and MS3 pins.
    """

    def __init__(
        self,
        step_pin: int,
        dir_pin: int,
        enable_pin: int | None = None,
        ms1_pin: int | None = None,
        ms2_pin: int | None = None,
        ms3_pin: int | None = None,
        steps_per_revolution: int = 200,
        logger: logging.Logger | None = None
    ) -> None:
        """
        Initialize an A4988 stepper motor driver instance.

        Parameters
        ----------
        step_pin : int
            GPIO pin connected to the STEP input of the driver.
        dir_pin : int
            GPIO pin connected to the DIR input of the driver.
        enable_pin : int | None, optional
            GPIO pin connected to the EN input of the driver (active low).
        ms1_pin : int | None, optional
            GPIO pin connected to MS1 for microstepping control.
        ms2_pin : int | None, optional
            GPIO pin connected to MS2 for microstepping control.
        ms3_pin : int | None, optional
            GPIO pin connected to MS3 for microstepping control.
        steps_per_revolution : int, optional
            Number of full steps per motor revolution. Default is 200.
        logger : logging.Logger | None, optional
            Logger instance for debug/info output.
        """
        super().__init__(step_pin, dir_pin, enable_pin, steps_per_revolution, logger)
        self.ms1 = DigitalOutput(ms1_pin, label="MS1") if ms1_pin is not None else None
        self.ms2 = DigitalOutput(ms2_pin, label="MS2") if ms2_pin is not None else None
        self.ms3 = DigitalOutput(ms3_pin, label="MS3") if ms3_pin is not None else None
    
    def set_microstepping(self, mode: str) -> None:
        """
        Configure microstepping mode.

        Parameters
        ----------
        mode : str
            One of: "full", "1/2", "1/4", "1/8", "1/16"
        """
        config: dict[str, tuple[int, int, int]] = {
            "full":  (0, 0, 0),
            "1/2":   (1, 0, 0),
            "1/4":   (0, 1, 0),
            "1/8":   (1, 1, 0),
            "1/16":  (1, 1, 1),
        }
        if mode not in config:
            raise ValueError(f"Invalid microstepping mode: {mode}")

        if self.ms1 and self.ms2 and self.ms3:
            ms1_val, ms2_val, ms3_val = config[mode]
            self.ms1.write(ms1_val)
            self.ms2.write(ms2_val)
            self.ms3.write(ms3_val)
            self.logger.info(
                f"[{self.__class__.__name__}] "
                f"Microstepping set to {mode} "
                f"(MS1={ms1_val}, MS2={ms2_val}, MS3={ms3_val})"
            )
            self.microstep_mode = mode
        else:
            self.logger.warning(
                f"[{self.__class__.__name__}] "
                f"MS1/MS2/MS3 pins not configured, skipping microstepping setup"
            )
