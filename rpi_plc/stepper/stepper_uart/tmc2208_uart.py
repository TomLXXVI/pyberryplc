import serial
from typing import Optional


class TMC2208UART:
    """
    UART communication helper class for the Trinamic TMC2208 stepper driver.
    Supports reading and writing 24-bit registers using the Trinamic protocol.
    """

    def __init__(
        self,
        port: str = "/dev/ttyAMA0",
        baudrate: int = 115200,
        timeout: float = 0.5
    ) -> None:
        """
        Initialize the serial connection with the TMC2208.

        Parameters
        ----------
        port : str
            Serial port connected to the PDN_UART line.
        baudrate : int
            Baudrate for UART communication (default: 115200).
        timeout : float
            Timeout for reading a response (in seconds).
        """
        self.serial = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout
        )
    
    @staticmethod
    def _crc(data: bytes) -> int:
        crc = 0
        for b in data:
            crc ^= b
        return crc

    def read_register(self, reg_addr: int) -> Optional[int]:
        """
        Read a 24-bit register value from the TMC2208.

        Parameters
        ----------
        reg_addr : int
            Address of the register to read.

        Returns
        -------
        Optional[int]
            The 24-bit register value, or None if read failed.
        """
        tx = bytes([0x05, 0x00, reg_addr & 0xFF, 0x00, 0x00, 0x00, 0x00])
        crc = self._crc(tx)
        packet = tx + bytes([crc])

        self.serial.reset_input_buffer()
        self.serial.write(packet)
        self.serial.flush()

        response = self.serial.read(8)
        if len(response) == 8 and response[0] == 0x05:
            check = self._crc(response[:7])
            if check == response[7]:
                return response[4] | (response[5] << 8) | (response[6] << 16)
        return None

    def write_register(self, reg_addr: int, value: int) -> None:
        """
        Write a 24-bit value to a TMC2208 register.

        Parameters
        ----------
        reg_addr : int
            Address of the register to write.
        value : int
            24-bit value to write.
        """
        data = [
            0x05,        # Sync
            0x00,        # Slave address
            reg_addr & 0xFF,
            0x80,        # Write bit (bit 7 = 1)
            value & 0xFF,
            (value >> 8) & 0xFF,
            (value >> 16) & 0xFF
        ]
        crc = self._crc(bytes(data))
        packet = bytes(data + [crc])

        self.serial.write(packet)
        self.serial.flush()

    def close(self) -> None:
        """
        Close the serial connection.
        """
        self.serial.close()
