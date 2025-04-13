import logging
from rpi_plc.core.gpio import DigitalOutput
from rpi_plc.stepper.stepper_gpio.base import StepperMotor


class TMC2208StepperMotor(StepperMotor):
    """
    Stepper motor controlled via a TMC2208 driver and GPIO.
    Supports basic microstepping configuration via MS1 and MS2 pins.
    """

    def __init__(
        self,
        step_pin: int,
        dir_pin: int,
        enable_pin: int | None = None,
        ms1_pin: int | None = None,
        ms2_pin: int | None = None,
        microstep_mode: str = "1/8",
        steps_per_revolution: int = 200,
        logger: logging.Logger | None = None
    ) -> None:
        """
        Initialize a TMC2208 stepper motor driver instance.

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
        microstep_mode : str, optional
            Microstepping mode: "1/2", "1/4", "1/8", or "1/16". Default is "1/8".
        steps_per_revolution : int, optional
            Number of full steps per motor revolution. Default is 200.
        logger : logging.Logger | None, optional
            Logger instance for debug/info output.
        """
        super().__init__(steps_per_revolution, logger)
        self.step = DigitalOutput(step_pin, label="STEP", active_high=True)
        self.dir = DigitalOutput(dir_pin, label="DIR", active_high=True)
        self.enable = DigitalOutput(enable_pin, label="EN", active_high=False) if enable_pin is not None else None

        self.ms1 = DigitalOutput(ms1_pin, label="MS1") if ms1_pin is not None else None
        self.ms2 = DigitalOutput(ms2_pin, label="MS2") if ms2_pin is not None else None

        if self.enable:
            self.enable.write(True)  # LOW (active)
        
        self.microstep_mode = microstep_mode
        self.set_microstepping(microstep_mode)

    def set_microstepping(self, mode: str) -> None:
        """
        Configure microstepping mode.

        Parameters
        ----------
        mode : str
            One of: "1/2", "1/4", "1/8", "1/16"
        """
        config: dict[str, tuple[int, int]] = {
            "1/2":  (1, 0),
            "1/4":  (0, 1),
            "1/8":  (0, 0),
            "1/16": (1, 1),
        }
        if mode not in config:
            raise ValueError(f"Invalid microstepping mode: {mode}")

        if self.ms1 and self.ms2:
            ms1_val, ms2_val = config[mode]
            self.ms1.write(ms1_val)
            self.ms2.write(ms2_val)
            self.logger.info(
                f"[{self.__class__.__name__}] "
                f"Microstepping set to {mode} (MS1={ms1_val}, MS2={ms2_val})"
            )
        else:
            self.logger.warning(
                f"[{self.__class__.__name__}] "
                f"MS1/MS2 pins not configured, skipping microstepping setup"
            )
