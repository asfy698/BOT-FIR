# Robot Wiring Guide

## Ultrasonic Sensors (HC-SR04) - 3 Sensors Required

### Sensor Pinout
Each HC-SR04 ultrasonic sensor has 4 pins:
- **VCC** - Power (5V)
- **GND** - Ground
- **Trig** - Trigger pin (GPIO output)
- **Echo** - Echo pin (GPIO input)

### Raspberry Pi GPIO Pinout (BCM Numbering)

```
Physical Pin    BCM GPIO    Function
─────────────────────────────────────
Pin 2           5V          Power
Pin 6           GND         Ground
Pin 11          GPIO 17     Motor IN2 (Left)
Pin 13          GPIO 27     Motor IN3 (Right)
Pin 15          GPIO 22     Motor IN4 (Right)
Pin 18          GPIO 24     Motor IN1 (Left)
Pin 19          GPIO 10     (Available)
Pin 21          GPIO 9      (Available)
Pin 23          GPIO 11     (Available)
Pin 24          GPIO 8      (Available)
Pin 26          GPIO 7      (Available)
Pin 29          GPIO 5      Right Sensor Trig
Pin 31          GPIO 6      Right Sensor Echo
Pin 33          GPIO 13     (Available)
Pin 35          GPIO 19     Left Sensor Trig
Pin 37          GPIO 26     (Available)
Pin 38          GPIO 20     Center Sensor Trig
Pin 40          GPIO 21     Left Sensor Echo
```

### Default Wiring Configuration

#### Left Ultrasonic Sensor
- **VCC** → Pin 2 (5V) or Pin 4 (5V)
- **GND** → Pin 6 (GND) or Pin 9 (GND)
- **Trig** → Pin 35 (GPIO 19)
- **Echo** → Pin 40 (GPIO 21)

#### Center Ultrasonic Sensor
- **VCC** → Pin 2 (5V) or Pin 4 (5V)
- **GND** → Pin 6 (GND) or Pin 9 (GND)
- **Trig** → Pin 38 (GPIO 20)
- **Echo** → Pin 22 (GPIO 25)

#### Right Ultrasonic Sensor
- **VCC** → Pin 2 (5V) or Pin 4 (5V)
- **GND** → Pin 6 (GND) or Pin 9 (GND)
- **Trig** → Pin 29 (GPIO 5)
- **Echo** → Pin 31 (GPIO 6)

### Power Distribution

**Important:** All 3 sensors can share the same 5V and GND lines:
- Connect all **VCC** pins together → Raspberry Pi Pin 2 or Pin 4 (5V)
- Connect all **GND** pins together → Raspberry Pi Pin 6 or Pin 9 (GND)

### Motor Controller (L298N) Wiring

Already configured in `motor_controller.py`:
- **IN1** → GPIO 4 (Pin 7)
- **IN2** → GPIO 17 (Pin 11)
- **IN3** → GPIO 27 (Pin 13)
- **IN4** → GPIO 22 (Pin 15)

### Customizing GPIO Pins

If you need to use different GPIO pins, edit `hardware/robot_controller.py`:

```python
# In __init__ method, change:
self.ultrasonic_array = UltrasonicSensorArray(
    left_trig=19, left_echo=21,      # Change these
    center_trig=20, center_echo=25,  # Change these
    right_trig=5, right_echo=6        # Change these
)
```

### Testing Sensors

To test if sensors are working, you can run:

```python
from hardware.robot_controller import RobotController

robot = RobotController(use_real_sensors=True)
print(f"Left: {robot.get_left_distance()}cm")
print(f"Center: {robot.get_center_distance()}cm")
print(f"Right: {robot.get_right_distance()}cm")
```

### Troubleshooting

1. **Sensors always return 400cm or 0cm:**
   - Check wiring connections
   - Verify GPIO pins are correct
   - Ensure sensors have power (5V and GND)

2. **Import errors:**
   - Make sure you're running on Raspberry Pi
   - Install RPi.GPIO: `pip3 install RPi.GPIO`

3. **Sensors not detecting obstacles:**
   - Check threshold in `sensors/object_avoid.py` (default: 20cm)
   - Verify sensors are facing forward
   - Test individual sensors with the code above

### Notes

- HC-SR04 sensors have a range of 2cm to 400cm
- Minimum detection distance: ~2cm
- Maximum detection distance: ~400cm
- Response time: ~60ms per reading
- The code takes 3 readings and uses the median for stability

