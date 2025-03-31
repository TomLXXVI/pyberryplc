import os
import subprocess
from rpi_plc import AbstractPLC
from rpi_plc.switches import ToggleSwitch
from rpi_plc.timers import OnDelayTimer
from rpi_plc.counters import UpCounter
from rpi_plc.remote_interface import TCPRemoteDeviceClient
from rpi_plc.logging import init_logger


class PLC(AbstractPLC):
    
    def __init__(self):
        super().__init__()
        
        # Remote servo drive
        self.servo_drive = TCPRemoteDeviceClient(logger=self.logger)
        
        # Inputs & Outputs
        PIN_start = 4
        PIN_stop = 27
        
        self.start_btn = self.add_digital_input(PIN_start, 'start')
        stop_btn = self.add_digital_input(PIN_stop, 'stop')
        self.stop_switch = ToggleSwitch(stop_btn)
        
        # SFC Step markers
        self.X0 = self.add_marker('X0')
        
        self.X10 = self.add_marker('X10')
        self.X11 = self.add_marker('X11')
        self.X12 = self.add_marker('X12')

        self.X20 = self.add_marker('X20')
        self.X21 = self.add_marker('X21')
        self.X22 = self.add_marker('X22')

        self.X30 = self.add_marker('X30')
        self.X31 = self.add_marker('X31')
        self.X32 = self.add_marker('X32')

        self.X40 = self.add_marker('X40')
        self.X41 = self.add_marker('X41')
        self.X42 = self.add_marker('X42')
        
        # Markers
        self.pos1_free = self.add_marker('pos1_free')
        self.pos2_free = self.add_marker('pos2_free')
        self.pos3_free = self.add_marker('pos3_free')
    
        # Flags & Other Stuff
        self.init_flag = True
        self.pouches_available = True
        self.batch_size: int = 0
        
        # Timers
        self.T1 = OnDelayTimer(1)
        self.T2 = OnDelayTimer(2)
        self.T3 = OnDelayTimer(0.5)
        self.T4 = OnDelayTimer(1)
        
        # Counters
        self.pouch_counter = UpCounter()
        
    def init_control(self):
        if self.init_flag:
            self.servo_drive.connect()
            
            self.pos1_free.update(1)           
            self.pos2_free.update(1)
            self.pos3_free.update(1)
            
            self.batch_size = int(input("Enter batch size: "))
            
            self.X0.activate()
            self.logger.info("Machine ready.")

            self.init_flag = False
    
    def sequence_control(self):
        # Update state of stop soft switch
        self.stop_switch.update()
        
        # Stop condition
        stop_condition = (
                self.stop_switch.active 
                or self.pouch_counter.value == self.batch_size
        )
        
        if self.X0.active and self.start_btn.active:
            self.logger.info("Start button pressed.")
            self.X0.deactivate()
            self.X10.activate()
            self.X20.activate()
            self.X30.activate()
            self.X40.activate()
        
        if self.X10.active and self.pouches_available and self.pos1_free.active:
            # self.logger.info("POS1 free.")
            self.X10.deactivate()
            self.X11.activate()
        
        if self.X11.active and not self.pos1_free.active:
            # self.logger.info("Pouch available at POS1.")
            self.X11.deactivate()
            self.X12.activate()
        
        if self.X12.active and not stop_condition:
            self.X12.deactivate()
            self.X10.activate()
        
        if self.X20.active and not self.pos1_free.active and self.pos2_free.active:
            # self.logger.info("POS2 free.")
            self.X20.deactivate()
            self.X21.activate()
        
        if self.X21.active and not self.pos2_free.active:
            # self.logger.info("Pouch available at POS2.")
            self.X21.deactivate()
            self.X22.activate()
        
        if self.X22.active and not stop_condition:
            self.X22.deactivate()
            self.X20.activate()
        
        if (self.X30.active 
            and not self.pos2_free.active 
            and self.pos3_free.active 
            and self.T3.has_elapsed
        ):
            # self.logger.info("Carrousel free.")
            self.X30.deactivate()
            self.X31.activate()
            self.T3.reset()
        
        if self.X31.active and not self.pos3_free.active:
            # self.logger.info("Pouch available on carrousel.")
            self.X31.deactivate()
            self.X32.activate()
        
        if self.X32.active and not stop_condition:
            self.X32.deactivate()
            self.X30.activate()
        
        if self.X40.active and not self.pos3_free.active:
            self.X40.deactivate()
            self.X41.activate()
        
        if self.X41.active and self.pos3_free.active:
            self.X41.deactivate()
            self.X42.activate()
        
        if self.X42.active and not stop_condition:
            self.X42.deactivate()
            self.X40.activate()
        
        if self.X12.active and self.X22.active and self.X32.active and self.X42.active and stop_condition:
            self.logger.info("Stop button pressed")
            self.X12.deactivate()
            self.X22.deactivate()
            self.X32.deactivate()
            self.X42.deactivate()
            self.X0.activate()
        
    def execute_actions(self):
        if self.X0.active:
            self.pouch_counter.reset()
        
        if self.X10.active:
            pass
        
        if self.X11.active:
            if self.X11.raising_edge:
                self.logger.info("Transfer pouch to POS1.")
                self.T1.reset()
            # simulate action
            if self.T1.has_elapsed:
                self.pos1_free.update(False)
                if self.pos1_free.falling_edge:
                    self.pouch_counter.count_up()
                    self.logger.info(f"Pouches count: {self.pouch_counter.value}")
                
        if self.X12.active:
            pass
        
        if self.X20.active:
            pass
        
        if self.X21.active:
            if self.X21.raising_edge:
                self.logger.info("Transfer pouch from POS1 to POS2.")
                self.T2.reset()
            # simulate action
            if self.T2.has_elapsed:
                self.pos2_free.update(False)
                self.pos1_free.update(True)
        
        if self.X22.active:
            pass
        
        if self.X30.active:
            pass
        
        if self.X31.active:
            if self.X31.raising_edge:
                try:
                    self.logger.info("Transfer pouch from POS2 to carrousel.")
                    self.servo_drive.send_command({"command": "move"})
                    self.logger.info("Command 'move' sent to servo.")
                except Exception as e:
                    self.logger.error(f"Sending of 'move' failed: {e}")
            
            try:
                self.servo_drive.wait_for_done()  # blocks the PLC scan
                self.logger.info("Servo confirmed: movement finished.")
                self.pos3_free.update(False)
                self.pos2_free.update(True)
            except Exception as e:
                self.logger.error(f"Error while waiting for 'done': {e}")
         
        if self.X32.active:
            pass
        
        if self.X40.active:
            pass
        
        if self.X41.active:
            if self.X41.raising_edge:
                self.logger.info("Turn carrousel one position.")
                self.T4.reset()
            # simulate action
            if self.T4.has_elapsed:
                self.pos3_free.update(True)

    def control_routine(self):
        self.init_control()
        self.sequence_control()
        self.execute_actions()
    
    def exit_routine(self):
        try:
            self.servo_drive.shutdown()
        except Exception:
            self.logger.warning("Failure to send shutdown to servo drive.")
        self.servo_drive.close()
    
    def emergency_routine(self):
        pass
    

def main():
    
    project_path = "/shared/python-projects/rpi-gpio/applications/sprout_machine"
    venv_activate = "/home/tom-chr/.virtualenvs/rpi-gpio/bin/activate"
    slave_script = os.path.join(project_path, 'servo_drive.py')
        
    os.system("clear")
    
    # Start servo drive from the main application.
    subprocess.Popen(
        ['bash', '-c', f'source {venv_activate} && python {slave_script}']
    )

    init_logger()
    plc = PLC()
    plc.run()


if __name__ == '__main__':
    main()
