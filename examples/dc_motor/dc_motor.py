import os
from rpi_plc import AbstractPLC
from rpi_plc.switches import ToggleSwitch
from rpi_plc.logging import init_logger


class PLC(AbstractPLC):
    
    def __init__(self):
        super().__init__()
        
        PIN_btn = 4
        PIN_motor = 27
        
        button = self.add_digital_input(PIN_btn, 'button')
        self.switch = ToggleSwitch(button)
        self.motor, _ = self.add_digital_output(PIN_motor, 'motor')
        
        self.X0 = self.add_marker('X0')
        self.X1 = self.add_marker('X1')
        
        self.init_flag = True
        
    def _init_control(self):
        if self.init_flag:
            self.init_flag = False
            self.X0.activate()
            self.logger.info('Machine ready. Press button to start motor.')
    
    def _sequence_control(self):
        # Update soft switch state (depends on the current state of the button) 
        self.switch.update()
        if self.switch.rising_edge:
            self.logger.info('Press button to stop motor.')
        if self.switch.falling_edge:
            self.logger.info('Press button to start motor.')
        
        if self.X0.active and self.switch.active:
            self.X0.deactivate()
            self.X1.activate()
        
        if self.X1.active and not self.switch.active:
            self.X1.deactivate()
            self.X0.activate()
    
    def _execute_actions(self):
        if self.X0.active:
            self.motor.update(0)
        
        if self.X1.active:
            self.motor.update(1)
    
    def control_routine(self):
        self._init_control()
        self._sequence_control()
        self._execute_actions()
    
    def exit_routine(self):
        pass
    
    def emergency_routine(self):
        pass
    

def main():
    os.system("clear")
    init_logger()
    plc = PLC()
    plc.run()
    

if __name__ == '__main__':
    main()
