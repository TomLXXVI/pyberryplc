import serial


def trinamic_crc(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b
    return crc


uart = serial.Serial(
    port="/dev/ttyAMA0",
    baudrate=115200,
    timeout=0.5
)


# GCONF read command
tx = bytes([0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
crc = trinamic_crc(tx)
packet = tx + bytes([crc])

print("Transmit packet: ", packet.hex())

uart.write(packet)
uart.flush()

response = uart.read(8)
print("Response packet: ", response.hex())

if len(response) == 8 and response[0] == 0x05:
    data = response[4] | (response[5] << 8) | (response[6] << 16)
    check = trinamic_crc(response[:7])
    if check == response[7]:
        print(f"GCONF-register value: 0x{data:06X}")
    else:
        print("Checksum error in response!")
else:
    print("Received invalid response.")
