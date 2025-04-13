import serial
import time

# Maak verbinding met de hardware UART
uart = serial.Serial(
    port="/dev/ttyAMA0",
    baudrate=115200,       # standaard voor TMC2208
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1              # seconden wachten op reactie
)

# Even wachten om zeker te zijn dat de driver wakker is
time.sleep(0.1)

# Dummy-byte sturen (alleen om communicatie te testen)
uart.write(b'\x05')  # bijvoorbeeld 0x05
uart.flush()

print("Testbyte verzonden.")
