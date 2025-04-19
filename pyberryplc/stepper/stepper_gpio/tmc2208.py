import logging
import time
from pyberryplc.core.gpio import DigitalOutput
from pyberryplc.stepper.stepper_gpio import StepperMotor
from pyberryplc.stepper.stepper_uart import TMC2208UART
from pyberryplc.stepper.stepper_uart.tmc2208_registers import IHOLDIRUNRegister


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
        full_steps_per_rev: int = 200,
        uart: TMC2208UART | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(step_pin, dir_pin, enable_pin, full_steps_per_rev, logger)
        self.ms1 = DigitalOutput(ms1_pin, label="MS1") if ms1_pin is not None else None
        self.ms2 = DigitalOutput(ms2_pin, label="MS2") if ms2_pin is not None else None
        self.uart = uart

    def enable(self) -> None:
        """
        Enables the stepper driver.

        If UART is configured, this method opens the UART connection and
        configures the driver to accept software microstepping settings
        and activate current output. Otherwise, it falls back to GPIO-based
        enabling.
        """
        if self.uart is not None:
            self.uart.open()
            self.uart.update_register(
                "GCONF", 
                {"pdn_disable": True, "mstep_reg_select": True}
            )
            time.sleep(0.005)
            self.uart.update_register(
                "CHOPCONF", 
                {"toff": 3}
            )
            self.logger.info("Driver enabled")
        else:
            super().enable()

    def disable(self) -> None:
        """
        Disables the stepper driver.

        If UART is configured, this method turns off the driver's current
        output (via CHOPCONF) and closes the UART connection. Otherwise,
        it disables the driver through the GPIO enable pin.
        """
        if self.uart is not None:
            self.uart.update_register(
                "CHOPCONF", 
                {"toff": 0}
            )
            self.uart.close()
            self.logger.info("Driver disabled")
        else:
            super().disable()

    def set_microstepping(self, mode: str) -> None:
        """
        Sets the microstepping mode for the driver.

        If a UART interface is configured, this sets the resolution using the 
        internal CHOPCONF register. Otherwise, it configures the MS1/MS2 GPIO 
        pins to achieve the desired stepping resolution.

        Parameters
        ----------
        mode : str
            Desired microstepping mode. Supported values are:
            - UART: "1/256", "1/128", "1/64", "1/32", "1/16", "1/8", "1/4", "1/2", "full"
            - GPIO: "1/2", "1/4", "1/8", "1/16"

        Raises
        ------
        ValueError
            If the given mode is not supported.
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
                "MS1/MS2 pins not configured, skipping microstepping setup"
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
        self.uart.update_register("CHOPCONF", {"mres": mres})
        self.microstep_mode = mode
        self.logger.info(f"Setting microstepping via UART: {mode} (mres = {mres})")

    def set_current_via_uart(
        self,
        run_current_pct: float,
        hold_current_pct: float,
        ihold_delay: int = 8
    ) -> None:
        """
        Set motor current digitally via UART using percentages.

        Parameters
        ----------
        run_current_pct : float
            Run current as a percentage (0–100).
        hold_current_pct : float
            Hold current as a percentage (0–100).
        ihold_delay : int
            Delay before switching to hold current (0–15).
        """
        if self.uart is None:
            raise RuntimeError(
                "UART interface not available on this stepper motor."
            )

        assert 0 <= run_current_pct <= 100
        assert 0 <= hold_current_pct <= 100
        assert 0 <= ihold_delay <= 15

        irun = round(run_current_pct / 100 * 31)
        ihold = round(hold_current_pct / 100 * 31)

        if 0 < irun <= 1:
            irun = 1
        if 0 < ihold <= 1:
            ihold = 1

        self.uart.update_register("GCONF", {"i_scale_analog": False})
        self.uart.write_register("IHOLD_IRUN", IHOLDIRUNRegister(
            ihold=ihold,
            irun=irun,
            ihold_delay=ihold_delay
        ))
        self.logger.info(
            f"UART current config set: IRUN={irun}/31, IHOLD={ihold}/31, DELAY={ihold_delay}"
        )
