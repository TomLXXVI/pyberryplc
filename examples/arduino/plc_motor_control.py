import os
from rpi_plc import AbstractPLC
from rpi_plc.remote_interface import SerialRemoteDeviceClient
from rpi_plc.timers import OnDelayTimer
from rpi_plc.logging import init_logger
from rpi_plc.exceptions import EmergencyException


class MotorControlPLC(AbstractPLC):
    
    def __init__(self):
        super().__init__()

        # === Hardware Configuration ===
        self.start_btn = self.add_digital_input(pin=4, label="start_button")
        self.status_led, _ = self.add_digital_output(pin=27, label="status_led")

        # === SFC-steps ===
        self.X0 = self.add_marker("X0")
        self.X1 = self.add_marker("X1")
        self.X2 = self.add_marker("X2")
        self.X3 = self.add_marker("X3")

        # === Serial Client ===
        self.client = SerialRemoteDeviceClient(port="/dev/ttyACM0", baudrate=9600, logger=self.logger)
        self.timer_start = 0.0
        
        # === Timers ===
        self.T1 = OnDelayTimer(5)
        
        # === Internal Flags ===
        self.init_flag = True
        self.step1_finished = False
        self.step2_finished = False
        self.step3_finished = False

    def init_control(self):
        if self.init_flag:
            self.init_flag = False
            
            try:
                self.client.connect()
            except ConnectionError as e:
                self.logger.error(f"Connection failed: {e}")
                raise EmergencyException

            self.X0.activate()
            self.logger.info("Serial connection established with Arduino.")

    def sequence_control(self):
        # X0 -> X1: start button raising edge
        if self.X0.active and self.start_btn.raising_edge:
            self.X0.deactivate()
            self.X1.activate()

        # X1 -> X2: after successful "start"-command
        if self.X1.active and self.step1_finished:
            self.X1.deactivate()
            self.X2.activate()

        # X2 -> X3: after successful "set_speed"-command and timer T1 has elapsed
        if self.X2.active and self.step2_finished and self.T1.has_elapsed:
            self.X2.deactivate()
            self.X3.activate()

        # X3 -> X0: after successful "stop"-command 
        if self.X3.active and self.step3_finished:
            self.X3.deactivate()
            self.X0.activate()

    def execute_actions(self):
        self.status_led.update(
            self.X1.active 
            or self.X2.active 
            or self.X3.active
        )
        
        if self.X0.active:
            self.T1.reset()
            self.step1_finished = False
            self.step2_finished = False
            self.step3_finished = False

        if self.X1.raising_edge:
            r = self._send_command({"command": "start"})
            if r:
                self.step1_finished = True
            else:
                raise EmergencyException
            
        if self.X2.raising_edge:
            r = self._send_command({"command": "set_speed", "value": 240})
            if r:
                self.step2_finished = True
            else:
                raise EmergencyException
            
        if self.X3.raising_edge:
            r = self._send_command({"command": "stop"})
            if r:
                self.step3_finished = True
            else:
                raise EmergencyException
    
    def _send_command(self, cmd: dict):
        try:
            self.client.send_command(cmd)
            self.client.wait_for_done()
            self.logger.info(f"Command executed: {cmd}")
            return True
        except Exception as e:
            self.logger.error(f"Command failed: {e}")
            return False
        
    def control_routine(self):
        self.init_control()
        self.sequence_control()
        self.execute_actions()
    
    def exit_routine(self):
        self.client.shutdown()
        self.client.close()

    def emergency_routine(self):
        try:
            self.exit_routine()
        except:
            pass


def main():
    os.system("clear")
    init_logger()
    plc = MotorControlPLC()
    plc.run()


if __name__ == '__main__':
    main()
    