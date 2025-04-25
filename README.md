# pyberryplc

pyberryplc is a modular PLC framework written in Python for the Raspberry Pi 
platform. It enables real-time control of GPIO- and UART-driven components such 
as stepper motors.

The project is designed to make the Raspberry Pi function as a fully 
programmable logic controller (PLC), with support for structured sequential 
logic (SFC), motion profiles, and field I/O — implemented entirely in Python.

## Features

- Structured PLC execution based on a scan-cycle model
- Support for stepper motor drivers including A4988 and TMC2208
- Position-based dynamic motion profiling using trapezoidal and S-curved trajectories
- SFC-style logic control using step markers and explicit transitions
- UART integration for runtime configuration of drivers (e.g. TMC2208)
- Example test programs with GPIO or keyboard-based control

## Getting Started

### Requirements

- Raspberry Pi (any recent model)
- Python 3.9 or later
- GPIO and serial communication libraries: `gpiozero`, `pigpio`, `pyserial`, ...
- A stepper driver board such as the A4988 or TMC2208

### Installation

```bash
git clone https://github.com/TomLXXVI/pyberryplc.git
cd pyberryplc
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running a test script

```bash
python examples/stepper_motor/stepper_motor06.py
```

## Project Structure

```
pyberryplc/
├── core/              # PLC base classes, markers, and scan control
├── motion_profiles/   # Motion profile definitions and dynamic delay logic
├── stepper/           # Stepper driver abstractions and implementations
├── utils/             # Logging, keyboard input, and common helpers
└── examples/          # Sample PLC programs for testing and demonstration
```

## Background and Motivation

This project is aimed at developers and control engineers looking for a 
software-only alternative to ladder logic or proprietary PLC platforms.

It leverages the flexibility of Python and the I/O capabilities of Raspberry Pi 
to implement motion control applications with deterministic step sequencing.

## Documentation

Basic usage examples are included in the `examples/` directory. 
Full documentation will be added in a later phase.

## Author

TomLXXVI  
Control systems developer and Raspberry Pi integrator

## License

MIT License
