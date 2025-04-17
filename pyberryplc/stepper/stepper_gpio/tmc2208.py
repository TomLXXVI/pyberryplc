import logging
import time
from pyberryplc.core.gpio import DigitalOutput
from pyberryplc.stepper.stepper_gpio import StepperMotor
from pyberryplc.stepper.stepper_uart import TMC2208UART


class TMC2208StepperMotor(StepperMotor):
    """
    Stepper motor controlled via a TMC2208 driver and GPIO/UART.
    Supports basic microstepping configuration via MS1 and MS2 pins.
    """

    def __init__(
        self,
        step_pin: int,
        dir_pin: int,
        enable_pin: int | None = None,
        ms1_pin: int | None = None,
        ms2_pin: int | None = None,
        steps_per_revolution: int = 200,
        uart: TMC2208UART | None = None,
        logger: logging.Logger | None = None,
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
        steps_per_revolution : int, optional
            Number of full steps per motor revolution. Default is 200.
        uart: TMC2208UART | None, optional
            UART-interface for register-based configuration.
        logger : logging.Logger | None, optional
            Logger instance for debug/info output.
        """
        super().__init__(step_pin, dir_pin, enable_pin, steps_per_revolution, logger)
        self.ms1 = DigitalOutput(ms1_pin, label="MS1") if ms1_pin is not None else None
        self.ms2 = DigitalOutput(ms2_pin, label="MS2") if ms2_pin is not None else None
        self.uart = uart
    
    def enable(self) -> None:
        if self.uart is not None:
            self.uart.open()
            self.uart.update_register(
                reg_name="GCONF", 
                fields={
                    "pdn_disable": True,
                    "mstep_reg_select": True
                }
            )
            time.sleep(0.005)
            self.uart.update_register(
                reg_name="CHOPCONF", 
                fields={"toff": 3}
            )
            self.logger.info("Driver enabled")
        else:
            super().enable()
    
    def disable(self) -> None:
        if self.uart is not None:
            self.uart.update_register(
                reg_name="CHOPCONF", 
                fields={"toff": 0}
            )
            self.uart.close()
            self.logger.info("Driver disabled")
        else:
            super().disable()
    
    def set_microstepping(self, mode: str) -> None:
        """
        Configure microstepping mode.

        Parameters
        ----------
        mode : str
            One of: "full", "1/2", "1/4", "1/8", "1/16", "1/32", "1/64",
            "1/128", "1/256".
        """
        if self.uart is not None:
            self._set_microstepping_uart(mode)
        else:
            self._set_microstepping_gpio(mode)

    def _set_microstepping_gpio(self, mode: str) -> None:
        """
        Configure microstepping mode.

        Parameters
        ----------
        mode : str
            One of: "1/2", "1/4", "1/8", "1/16"
        """
        config: dict[str, tuple[int, int]] = {
            "1/2": (1, 0),
            "1/4": (0, 1),
            "1/8": (0, 0),
            "1/16": (1, 1),
        }
        if mode not in config:
            raise ValueError(f"Invalid microstepping mode: {mode}")

        if self.ms1 and self.ms2:
            ms1_val, ms2_val = config[mode]
            self.ms1.write(ms1_val)
            self.ms2.write(ms2_val)
            self.microstep_mode = mode
            self.logger.info(
                f"Microstepping set to {mode} (MS1={ms1_val}, MS2={ms2_val})"
            )
        else:
            self.logger.warning(
                f"MS1/MS2 pins not configured, skipping microstepping setup"
            )

    def _set_microstepping_uart(self, mode: str) -> None:
        config: dict[str, int] = {
            "1/256": 0,
            "1/128": 1,
            "1/64": 2,
            "1/32": 3,
            "1/16": 4,
            "1/8": 5,
            "1/4": 6,
            "1/2": 7,
            "full": 8
        }
        if mode not in config:
            raise ValueError(f"Invalid microstepping mode: {mode}")
        mres = config[mode]
        self.uart.update_register(
            reg_name="CHOPCONF", 
            fields={"mres": mres}
        )
        self.microstep_mode = mode
        self.logger.info(
            f"Setting microstepping via UART: {mode} (mres = {mres})"
        )
