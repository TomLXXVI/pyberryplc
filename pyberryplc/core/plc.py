from abc import ABC, abstractmethod
import sys
import signal
import logging
from dataclasses import dataclass
from gpiozero.pins.pigpio import PiFactory
from pyberryplc.utils import EmailNotification
from .gpio import GPIO, DigitalInput, DigitalOutput, PWMOutput
from .exceptions import ConfigurationError, InternalCommunicationError, EmergencyException


@dataclass
class MemoryVariable:
    """
    Represents a variable with a memory: the variable holds its current state,
    but also remembers its previous state (from the previous PLC scan cycle). 
    This allows for edge detection. 
    
    Attributes
    ----------
    curr_state: bool | int | float
        Current state of the variable, i.e., its state in the current PLC
        scan cycle.
    prev_state: bool | int | float
        Previous state of the variable, i.e., its state in the previous PLC
        scan cycle.
    single_bit: bool
        Indicates that the memory variable should be treated as a single bit 
        variable (its value can be either 0 or 1). Default value is `True`.
    decimal_precision: int
        Sets the decimal precision for floating point values in case the memory
        variable state is represented by a float. The default precision is 3.
    """
    curr_state: bool | int | float = 0
    prev_state: bool | int | float = 0
    single_bit: bool = True
    decimal_precision: int = 3

    def update(self, value: bool | int | float) -> None:
        """Updates the current state of the variable with parameter `value`.
        Before `value` is assigned to the current state of the variable, the
        preceding current state is stored in attribute `prev_state`.
        """
        self.prev_state = self.curr_state
        self.curr_state = value
    
    @property
    def active(self) -> bool:
        """Returns `True` if the current state evaluates to `True`, else returns
        `False`.
        """
        if self.curr_state:
            return True
        return False
    
    def activate(self) -> None:
        """Sets the current state to `True` (1). Only for single bit variables 
        (attribute `is_binary` must be `True`; if `is_binary` is `False`, a
        `ValueError` exception is raised).
        """
        if self.single_bit:
            self.update(1)
        else:
            raise ValueError("Memory variable is not single bit.")

    def deactivate(self) -> None:
        """Sets the current state to `False` (0). Only for single bit variables 
        (attribute `is_binary` must be `True`; if `is_binary` is `False`, a
        `ValueError` exception is raised).
        """
        if self.single_bit:
            self.update(0)
        else:
            raise ValueError("Memory variable is not single bit.")
    
    @property
    def rising_edge(self) -> bool:
        """Returns `True` if `prev_state` is 0 and `curr_state` is 1. Only for 
        single bit variables (attribute `is_binary` must be `True`; if `is_binary` 
        is `False`, a `ValueError` exception is raised).
        """
        if self.single_bit:
            if self.curr_state and not self.prev_state:
                return True
            return False
        else:
            raise ValueError("Memory variable is not single bit.")

    @property
    def falling_edge(self) -> bool:
        """Returns `True` if `prev_state` is 1 and `curr_state` is 0. Only for 
        single bit variables (attribute `is_binary` must be `True`; if `is_binary` 
        is `False`, a `ValueError` exception is raised).
        """
        if self.single_bit:
            if self.prev_state and not self.curr_state:
                return True
            return False
        else:
            raise ValueError("Memory variable is not single bit.")
    
    @property
    def state(self) -> bool | int | float:
        """Returns the current state (value) of the memory variable, i.e. the 
        state (value) in the current PLC scan cycle. If the state is represented
        by a float, it will be rounded to the decimal precision specified when
        the memory variable was instantiated.
        """
        if isinstance(self.curr_state, float):
            return round(self.curr_state, self.decimal_precision)
        else:
            return self.curr_state


class AbstractPLC(ABC):
    """
    Framework class: implements the functionality common to any PLC application 
    running on a Raspberry Pi.

    To write a specific PLC application, the user needs to write its own class
    derived from this base class and implement the abstract methods of this 
    base class.
    """
    def __init__(
        self,
        pin_factory: PiFactory | None = None,
        eml_notification: EmailNotification | None = None
    ) -> None:
        """Creates an `AbstractPLC` instance.

        Parameters
        ----------
        pin_factory:
            Abstraction layer that allows `gpiozero` to interface with the
            hardware-specific GPIO implementation behind the scenes. If `None`,
            the default pin factory is used, which is `PiGPIOFactory`. This
            requires that `pigpio` is installed on the Raspberry Pi, and that
            the `pigpiod` daemon is running in the background.
        eml_notification: optional
            Instance of class `EmailNotification` (see module
            email_notification.py). Allows to send email messages if certain
            events have occurred (e.g. to send an alarm).
        
        Notes
        -----
        The PLC object has an attribute `logger` that can be used to write
        messages to a log file and to the display of the terminal. See also
        `logging.py`.
        """
        self.pin_factory = pin_factory
        
        # Attaches the e-mail notification service (can be None).
        self.eml_notification = eml_notification

        # Attaches a logger to the PLC application (the logger can be configured
        # by calling the function `init_logger()` in module `unipi.logging.py`
        # at the start of the main program).
        self.logger = logging.getLogger("RPI-PLC")

        # Dictionaries that hold the inputs/outputs used by the PLC application.
        self._inputs: dict[str, GPIO] = {}
        self._outputs: dict[str, GPIO] = {}
        
        # Dictionaries where the states of inputs/outputs are stored. These are
        # the memory registries of the PLC. The program logic reads from or 
        # writes to these registries.
        self.input_registry: dict[str, MemoryVariable] = {}
        self.output_registry: dict[str, MemoryVariable] = {}
        self.marker_registry: dict[str, MemoryVariable] = {}
        
        # To terminate program: press Ctrl-Z and method `exit_handler` will be
        # called which terminates the PLC scanning loop.
        signal.signal(signal.SIGTSTP, lambda signum, frame: self.exit_handler())
        self._exit: bool = False

    def add_digital_input(
        self,
        pin: str | int,
        label: str,
        NC_contact: bool | None = False,
    ) -> MemoryVariable:
        """Adds a digital input to the PLC application.

        Parameters
        ----------
        pin:
            GPIO pin the digital input is connected to.
        label:
            Meaningful name for the digital input. This will be the name used
            in the PLC application to access the input.
        NC_contact:
            Indicates if the digital input has a NC-contact. Default is `False`,
            which means by default a NO-contact is assumed.
        
        Returns
        -------
        The memory variable of the digital input in the input memory registry.
        """
        if NC_contact:
            active_state = False
            init_value = 1
        else:
            active_state = True
            init_value = 0
        self._inputs[label] = DigitalInput(
            pin, 
            label, 
            self.pin_factory, 
            pull_up=None, 
            active_state=active_state
        )
        self.input_registry[label] = MemoryVariable(
            curr_state=init_value,
            prev_state=init_value
        )
        return self.input_registry[label]

    def add_digital_output(
        self,
        pin: str | int,
        label: str,
        active_high: bool = True,
        init_value: bool = 0
    ) -> tuple[MemoryVariable, MemoryVariable]:
        """Adds a digital output to the PLC application.
        
        Parameters
        ----------
        pin:
            GPIO pin the digital input is connected to.
        label:
            Meaningful name for the digital input. This will be the name used
            in the PLC application to access the input.
        active_high:
            If `True`, the output will be HIGH (e.g. at 5 V or 3.3 V) when 
            triggered (i.e. when writing 1 to it).
            If `False`, the opposite happens: the output will be LOW (pulled to 
            GND) when the output is triggered.
        init_value:
            Initial value that must be written to the digital output.
        
        Returns
        -------
        The memory variable of the digital output in the output memory registry, 
        and the memory variable of its status in the input memory registry. 
        """
        self._outputs[label] = DigitalOutput(
            pin, 
            label,
            active_high,
            self.pin_factory,
            init_value
        )
        self.output_registry[label] = MemoryVariable(
            curr_state=init_value,
            prev_state=init_value
        )
        self.input_registry[f"{label}_status"] = MemoryVariable()
        return (
            self.output_registry[label], 
            self.input_registry[f"{label}_status"]
        )
    
    def add_pwm_output(
        self,
        pin: str | int,
        label: str,
        init_value: float = 0,
        frame_width: float = 20.0,  # ms
        min_pulse_width: float = 1.0,  # ms
        max_pulse_width: float = 2.0,  # ms
        min_value: float = 0.0,
        max_value: float = 1.0,
        decimal_precision: int = 0
    ) -> tuple[MemoryVariable, MemoryVariable]:
        """Adds a Pulse-Width-Modulation (PWM) output to the PLC application.
        
        Parameters
        ----------
        pin:
            GPIO pin the digital output is connected to.
        label:
            Meaningful name for the digital output. This will be the name used
            in the PLC application to access the output.
        init_value:
            Initial duty cycle that must be written to the output at the 
            start-up of the program. This must be a value between 0.0 and 1.0.
        frame_width:
            Time in milliseconds (ms) between the start of the current pulse and
            the start of the next pulse. The inverse of the frame width 
            determines the frequency of the pulses (i.e. the number of emitted 
            pulses per time unit).
        min_pulse_width:
            Minimum pulse duration in milliseconds (ms).
        max_pulse_width:
            Maximum pulse duration in milliseconds (ms).
        min_value:
            The real-world value that corresponds with `min_pulse_width`.
        max_value:
            The real-world value that corresponds with `max_pulse_width`.
        decimal_precision:
            Number of decimal places the status value is rounded to when read
            from the memory input registry. 
        
        Returns
        -------
        The memory variable of the PWM output in the output memory registry, 
        and the memory variable of its status in the input memory registry.
        """
        self._outputs[label] = PWMOutput(
            pin, label, self.pin_factory, init_value, frame_width, 
            min_pulse_width, max_pulse_width, min_value, max_value
        )
        self.output_registry[label] = MemoryVariable(
            curr_state=init_value,
            prev_state=init_value,
            single_bit=False
        )
        self.input_registry[f"{label}_status"] = MemoryVariable(
            single_bit=False,
            decimal_precision=decimal_precision
        )
        return (
            self.output_registry[label],
            self.input_registry[f"{label}_status"]
        )
    
    def add_marker(self, label: str, init_value: bool | int = 0) -> MemoryVariable:
        """Adds a marker to the marker-registry of the PLC-application and 
        returns its `MemoryVariable` object.
        """
        marker = MemoryVariable(
            curr_state=init_value,
            prev_state=init_value
        )
        self.marker_registry[label] = marker
        return marker

    def di_read(self, label: str) -> bool:
        """Reads the current state of the digital input specified by the given
        label.

        Raises a `ConfigurationError` exception if the digital input with the
        given label has not been added to the PLC-application before.

        Returns the read value (integer). If the digital input has been
        configured as normally closed, the inverted value is returned.
        """
        di = self._inputs.get(label)
        if di:
            value = di.read()
            return value
        else:
            raise ConfigurationError(f"unknown digital input `{label}`")

    def do_write(self, label: str, value: bool) -> None:
        """Writes the given value (bool) to the digital output with the given
        label.

        Raises a `ConfigurationError` exception if the digital output with the
        given label has not been added to the PLC-application before.
        """
        do = self._outputs.get(label)
        if do:
            do.write(value)
        else:
            raise ConfigurationError(f"unknown digital output `{label}`")
    
    def pwm_write(self, label: str, value: float) -> None:
        """Writes the given value (float) to the PWM output with the given 
        label.
        
        Raises a `ConfigurationError` exception if the PWM output with the
        given label has not been added to the PLC-application before.
        """
        pwm_output = self._outputs.get(label)
        if pwm_output:
            pwm_output.write(value)
        else:
            raise ConfigurationError(f"unknown PWM output `{label}`")
    
    def read_inputs(self) -> None:
        """Reads all the physical inputs defined in the PLC application 
        and writes their current states in their respective input registries.

        Raises an `InternalCommunicationError` exception when a read operation
        fails.
        """
        try:
            for input_ in self._inputs.values():
                self.input_registry[input_.label].update(input_.read())
            for output in self._outputs.values():
                self.input_registry[f"{output.label}_status"].update(output.read())
        except InternalCommunicationError as error:
            self.int_com_error_handler(error)

    def write_outputs(self) -> None:
        """Writes all the current states in the output registries to their 
        corresponding physical outputs.

        Raises an `InternalCommunicationError` exception when a write operation
        fails.
        """
        try:
            for output in self._outputs.values():
                output.write(self.output_registry[output.label].curr_state)
        except InternalCommunicationError as error:
            self.int_com_error_handler(error)
    
    def update_registries(self):
        """At the beginning of each new scan cycle the values in the 
        current state location of the memory variables and output variables are
        moved to the previous state location. This allows for edge detection.
        """
        for marker in self.marker_registry.values():
            marker.update(marker.curr_state)
        for output in self.output_registry.values():
            output.update(output.curr_state)
    
    def int_com_error_handler(self, error: InternalCommunicationError):
        """Handles an `InternalCommunication` exception. An error message is
        sent to the logger. If the email notification service is used, an email
        is sent with the error message. Finally, the PLC application is
        terminated.
        """
        msg = f"program interrupted: {error.description}"
        self.logger.error(msg)
        if self.eml_notification: self.eml_notification.send(msg)
        sys.exit(msg)

    def exit_handler(self):
        """Terminates the PLC scanning loop when the user has pressed the key
        combination <Ctrl-Z> on the keyboard of the PLC (Raspberry Pi) to stop
        the PLC application.
        """
        self._exit = True

    @abstractmethod
    def control_routine(self):
        """Implements the running operation of the PLC-application.

        Must be overridden in the PLC application class derived from this class.
        """
        ...

    @abstractmethod
    def exit_routine(self):
        """Implements the routine that is called when the PLC-application is
        to be stopped, i.e. when the user has pressed the key combination
        <Ctrl-Z> on the keyboard of the PLC (Raspberry Pi).

        Must be overridden in the PLC application class derived from this class.
        """
        ...

    @abstractmethod
    def emergency_routine(self):
        """Implements the routine for when an `EmergencyException` has been 
        raised. An `EmergencyException` can be raised anywhere within the
        `control_routine` method to signal an emergency situation for which the
        PLC application must be terminated.

        Must be overridden in the PLC application class derived from this class.
        """
        ...

    @abstractmethod
    def crash_routine(self, exception: Exception | KeyboardInterrupt) -> None:
        """Handles unexpected runtime exceptions."""
        pass

    def run(self):
        """Implements the global running operation of the PLC."""
        try:
            while not self._exit:
                try:
                    self.update_registries()
                    self.read_inputs()
                    self.control_routine()
                except EmergencyException:
                    self.logger.warning("Emergency stop triggered.")
                    self.emergency_routine()
                    return
                finally:
                    self.write_outputs()
            else:
                self.exit_routine()
                self.write_outputs()
        except KeyboardInterrupt as e:
            self.logger.warning(
                "KeyboardInterrupt received — invoking crash routine."
            )
            self.crash_routine(e)
        except Exception as e:
            self.logger.exception(
                "Unexpected exception occurred — invoking crash routine."
            )
            self.crash_routine(e)
