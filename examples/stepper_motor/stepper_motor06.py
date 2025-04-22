"""
Test script for dynamic motion profile using DynamicDelayGenerator.

When the start button is pressed, the motor begins to accelerate.
When the stop button is pressed, the motor decelerates and stops.

Intended to be run on a Raspberry Pi using a GPIO-compatible StepperMotor subclass.
"""
from pyberryplc.core import AbstractPLC
from pyberryplc.motion_profiles import TrapezoidalProfile, DynamicDelayGenerator
from pyberryplc.stepper.driver import A4988StepperMotor  # or your specific subclass
from pyberryplc.gpio import DigitalInput

class DynamicMotionPLC(AbstractPLC):
    def init_control(self):
        self.button_start = self.add_digital_input(pin=17, pull_up=True)
        self.button_stop = self.add_digital_input(pin=27, pull_up=True)

        self.stepper = A4988StepperMotor(step_pin=20, dir_pin=21)
        self.profile = TrapezoidalProfile(v_m=360.0, a_m=720.0, ds_tot=90.0)  # deg/s, deg/s², deg
        self.generator = DynamicDelayGenerator(self.stepper, self.profile)

        self.motion_active = False

    def execute_actions(self):
        if self.button_start.read() and not self.motion_active:
            self.logger.info("Motion started.")
            self.stepper.start_rotation_dynamic(self.generator, direction="forward")
            self.motion_active = True

        if self.button_stop.read() and self.motion_active:
            self.logger.info("Motion stopping...")
            self.generator.trigger_decel()
            self.motion_active = False

        self.stepper.do_single_step()

if __name__ == "__main__":
    plc = DynamicMotionPLC(scan_cycle=0.005)
    try:
        plc.run()
    except KeyboardInterrupt:
        plc.stop()
