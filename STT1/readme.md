# Robot Control System

## Installation

```bash
pip3 list
pip freeze > my_requirements.txt
sudo pip3 install -r requirements.txt
```

## Hardware Setup

### Ultrasonic Sensors Wiring

**IMPORTANT:** The robot uses 3 HC-SR04 ultrasonic sensors for obstacle detection.

See **[WIRING.md](WIRING.md)** for complete wiring instructions.

Quick wiring summary:
- **Left Sensor**: Trig=GPIO18, Echo=GPIO23
- **Center Sensor**: Trig=GPIO24, Echo=GPIO25  
- **Right Sensor**: Trig=GPIO5, Echo=GPIO6
- All sensors share: VCC→5V, GND→GND

### Motor Controller

Motor pins are already configured in `hardware/motor_controller.py`:
- IN1=GPIO4, IN2=GPIO17 (Left Motor)
- IN3=GPIO27, IN4=GPIO22 (Right Motor)

## Usage

The robot will automatically use real sensors if available, or fall back to simulation mode for testing.

To force simulation mode (for testing without hardware):
```python
robot = RobotController(use_real_sensors=False)
```
