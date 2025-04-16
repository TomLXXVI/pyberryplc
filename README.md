# rpi-gpio

A modular Python package for developing PLC-like applications on the Raspberry Pi.  
Supports digital I/O, timers, counters, edge detection, and stepper motor control via GPIO or UART.

## 🚀 Features

- PLC-inspired framework with scan-cycle logic
- Support for digital inputs, outputs, PWM
- Built-in timers (TON, TOF) and counters
- Edge-detecting switches (rising/falling/toggle)
- Stepper motor drivers:
  - A4988 (via GPIO)
  - TMC2208 (via GPIO or UART)
- UART configuration support for Trinamic drivers
- Modular structure for extension and testing

## 🧱 Project structure

```
rpi_plc/
├── core/              # PLC core logic: gpio, timers, counters, switches
├── stepper/           # Stepper motor control (GPIO and UART)
│   ├── stepper_gpio/
│   └── stepper_uart/
├── utils/             # Auxiliary tools (e.g. email notifications)
├── remote_interface.py
├── log_utils.py
└── ...
```

## 📦 Installation (for development)

```bash
git clone https://github.com/yourusername/rpi-gpio.git
cd rpi-gpio
pip install -e .
```

Requires Python 3.11 or higher.

## 🧪 Example usage

```python
from rpi_plc.core import AbstractPLC, DigitalInput, DigitalOutput, TimerOnDelay
from rpi_plc.stepper import A4988StepperMotor
```

See the `examples/` folder for test scripts and sample PLC applications.

## ⚙️ Requirements

- `gpiozero`
- `pigpio`
- `pyserial`
- `python-decouple` (for environment configuration)

## 📄 License

This project is licensed under the terms of the MIT license.
