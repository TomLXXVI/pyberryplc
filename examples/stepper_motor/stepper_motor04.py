import os
from rpi_plc.core import AbstractPLC
from rpi_plc.stepper import TMC2208StepperMotor, TMC2208UART
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
            logger=self.logger
        )
        
        self.uart = TMC2208UART(port="/dev/ttyAMA0")

        self.X0 = self.add_marker("X0")
        self.X1 = self.add_marker("X1")
        self.X2 = self.add_marker("X2")

        self.input_flag = True
    
    def _init_control(self):
        if self.input_flag:
            self.input_flag = False
        
            self.logger.info("Initializing stepper via UART...")
            self.uart.open()
            try:
                # toff = 3, mres = 5 (1/8 microstepping)
                mask = 0xF | (0xF << 24)
                value = 3 | (5 << 24)
                self.uart.update_register_bits(0x6C, mask, value)
                self.logger.info("CHOPCONF configured.")
            except IOError as e:
                self.logger.error(f"UART config failed: {e}")
            
            self.X0.activate()
    
    def _sequence_control(self):
        if self.X0.active and self.key_input.rising_edge("s"):
            self.logger.info("Start: rotating forward.")
            self.X0.deactivate()
            self.X1.activate()
            
        if self.X1.active and self.key_input.rising_edge("r"):
            self.logger.info("Reverse: rotating backward.")
            self.X1.deactivate()
            self.X2.activate()
            
        if self.X2.active and self.key_input.is_pressed("q"):
            self.logger.info("Back to idle.")
            self.X2.deactivate()
            self.X0.activate()
    
    def _execute_actions(self):
        if self.X1.rising_edge:
            self.stepper.rotate(720, direction="forward", angular_speed=180)
        
        if self.X2.rising_edge:
            self.stepper.rotate(720, direction="backward", angular_speed=180)
    
    def control_routine(self):
        self.key_input.update()
        self._init_control()
        self._sequence_control()
        self._execute_actions()
    
    def exit_routine(self):
        self.logger.info("Exiting... disabling driver.")
        try:
            self.uart.update_register_bits(0x6C, 0xF, 0)
        except IOError as e:
            self.logger.warning(f"Could not disable driver: {e}")
        self.uart.close()

    def emergency_routine(self):
        pass
    


if __name__ == "__main__":
    os.system("clear")
    init_logger()
    plc = StepperUARTTestPLC()
    plc.run()
