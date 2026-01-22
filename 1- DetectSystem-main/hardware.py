# hardware.py
import RPi.GPIO as GPIO
import pigpio
import config
import state
from gpiozero import LED
from mqtt_client import publish_alarm_event, stop_dht  # Import hàm alarm

# Khởi tạo 1 lần
led = LED(config.LED_PIN)
GPIO.setmode(GPIO.BCM)
GPIO.setup(config.BUZZER_PIN, GPIO.OUT)
GPIO.output(config.BUZZER_PIN, GPIO.LOW)

def init_hardware():
    """Khởi động PIGPIO và đưa servo về home."""
    print("[HARDWARE] Initializing...")
    try:
        state.pi_gpio = pigpio.pi()
        if not state.pi_gpio.connected:
            raise Exception("Failed to connect to pigpio daemon")
        
        print("[PIGPIO] Connected to pigpio daemon.")
        move_servo_home()
        publish_alarm_event("SERVO INITIALIZATION SUCCESSFUL", alert_type="alarm_system")
    except Exception as e:
        print(f"[PIGPIO ERROR] Unable to initialize pigpio: {e}")
        publish_alarm_event("SERVO INITIALIZATION FAILED", alert_type="alarm_system")
        state.pi_gpio = None

def activate_buzzer(high=True):
    """Bật/tắt còi báo động."""
    GPIO.output(config.BUZZER_PIN, GPIO.HIGH if high else GPIO.LOW)

def map_angle_to_pulsewidth(angle):
    return int(500 + (angle / 180.0) * 2000)

def set_servo_angle(pin, angle, min_angle, max_angle):
    """Đặt góc cho 1 servo, trả về góc đã bị kẹp (clamped)."""
    clamped_angle = max(min_angle, min(angle, max_angle))
    pulse_width = map_angle_to_pulsewidth(clamped_angle)
    
    if state.pi_gpio:
        state.pi_gpio.set_servo_pulsewidth(pin, pulse_width)
    
    return clamped_angle

def move_servo(pan_angle, tilt_angle):
    """Di chuyển cả 2 servo đến góc mong muốn."""
    if not state.pi_gpio:
        return
        
    state.current_servo_x = set_servo_angle(
        config.SERVO_X_PIN, pan_angle, 
        config.SERVO_X_MIN_ANGLE, config.SERVO_X_MAX_ANGLE
    )
    state.current_servo_y = set_servo_angle(
        config.SERVO_Y_PIN, tilt_angle, 
        config.SERVO_Y_MIN_ANGLE, config.SERVO_Y_MAX_ANGLE
    )

def move_servo_home():
    """Di chuyển servo về vị trí Home."""
    print(f"[SERVO] Moving to Home position (X: {config.SERVO_X_HOME}°, Y: {config.SERVO_Y_HOME}°)")
    move_servo(config.SERVO_X_HOME, config.SERVO_Y_HOME)

def stop_hardware():
    print("[HARDWARE] Starting cleanup...")
    try:
        if state.pi_gpio:
            print("[PIGPIO] Disabling servo and disconnecting.")
            state.pi_gpio.set_servo_pulsewidth(config.SERVO_X_PIN, 0)
            state.pi_gpio.set_servo_pulsewidth(config.SERVO_Y_PIN, 0)
            state.pi_gpio.stop()
            state.pi_gpio = None
            print("[PIGPIO] Cleanup complete.")
    except Exception as e:
        print(f"[PIGPIO ERROR] {e}")

    try:
        stop_dht()   
    except Exception:
        pass

    # ==== CLEANUP GPIO ====
    try:
        GPIO.cleanup()
        led.close()
        print("[GPIO] Cleanup complete.")
    except Exception as e:
        print(f"[GPIO CLEANUP ERROR] {e}")

    print("[HARDWARE] Cleanup complete.")
