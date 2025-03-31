import serial
import time

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)

    print("Verbonden met Arduino. Lezen gestart...\nDruk op Ctrl+C om te stoppen.\n")

    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').strip()
            if line.isdigit():
                waarde = int(line)
                print(f"Potentiometer waarde: {waarde}")

except KeyboardInterrupt:
    print("\nGebruiker gestopt.")

except serial.SerialException as e:
    print(f"Seriële fout: {e}")

finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("Seriële poort gesloten.")
