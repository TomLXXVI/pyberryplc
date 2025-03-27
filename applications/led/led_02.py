import os
from rpi_plc import AbstractPLC, MemoryVariable
from rpi_plc.switches import ToggleSwitch
from rpi_plc.logging import init_logger


class LedPLC(AbstractPLC):
    
    def __init__(self):
        super().__init__()
        
        # Inputs & Outputs
        button = self.add_digital_input(4, 'button')
        self.switch = ToggleSwitch(button)
        self.led = self.add_digital_output(27, 'led')
        
        # Flags
        self.init_flag = True
        
        # Steps
        self.X0 = MemoryVariable()
        self.X1 = MemoryVariable()
    
    def _init_control(self):
        self.init_flag = False
        self.X0.activate()
        self.logger.info("led control ready")
    
    def _sequence_control(self):
        # Update the state of the switch in the current PLC scan loop.
        self.switch.update()
        
        if self.X0.active and self.switch.active:
            self.X0.deactivate()
            self.X1.activate()
            self.logger.info("turn led on")
        
        if self.X1.active and not self.switch.active:
            self.X1.deactivate()
            self.X0.activate()
            self.logger.info("turn led off")
    
    def _execute_actions(self):
        if self.X0.active:
            self.led.deactivate()
        
        if self.X1.active:
            self.led.activate()
    
    def control_routine(self):
        if self.init_flag: self._init_control()
        self._sequence_control()
        self._execute_actions()
            
    def exit_routine(self):
        pass
    
    def emergency_routine(self):
        pass


def main():
    os.system("clear")
    init_logger()
    led_plc = LedPLC()
    led_plc.run()


if __name__ == '__main__':
    main()
