import eventlet
eventlet.monkey_patch()  # patch for green threads

from flask import Flask, render_template
from flask_socketio import SocketIO
import serial

# ===== Arduino Serial Port =====
ARDUINO_PORT = '/dev/ttyUSB0'  # Update if needed
BAUD_RATE = 9600

# ===== Initialize Flask and SocketIO =====
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ===== Initialize Serial =====
try:
    ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    print("Serial connected successfully!")
except Exception as e:
    print("Error connecting to Arduino:", e)
    ser = None

# ===== Motor Control Functions =====
def motor_retract():
    if ser:
        ser.write(b'RETRACT\n')  # Arduino handles this command

def motor_reverse():
    if ser:
        ser.write(b'REVERSE\n')  # Arduino handles this command

# ===== Read Sensors in Background =====
def read_sensors():
    if not ser:
        print("Serial not initialized!")
        return

    while True:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                continue

            # Example: 25.0,60.0,80,150,20
            parts = line.split(",")
            if len(parts) != 5:
                continue

            try:
                data = {
                    'temperature': float(parts[0]),
                    'humidity': float(parts[1]),
                    'light': int(parts[2]),
                    'mq135': int(parts[3]),
                    'rain': int(parts[4])
                }
            except ValueError:
                continue

            # ===== Alerts (logic remains in server for display) =====
            alerts = []

            if data['rain'] >= 90:
                alerts.append("Incoming Rainfall!")

            if data['humidity'] >= 98:
                alerts.append("High Humidity: Rain likely!")

            if data['light'] <= 75:
                alerts.append("Cloudy or Low Light detected!")

            if data['mq135'] >= 500:
                alerts.append("Severe Smoke Detected! Automatic Retract!")

            data['alerts'] = alerts

            # Emit to all clients
            socketio.emit('sensor_data', data)

            # Reduce sleep time for a faster update rate.
            # 0.01 seconds provides a near real-time feel.
            eventlet.sleep(0.01)

        except Exception as e:
            print("Error reading serial:", e)
            eventlet.sleep(1)

# Start background green thread
eventlet.spawn(read_sensors)

# ===== Flask route =====
@app.route('/')
def index():
    return render_template('index.html')

# ===== SocketIO events for manual motor control =====
@socketio.on('manual_retract')
def handle_manual_retract():
    print("Manual retract requested")
    motor_retract()

@socketio.on('manual_reverse')
def handle_manual_reverse():
    print("Manual reverse requested")
    motor_reverse()

@socketio.on('steamer_on')
def handle_steamer_on():
    print("Steamer ON requested")
    if ser:
        ser.write(b'STEAMER_ON\n')

# ===== Run Server =====
if __name__ == '__main__':
    print("Server running at http://0.0.0.0:5000")
    socketio.run(app, host='0.0.0.0', port=5000)
