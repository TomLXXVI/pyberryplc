# app.py - pyberryplc HMI server using Flask + Flask-SocketIO

from threading import Thread, Event
import time

import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO


# DummyTMC2208UART simulates a UART-connected driver.
# It allows testing the HMI without real hardware.
class DummyTMC2208UART:
    def __init__(self):
        self.run_current_pct = 0
        self.hold_current_pct = 0
        self.sg_result = 0

    def set_currents(self, run, hold):
        """Simulates setting run/hold current percentage."""
        self.run_current_pct = run
        self.hold_current_pct = hold

    def read_sg_result(self):
        """Simulates reading a sensorless stallguard result (SG_RESULT)."""
        self.sg_result = (self.sg_result + 10) % 256
        return self.sg_result

# ------------------------------------------------------------------------------
# Initialize Flask app and SocketIO for WebSocket support
app = Flask(__name__, template_folder='templates')
socketio = SocketIO(app, async_mode='eventlet')

# Create a dummy UART handler (to be replaced with real TMC2208UART later)
uart_handler = DummyTMC2208UART()

@app.route('/')
def index():
    """Renders the main HMI page with current parameter values."""
    return render_template(
        'index.html', 
        run_current=uart_handler.run_current_pct, 
        hold_current=uart_handler.hold_current_pct
    )

@app.route('/set_currents', methods=['POST'])
def set_currents():
    """Handles form submission to update run/hold current settings."""
    run = int(request.form['run_current_pct'])
    hold = int(request.form['hold_current_pct'])
    uart_handler.set_currents(run, hold)
    return redirect(url_for('index'))

# ------------------------------------------------------------------------------
# Background thread to send SG_RESULT over WebSocket to connected clients
def emit_sg_result(stop_event):
    """Periodically emits SG_RESULT values over WebSocket."""
    while not stop_event.is_set():
        value = uart_handler.read_sg_result()
        socketio.emit('sg_update', {'sg_result': value})
        time.sleep(1)  # Adjust frequency as needed

# Set up and start the background thread
stop_event = Event()
th = Thread(target=emit_sg_result, args=(stop_event,))
th.daemon = True
th.start()

# ------------------------------------------------------------------------------
# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Logs when a client connects via WebSocket."""
    print("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    """Logs when a client disconnects."""
    print("Client disconnected")

# ------------------------------------------------------------------------------
# Launch the Flask app with WebSocket support
if __name__ == '__main__':
    # host='0.0.0.0' makes the server accessible on the local network
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
