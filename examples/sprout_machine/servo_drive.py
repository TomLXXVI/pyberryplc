import os
import socket
import json
import threading
import time
import logging
from datetime import datetime

from pyberryplc.core.gpio import PWMOutput, DigitalOutput

log_dir = "/shared/python-projects/rpi-gpio/applications/sprout_machine/logs"
os.makedirs(log_dir, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d")
logfile_path = os.path.join(log_dir, f"servo_drive_{timestamp}.log")

logging.basicConfig(
    filename=logfile_path,
    level=logging.INFO,
    format="[%(name)s %(asctime)s | %(levelname)s] %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S",
    filemode='a'
)


SERVO_GPIO = 13
LED_GPIO = 26

servo = PWMOutput(
    SERVO_GPIO,
    label='servo',
    frame_width=20,
    min_pulse_width=1 - 0.37,
    max_pulse_width=2,
    min_value=-60,
    max_value=60
)
status_led = DigitalOutput(
    LED_GPIO, 
    label='lamp',
    initial_value=0
)

HOST = '0.0.0.0'
PORT = 65432

conn_to_master = None
movement_in_progress = False


def notify_master(message_dict):
    if conn_to_master:
        try:
            conn_to_master.sendall((json.dumps(message_dict) + "\n").encode())
        except:
            logging.error("Failed to send message to master.")


def move_servo():
    global movement_in_progress
    status_led.write(1)
    movement_in_progress = True

    for angle in range(-60, 120, 60):
        servo.write(angle)
        time.sleep(1)

    movement_in_progress = False
    status_led.write(0)
    notify_master({"status": "done", "message": "Movement complete"})


def handle_command(command):
    global movement_in_progress
    if command == "move":
        if movement_in_progress:
            return {"status": "busy", "message": "Already moving"}
        threading.Thread(target=move_servo, daemon=True).start()
        return {"status": "started", "message": "Movement started"}
    elif command == "shutdown":
        return {"status": "ok", "message": "Shutting down"}
    else:
        return {"status": "error", "message": "Unknown command"}


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    logging.info(f"Slave listening on {HOST}:{PORT}...")

    conn, addr = s.accept()
    with conn:
        conn_to_master = conn
        logging.info(f"Connected to master: {addr}")
        while True:
            data = conn.recv(1024)
            if not data:
                break
            try:
                command = json.loads(data.decode())
                response = handle_command(command.get("command", ""))
            except Exception as e:
                response = {"status": "error", "message": str(e)}

            conn.sendall((json.dumps(response) + "\n").encode())

            if command.get("command") == "shutdown":
                logging.warning("Shutdown received. Closing connection.")
                break
