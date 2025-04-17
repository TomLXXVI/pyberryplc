import os
from pyberryplc.core import AbstractPLC, MemoryVariable
from pyberryplc.core.timers import TimerOnDelay
from pyberryplc.log_utils import init_logger


class ServoSubroutine:
    """Implements a simple servo motor motion sequence inside a subroutine which
    will be called by the main PLC routine. The subroutine turns the servo motor
    from the start angle to the end angle in a number of steps (one step is 10°).
    """
    def __init__(self, calling_step: MemoryVariable, servo: MemoryVariable):
        """Creates the `ServoSubroutine` object.
        
        Parameters
        ----------
        calling_step:
            The step in the main routine from where the subroutine is called.
        servo:
            Reference to the servo motor output, which is created in the 
            __init__() method of the main PLC class (`ServoPLC` class, see 
            below).             
        """
        self.calling_step = calling_step
        self.servo = servo
        # Define a range of angular positions to drive the servo motor. Each
        # angle will correspond with a step in the subroutine.
        self.angles = [angle for angle in range(-50, 70, 10)]
        self.servo_steps = [MemoryVariable() for _ in self.angles]        
        # Define the initial step to trigger the subroutine in the 
        # initialization of main routine, and define the end step of the 
        # subroutine which will be used to deactivate the subroutine in the
        # main routine.
        self.init_step = MemoryVariable()
        self.end_step = MemoryVariable()
        # We need a timer to move from one step to the next as the servo motor
        # does not provide feedback when the desired angle in the step has been
        # reached.
        self.step_timer = TimerOnDelay(1)
        # To avoid code duplication, we use a step counter to keep track of
        # which step is active.
        self.step_counter = 0
        
    def init(self):
        """Initializes the subroutine. This function is called in the 
        initialization step of the main routine. It activates the init step of 
        the subroutine.
        """
        self.init_step.activate()
    
    def _sequence_control(self):
        """Controls the activation and deactivation of subsequent steps in the 
        sequence. This is an internal function of the subroutine.
        """
        # The subroutine is already "triggered" at the start of the main 
        # program, but waits here until the calling step in the main routine 
        # becomes active.
        if self.init_step.active and self.calling_step.active:
            self.init_step.deactivate()
            self.servo_steps[0].activate()  # activate the first step of the servo sequence.
        
        # Servo motion sequence. The transition from one step to the next is
        # controlled by a timer to make sure the motion in one step is finished
        # before going to the next step.
        i = self.step_counter
        if self.servo_steps[i].active and self.step_timer.has_elapsed:
            self.servo_steps[i].deactivate()
            self.step_timer.reset()
            if i + 1 < len(self.servo_steps):
                self.servo_steps[i + 1].activate()
                self.step_counter += 1
            else:
                # End of the servo motion sequence is reached; activate the
                # end step of the subroutine.
                self.end_step.activate()
        
        if self.end_step.active:
            # Reset the subroutine to its initial state.
            self.step_counter = 0
            self.init_step.activate()
    
    def _execute_actions(self):
        """Executes the actions that belong to the active step in the subroutine
        sequence. This is an internal function of the subroutine.
        """
        i = self.step_counter
        if self.servo_steps[i].active:
            self.servo.update(self.angles[i])
    
    def __call__(self):
        """Calls the subroutine from the main routine."""
        self._sequence_control()  # determine which step is active
        self._execute_actions()   # execute the actions that belong to the active step
    

class ServoPLC(AbstractPLC):
    """Simple PLC application to drive a PWM controlled servo motor."""
    def __init__(self):
        super().__init__()
        
        # Inputs & Outputs
        self.button1 = self.add_digital_input(
            pin=4, 
            label='button1'
        )
        self.servo, _ = self.add_pwm_output(
            pin=13, 
            label='servo',
            frame_width=20,
            min_pulse_width=1 - 0.37,
            max_pulse_width=2,
            min_value=-60,
            max_value=60
        )
        
        # Internal flags.
        self.init_flag = True
        
        # Steps of the main program
        self.X0 = MemoryVariable()
        self.X1 = MemoryVariable()
        
        # Subroutines used by the main program
        self.servo_subroutine = ServoSubroutine(self.X1, self.servo)
    
    def _init_control(self):
        """Initializes the PLC control. This function is called only once in the
        first PLC scan of the main routine.
        """
        self.init_flag = False
        self.X0.activate()
        self.servo_subroutine.init()  # set servo subroutine ready 
        self.logger.info("servo ready")
        
    def _sequence_control(self):
        """Controls the activation and deactivation of subsequent steps in the 
        sequence.
        """
        # Transition step X0 -> step X1. The transition happens when the user
        # has pressed the button.
        if self.X0.active and self.button1.active:
            self.X0.deactivate()
            self.X1.activate()  # turn next step X1 active
            self.logger.info("start servo sequence")
        
        # Transition step X1 -> X0. The transition happens when the servo 
        # subroutine has reached its end step.
        if self.X1.active and self.servo_subroutine.end_step.active:
            self.servo_subroutine.end_step.deactivate()  # 
            self.X1.deactivate()
            self.X0.activate()
            self.logger.info("move to -60°")
    
    def _execute_actions(self):
        """Executes the actions that belong to the active step in the main 
        routine sequence. This is an internal function of the subroutine.
        """
        if self.X0.active:
            # As long as step X0 is active, command servo to move or stay at
            # angle -60°.
            self.servo.update(-60.0)
        
        if self.X1.active:
            # As long as step X1 is active, call the servo subroutine sequence.
            self.servo_subroutine()
    
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
    servo_plc = ServoPLC()
    servo_plc.run()


if __name__ == '__main__':
    main()
