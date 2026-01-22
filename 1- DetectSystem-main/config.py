# config.py
# ========================== MQTT CONFIG ==========================
MQTT_BROKER_URL = "p6ff1523.ala.asia-southeast1.emqxsl.com"
MQTT_PORT = 8883
MQTT_USERNAME = "admin"
MQTT_PASSWORD = "admin123"
MQTT_FIRE_TOPIC = "/system/fire_mode"
MQTT_SECURITY_TOPIC = "/system/security_mode"
MQTT_ALARM_TOPIC = "system/alarm"
MQTT_SYSTEM_TOPIC = "system/config/state"
MQTT_DHT_TOPIC = "system/sensor"
MQTT_CA_CERT = "ca.crt" # Đường dẫn đến file cert

# ========================== TELEGRAM CONFIG ==========================
BOT_TOKEN = "8306486016:AAGjxb8sCAWStrSqkXzN7vG8tYAP2EkvYQg"
CHAT_ID = "6980193088"

# ========================== YOLO CONFIG ==========================
YOLO_MODEL_PATH = "best.onnx"
OBJECTS_TO_DETECT = [0]  # 0: face, 1: fire, 2: person
FIRE_CLASS_ID = 1 # 🔹 CHỈNH ID CỦA LỚP "FIRE"
PERSON_CLASS_ID = 2 # 🔹 CHỈNH ID CỦA LỚP "PERSON"
FACE_CLASS_ID = 0 # 🔹 CHỈNH ID CỦA LỚP "FACE"

# ========================== CAMERA & FRAME ==========================
FRAME_WIDTH = 640
FRAME_HEIGHT = 360
FRAME_CX = FRAME_WIDTH // 2
FRAME_CY = FRAME_HEIGHT // 2

# ========================== HARDWARE PINS ==========================
SERVO_Y_PIN = 12
SERVO_X_PIN = 13
LED_PIN = 23
BUZZER_PIN = 24
DHT_PIN = 17

# ========================== SENSOR DATA ==========================
DHT_PUBLISH_INTERVAL = 30   

# ========================== SERVO CONTROL ==========================
SERVO_Y_MIN_ANGLE = 40
SERVO_Y_MAX_ANGLE = 100
SERVO_X_MIN_ANGLE = 0
SERVO_X_MAX_ANGLE = 180
SERVO_Y_HOME = 50
SERVO_X_HOME = 70
PAN_GAIN = 0.05
TILT_GAIN = 0.05
DEAD_ZONE_X = 5
DEAD_ZONE_Y = 5

PAN_KP  = 0.036
PAN_KD  = 0.009

TILT_KP = 0.042
TILT_KD = 0.011

MAX_PAN_STEP  = 3.5    # độ / frame
MAX_TILT_STEP = 3

# ========================== SYSTEM LOGIC ==========================
TAIL_LENGTH = 10           # Số giây ghi thêm sau khi mất dấu
FIRE_AUTO_RESET_DELAY = 60 # Số giây không thấy lửa thì tự reset
TIME_TO_RETURN_HOME = 4.0  # Số giây không thấy người thì về Home

# ========================== WEB SERVER ==========================
STREAM_PORT = 8000