import serial

ser = serial.Serial("/dev/ttyACM0", 9600, timeout=1)

print("Listening to Arduino...")
while True:
    try:
        line = ser.readline().decode().strip()
        if line:
            print("->", line)
    except Exception as e:
        print("Error:", e)
        break
