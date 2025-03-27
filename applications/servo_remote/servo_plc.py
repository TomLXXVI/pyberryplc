import os
from rpi_plc.plc import AbstractPLC
from rpi_plc.remote_interface import RemoteDeviceClient
from rpi_plc.logging import init_logger


class ServoControlPLC(AbstractPLC):
    
    def __init__(self, pin_factory=None, eml_notification=None):
        super().__init__(pin_factory, eml_notification)
        self.remote_device = RemoteDeviceClient(logger=self.logger.info)

        # Scan-flags
        self._first_scan = True

        # SFC-steps
        self.X0 = self.add_step('X0')
        self.X1 = self.add_step('X1')

        # Pushbutton input (GPIO 4)
        self.btn = self.add_digital_input(pin=4, label="BTN")

        # Synchronization status
        self.command_done = False

    def init_control(self):
        if self._first_scan:
            self.remote_device.connect()
            self._first_scan = False
            self.X0.activate()
            self.logger.info("Machine ready.")
            
    def sequence_control(self):
        if self.X0.active and self.btn.active:
            self.X0.deactivate()
            self.X1.activate()
        
        if self.X1.active and self.command_done:
            self.X1.deactivate()
            self.X0.activate()

    def execute_actions(self):
        if self.X0.active:
            self.command_done = False
        
        if self.X1.active:
            if self.X1.raising_edge:
                try:
                    self.remote_device.send_command({"command": "move"})
                    self.logger.info("Command 'move' sent to slave.")
                except Exception as e:
                    self.logger.error(f"Sending of 'move' failed: {e}")
            try:
               self.remote_device.wait_for_done()
               self.logger.info("Slave confirmed: movement finished.")
               self.command_done = True
            except Exception as e:
               self.logger.error(f"Error while waiting for 'done': {e}")
                   
    def control_routine(self):
        self.init_control()
        self.sequence_control()
        self.execute_actions()

    def exit_routine(self):
        try:
            self.remote_device.shutdown()
        except Exception:
            self.logger.warning("Failure to send shutdown to slave.")
        self.remote_device.close()

    def emergency_routine(self):
        self.logger.error("E-stop activated!")
        self.remote_device.close()


def main():
    init_logger()
    os.system("clear")
    servo_plc = ServoControlPLC()
    servo_plc.run()


if __name__ == '__main__':
    main()
