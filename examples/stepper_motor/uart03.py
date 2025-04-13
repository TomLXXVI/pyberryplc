from rpi_plc.stepper import TMC2208UART


driver = TMC2208UART(port="/dev/ttyAMA0")

gconf = driver.read_register(0x00)

if gconf is not None:
    print(f"GCONF = 0x{gconf:06X}")
else:
    print("Failed to read GCONF")

driver.close()
