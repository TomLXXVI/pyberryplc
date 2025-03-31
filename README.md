# python-rpi-gpio

A modular Python package that enables programmable PLC-style control on a 
Raspberry Pi using GPIO pins. Ideal for building small automation systems, 
testing I/O logic, or integrating with remote devices such as Arduino.

---

## Features

- PLC-style control structure (scan cycle, memory variables)
- Digital input and output abstraction
- PWM output with configurable pulse timing
- Serial and TCP communication with external devices
- Seamless integration with `gpiozero` and `pigpio` under the hood

---

## Installation

Make sure you're using Python 3.10 or higher. This package is intended for use 
**only on Raspberry Pi OS**.

```bash
# Clone the repository
$ git clone https://github.com/TomLXXVI/python-rpi-gpio.git
$ cd python-rpi-gpio

# (Optional) Create a virtual environment
$ python -m venv .venv
$ source .venv/bin/activate  # Raspberry Pi/Linux only

# Install dependencies
> pip install .
```

---

## Hardware Compatibility

- Works exclusively on Raspberry Pi with GPIO support
- Supports external devices like:
  - Arduino (via USB serial)
  - Other TCP/UDP remote devices

You can integrate any hardware that communicates via digital I/O, PWM, or 
JSON over serial/TCP.

---

## License

This project is licensed under the MIT License. See `LICENSE.md` for details.
