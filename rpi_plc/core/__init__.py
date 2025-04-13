"""
Core components for building a Python-based PLC.

This module exposes base classes and utilities for digital I/O, timers,
counters, switches, and the main PLC execution engine.
"""

from rpi_plc.core.plc import AbstractPLC, MemoryVariable
from rpi_plc.core.gpio import DigitalInput, DigitalOutput, PWMOutput
from rpi_plc.core.timers import TimerSingleScan, TimerOnDelay, TimerOffDelay
from rpi_plc.core.counters import CounterUp, CounterDown, CounterUpDown
from rpi_plc.core.switches import ToggleSwitch
from rpi_plc.core.exceptions import InternalCommunicationError, ConfigurationError, EmergencyException

__all__ = [
    "AbstractPLC",
    "MemoryVariable",
    "DigitalInput",
    "DigitalOutput",
    "PWMOutput",
    "TimerSingleScan",
    "TimerOnDelay",
    "TimerOffDelay",
    "CounterUp",
    "CounterDown",
    "CounterUpDown",
    "ToggleSwitch",
    "InternalCommunicationError",
    "ConfigurationError",
    "EmergencyException"
]
