import serial
from typing import Optional


class TMC2208UART:
    """
    UART communication helper for Trinamic TMC2208 driver.

    Supports register-level read and write access using the Trinamic UART protocol.

    This class is a context manager, ensuring the serial port is safely closed
    after use, even when exceptions occur.

    Parameters
    ----------
    port : str
        Serial port name (e.g., '/dev/ttyAMA0').
    baudrate : int, optional
        Baudrate for UART communication (default is 115200).
    timeout : float, optional
        Timeout in seconds for UART reads (default is 0.5).
    slave_address : int, optional
        Address of the TMC2208 slave device (default is 0x00).
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 0.5,
        slave_address: int = 0x00
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.slave_address = slave_address
        self.serial: Optional[serial.Serial] = None

    def open(self) -> None:
        """
        Opens the serial port if it is not already open.
        """
        if not self.serial or not self.serial.is_open:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )

    def close(self) -> None:
        """
        Closes the serial port if it is open.
        """
        if self.serial and self.serial.is_open:
            self.serial.close()

    def __enter__(self) -> "TMC2208UART":
        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.serial and self.serial.is_open:
            self.serial.close()
    
    @staticmethod
    def _calculate_crc(data: list[int]) -> int:
        crc = 0
        for byte in data:
            for _ in range(8):
                if (crc >> 7) ^ (byte & 0x01):
                    crc = ((crc << 1) ^ 0x07) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
                byte >>= 1
        return crc

    def read_register(self, register: int) -> int:
        """
        Sends a read request for the specified register and returns its value.

        Parameters
        ----------
        register : int
            Address of the register to read.

        Returns
        -------
        int
            32-bit register value.

        Raises
        ------
        IOError
            If communication fails or an invalid response is received.
        """
        if not self.serial or not self.serial.is_open:
            raise IOError("Serial port is not open.")

        request = [0x05, self.slave_address, register & 0x7F]
        request.append(self._calculate_crc(request))

        self.serial.write(bytes(request))
        self.serial.flush()

        response = self.serial.read(12)
        if len(response) < 12:
            raise IOError("Incomplete response received from driver.")

        response = response[4:]  # Skip echo (first 4 bytes)

        if response[0] != 0x05:
            raise IOError(f"Invalid sync byte in response: 0x{response[0]:02X}")

        if response[1] != 0xFF:
            raise IOError(f"Invalid master address: 0x{response[1]:02X}")

        if response[2] != (register & 0x7F):
            raise IOError(f"Unexpected register address in response: 0x{response[2]:02X}")

        if self._calculate_crc(list(response[:7])) != response[7]:
            raise IOError("CRC check failed for received response.")

        value = (
            (response[3] << 24) |
            (response[4] << 16) |
            (response[5] << 8) |
            response[6]
        )
        return value

    def write_register(self, register: int, value: int) -> None:
        """
        Writes a 32-bit value to the specified register.

        Parameters
        ----------
        register : int
            Address of the register to write.
        value : int
            32-bit value to write into the register.

        Raises
        ------
        IOError
            If the serial port is not open.
        """
        if not self.serial or not self.serial.is_open:
            raise IOError("Serial port is not open.")

        datagram = [
            0x05,                    # Sync
            self.slave_address,      # Slave address
            register | 0x80,         # Write bit (MSB set)
            (value >> 24) & 0xFF,    # Data byte 1 (MSB)
            (value >> 16) & 0xFF,    # Data byte 2
            (value >> 8) & 0xFF,     # Data byte 3
            value & 0xFF             # Data byte 4 (LSB)
        ]
        crc = self._calculate_crc(datagram)
        datagram.append(crc)

        self.serial.write(bytes(datagram))
        self.serial.flush()

    def update_register_bits(self, register: int, mask: int, value: int) -> None:
        """
        Updates selected bits in a register using a read–modify–write operation.
    
        Parameters
        ----------
        register : int
            Address of the register to update.
        mask : int
            Bitmask that defines which bits should be updated (1 = modify).
        value : int
            New bit values to apply (only bits under the mask are used).
    
        Raises
        ------
        IOError
            If reading or writing the register fails.
        """
        current = self.read_register(register)
        new_value = (current & ~mask) | (value & mask)
        self.write_register(register, new_value)
