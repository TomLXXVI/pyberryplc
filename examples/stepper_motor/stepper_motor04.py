import os
from rpi_plc.core import AbstractPLC
from rpi_plc.stepper import TMC2208StepperMotor, TMC2208UART, TrapezoidalProfile
from rpi_plc.log_utils import init_logger
from keyboard_input import KeyInput


class StepperUARTTestPLC(AbstractPLC):
    
    def __init__(self):
        super().__init__()
        
        self.key_input = KeyInput()

        self.stepper = TMC2208StepperMotor(
            step_pin=27,
            dir_pin=26,
            steps_per_revolution=200,
            uart=TMC2208UART(port="/dev/ttyAMA0"),
            logger=self.logger
        )

        self.profile = TrapezoidalProfile(
            min_angular_speed=11.25,
            max_angular_speed=720.0,
            accel_angle=90,
            decel_angle=90
        )
        
        self.X0 = self.add_marker("X0")
        self.X1 = self.add_marker("X1")
        self.X2 = self.add_marker("X2")

        self.input_flag = True
    
    def _init_control(self):
        if self.input_flag:
            self.input_flag = False
            self.stepper.enable()
            self.stepper.set_microstepping("1/16")
            self.X0.activate()
    
    def _sequence_control(self):
        if self.X0.active and self.key_input.rising_edge("s"):
            self.logger.info("Start: rotating forward")
            self.X0.deactivate()
            self.X1.activate()
            
        if self.X1.active and self.key_input.rising_edge("r"):
            self.logger.info("Reverse: rotating backward")
            self.X1.deactivate()
            self.X2.activate()
            
        if self.X2.active and self.key_input.is_pressed("q"):
            self.logger.info("Back to idle")
            self.X2.deactivate()
            self.X0.activate()
    
    def _execute_actions(self):
        if self.X0.rising_edge:
            self.logger.info("Press 's' to start motor")
            
        if self.X1.rising_edge:
            self.stepper.rotate(720, direction="forward", profile=self.profile)
            self.logger.info("Press 'r' to start motor in reverse")
            
        if self.X2.rising_edge:
            self.stepper.rotate(720, direction="backward", profile=self.profile)
            self.logger.info("Press 'q' to go back to idle")
            
    def control_routine(self):
        self.key_input.update()
        self._init_control()
        self._sequence_control()
        self._execute_actions()
    
    def exit_routine(self):
        self.logger.info("Exiting... disabling driver.")
        self.stepper.disable()

    def emergency_routine(self):
        pass
    

if __name__ == "__main__":
    os.system("clear")
    init_logger()
    plc = StepperUARTTestPLC()
    plc.run()
