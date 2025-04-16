from rpi_plc.stepper.stepper_gpio import TMC2208StepperMotor
import time

# Stel hier je GPIO-pinnen in
STEP_PIN = 27
DIR_PIN = 26
EN_PIN = 19
MS1_PIN = 23
MS2_PIN = 24

motor = TMC2208StepperMotor(
    step_pin=STEP_PIN,
    dir_pin=DIR_PIN,
    enable_pin=EN_PIN,
    ms1_pin=MS1_PIN,
    ms2_pin=MS2_PIN,
    microstep_mode="1/8",
    steps_per_revolution=200
)

# Trapeziumprofiel parameters
total_steps = 1600
min_speed = 100     # stappen per seconde
max_speed = 800     # stappen per seconde
acc_steps = 400     # aantal stappen voor versnellen
dec_steps = 400     # aantal stappen voor vertragen
flat_steps = total_steps - acc_steps - dec_steps

def rotate_n_steps(n: int, speed: float) -> None:
    delay = 1.0 / speed / 2
    for _ in range(n):
        motor.step.write(True)
        time.sleep(delay)
        motor.step.write(False)
        time.sleep(delay)

# Richting instellen
motor.dir.write(True)  # of False

print("Versnellen...")
for i in range(acc_steps):
    speed = min_speed + (max_speed - min_speed) * (i / acc_steps)
    rotate_n_steps(1, speed)

print("Constante snelheid...")
rotate_n_steps(flat_steps, max_speed)

print("Vertragen...")
for i in range(dec_steps):
    speed = max_speed - (max_speed - min_speed) * (i / dec_steps)
    rotate_n_steps(1, speed)

print("Beweging voltooid.")
