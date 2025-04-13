import os
from rpi_plc import AbstractPLC
from rpi_plc.log_utils import init_logger
from rpi_plc.stepper.stepper_gpio import TMC2208StepperMotor
from rpi_plc.stepper.stepper_gpio import TrapezoidalProfile

from keyboard_input import KeyInput


class PLC(AbstractPLC):
    
    def __init__(self):
        super().__init__()
        self.key_input = KeyInput()

        self.stepper = TMC2208StepperMotor(
            step_pin=27,
            dir_pin=26,
            enable_pin=19,
            ms1_pin=13,
            ms2_pin=21,
            microstep_mode="1/16",
            steps_per_revolution=200,
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

    def control_routine(self):
        self.key_input.update()
        self.init_control()
        self.sequence_control()
        self.execute_actions()
    
    def init_control(self):
        if self.input_flag:
            self.input_flag = False
            self.X0.activate()
    
    def sequence_control(self):
        if self.X0.active and self.key_input.rising_edge('w'):
            self.X0.deactivate()
            self.X1.activate()
            
        if self.X1.active and self.key_input.rising_edge('s'):
            self.X1.deactivate()
            self.X2.activate()
        
        if self.X2.active and self.key_input.rising_edge('q'):
            self.X2.deactivate()
            self.X0.activate()
            
    def execute_actions(self):
        if self.X0.rising_edge:
            self.logger.info("Press key 'w' to turn motor forward.")
            
        if self.X1.rising_edge:
            self.logger.info("Turn forward")
            self.stepper.rotate(
                degrees=1080, 
                direction="forward", 
                profile=self.profile
            )
            self.logger.info("Press key 's' to turn motor backward.")
            
        if self.X2.rising_edge:
            self.logger.info("Turn backward")
            self.stepper.rotate(
                degrees=1080, 
                direction="backward", 
                profile=self.profile
            )
            self.logger.info("Press key 'q' to start new cycle or <Ctrl-Z> to exit.")
            
    def exit_routine(self):
        self.logger.info("PLC stopped. Motor turned off.")
        self.stepper.disable()
    
    def emergency_routine(self):
        pass


def main():
    os.system("clear")
    print(f"Running as user: {os.geteuid()}")
    init_logger()
    plc = PLC()
    plc.run()
    

if __name__ == "__main__":
    main()
