# state.py
from threading import Condition, Lock
from datetime import datetime
import time


# --- System Flags ---
fire_system_enabled = True
security_system_enabled = True
stop_all_flag = False   # Cờ để dừng mọi hoạt động (khi có cháy)
fire_detected = False

# --- Recording State ---
recording = False
last_person_time = 0
video_writer = None
current_filename = None
record_start_time = None       
last_behavior_alert_time = None 
sent_stranger_alert = False     

# --- Frame & Camera ---
frame_lock = Lock()    
latest_frame = None     # Frame mới nhất từ camera
frame_counter = 0   

# --- Hardware State ---
current_servo_y = 0     # Vị trí servo hiện tại
current_servo_x = 0
pi_gpio = None          # Đối tượng pigpio instance
prev_cx = 0
prev_cy = 0
prev_error_x = 0
prev_error_y = 0
prev_time = time.time()

# --- DHT22 ---
dht_temperature = None   # nhiệt độ tính bằng °C (float)
dht_humidity = None      # độ ẩm RH% (float)
dht_last_update = None   # timestamp lần đọc cuối (datetime hoặc epoch)
dht_error_count = 0      # đếm lỗi liên tiếp

# --- Streaming ---
class StreamingOutput:
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def set_frame(self, frame_bytes):
        with self.condition:
            self.frame = frame_bytes
            self.condition.notify_all()

streaming_output = StreamingOutput()