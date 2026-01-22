# detection.py
import time
import cv2
import numpy as np
import state
import config
import hardware
import notifications
import recorder
from mqtt_client import reset_fire_alarm # Import hàm reset
from mqtt_client import publish_alarm_event # Import hàm alarm
import os
import psutil

class PerformanceMonitor:
    def __init__(self):
        self.prev_frame_time = 0
        self.new_frame_time = 0
        self.process = psutil.Process(os.getpid())

    def get_cpu_temp(self):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return float(f.read()) / 1000
        except:
            return 0.0

    def get_system_stats(self):
        return psutil.cpu_percent(interval=None), self.process.memory_info().rss / 1024 / 1024

    def draw_stats(self, frame, infer_time_ms):
        
        self.new_frame_time = time.time()
        diff = self.new_frame_time - self.prev_frame_time
        fps = 1 / diff if diff > 0 else 0
        self.prev_frame_time = self.new_frame_time
       
        temp = self.get_cpu_temp()
        cpu, ram = self.get_system_stats()

        lines = [
            f"Infer: {infer_time_ms:.1f} ms",
            f"FPS: {int(fps)}",
            f"CPU: {cpu}percent | RAM: {ram:.0f}MB",
            f"Temp: {temp:.1f} C"
        ]

        for i, line in enumerate(lines):
            y = 30 + i * 30
            cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
            cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        return frame

def calculate_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    unionArea = float(boxAArea + boxBArea - interArea)
    if unionArea == 0:
        return 0
    return interArea / unionArea


def fire_detection_thread(model):
    print("[YOLO] Fire detection thread started.")
    last_detect_frame_fire = 0
    last_fire_seen_time = 0
    # Biến đếm số lần phát hiện lửa liên tục
    consecutive_fire_detections = 0
    # Ngưỡng kích hoạt (5 lần liên tục)
    FIRE_CONFIRMATION_THRESHOLD = 5

    while True:
        if not state.fire_system_enabled:
            time.sleep(1)
            continue

        if state.frame_counter - last_detect_frame_fire < 10:
            time.sleep(0.05)
            continue
        
        last_detect_frame_fire = state.frame_counter

        # Lấy frame
        with state.frame_lock:
            if state.latest_frame is not None:
                frame_copy = state.latest_frame.copy()
            else:
                frame_copy = None

        if frame_copy is None:
            continue

        try:
            results = model(frame_copy, verbose=False)
            boxes = results[0].boxes

            is_fire_in_frame = False
            if len(boxes) > 0:
                detected_ids = boxes.cls.tolist()
                if any(int(cls) == config.FIRE_CLASS_ID for cls in detected_ids):
                    is_fire_in_frame = True
            
            if is_fire_in_frame:
                last_fire_seen_time = time.time()
                consecutive_fire_detections += 1 # Tăng biến đếm
                print(f"Fire detected, confirming... (Count: {consecutive_fire_detections}/{FIRE_CONFIRMATION_THRESHOLD})")
                
                # Chỉ kích hoạt khi đếm đủ 5 lần
                if consecutive_fire_detections >= FIRE_CONFIRMATION_THRESHOLD:
                    if not state.fire_detected:
                        print(f"FIRE DETECTED ({FIRE_CONFIRMATION_THRESHOLD} consecutive) — Activate the fire alarm!")
                        state.fire_detected = True
                        state.stop_all_flag = True # Dừng mọi hoạt động khác
                        hardware.activate_buzzer(True)
                        hardware.led.blink(on_time=0.2, off_time=0.2, background=True)
                        notifications.send_telegram_alert("🔥🔥🔥 FIRE FIRE FIRE! 🔥🔥🔥")
                        publish_alarm_event("FIRE DETECTED!", alert_type="alarm_fire")
                    else:
                        print("Fire still detected (confirmed)...")
            
            else:
                # --- THÊM MỚI ---
                # Không thấy lửa, reset bộ đếm
                if consecutive_fire_detections > 0:
                    print(f"Fire not seen, resetting consecutive to 0.")
                consecutive_fire_detections = 0

                if state.fire_detected:
                    time_since_last_fire = time.time() - last_fire_seen_time
                    
                    if time_since_last_fire > config.FIRE_AUTO_RESET_DELAY:
                        print(f"[AUTO-RESET] No fire detected in {config.FIRE_AUTO_RESET_DELAY} seconds. Turn off the alarm.")
                        reset_fire_alarm() # Gọi hàm reset
                        hardware.led.off()
                        publish_alarm_event(f"AUTOMATICALLY TURN OFF THE ALARM AFTER {config.FIRE_AUTO_RESET_DELAY}s", alert_type="alarm_fire")
                    else:
                        print(f"Fire not seen. Auto-reset in {config.FIRE_AUTO_RESET_DELAY - time_since_last_fire:.0f}s...")

        except Exception as e:
            print(f"[FIRE DETECT ERROR] {e}")
            publish_alarm_event("FIRE DETECT ERROR", alert_type="alarm_system")

def person_detection_thread(model):
    print(f"\n[YOLO] Person detection thread started.")
    monitor = PerformanceMonitor()
    
    # Biến lưu thời điểm cuối cùng nhìn thấy người
    # Khởi tạo bằng thời gian hiện tại để tránh về Home ngay lập tức khi vừa bật
    last_seen_time = time.time() 

    while True:
        # 1. Kiểm tra trạng thái hệ thống
        if state.stop_all_flag: 
            time.sleep(1)
            continue
        
        if not state.security_system_enabled:
            hardware.move_servo_home()
            recorder.stop_recording()
            hardware.led.off()
            time.sleep(1)
            continue

        # 2. Lấy frame
        with state.frame_lock:
            frame_copy = state.latest_frame.copy() if state.latest_frame is not None else None

        if frame_copy is None:
            time.sleep(0.02)
            continue

        try:
            t_start = time.time()
            # 3. Detect
            results = model(frame_copy, verbose=False, imgsz=320, conf=0.4)
            
            t_end = time.time()
            infer_time = (t_end - t_start) * 1000
            
            frame_copy = monitor.draw_stats(frame_copy, infer_time)
            
            boxes = results[0].boxes
            target_box = None
            max_area = 0

            # 4. Tìm người
            for box in boxes:
                cls_id = int(box.cls[0])
                if cls_id in [config.PERSON_CLASS_ID, config.FACE_CLASS_ID]: 
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = map(int, xyxy)
                    area = (x2 - x1) * (y2 - y1)
                    
                    if area > max_area:
                        max_area = area
                        target_box = xyxy

            # 5. Logic điều khiển
            if target_box is not None:
                # [QUAN TRỌNG] Cập nhật thời gian vừa nhìn thấy người
                last_seen_time = time.time() 

                x1, y1, x2, y2 = map(int, target_box)
                box_cx = (x1 + x2) / 2
                box_cy = (y1 + y2) / 2
                
                box_cx = 0.7 * state.prev_cx + 0.3 * box_cx
                box_cy = 0.7 * state.prev_cy + 0.3 * box_cy
                state.prev_cx = box_cx
                state.prev_cy = box_cy

                now = time.time()
                dt = max(now - state.prev_time, 0.001)

                error_x = box_cx - config.FRAME_CX
                error_y = box_cy - config.FRAME_CY

                if abs(error_x) < config.DEAD_ZONE_X:
                    error_x = 0
                if abs(error_y) < config.DEAD_ZONE_Y:
                    error_y = 0

                de_x = (error_x - state.prev_error_x) / dt
                de_y = (error_y - state.prev_error_y) / dt

                delta_x = config.PAN_KP * error_x + config.PAN_KD * de_x
                delta_y = config.TILT_KP * error_y + config.TILT_KD * de_y

                delta_x = max(-config.MAX_PAN_STEP, min(config.MAX_PAN_STEP, delta_x))
                delta_y = max(-config.MAX_TILT_STEP, min(config.MAX_TILT_STEP, delta_y))

                new_x = max(config.SERVO_X_MIN_ANGLE,
                            min(config.SERVO_X_MAX_ANGLE, state.current_servo_x + delta_x))
                new_y = max(config.SERVO_Y_MIN_ANGLE,
                            min(config.SERVO_Y_MAX_ANGLE, state.current_servo_y - delta_y))

                if abs(new_x - state.current_servo_x) > 0.3 or abs(new_y - state.current_servo_y) > 0.3:
                    hardware.move_servo(new_x, new_y)

                state.prev_error_x = error_x
                state.prev_error_y = error_y
                state.prev_time = now
                # Logic ghi hình
                state.last_person_time = time.time()
                if not state.recording:
                    recorder.start_recording(frame_copy)
                    hardware.led.blink(on_time=0.5, off_time=0.5, background=True)

            else:
                # --- [SỬA ĐỔI] LOGIC MẤT DẤU THEO GIÂY ---
                time_elapsed = time.time() - last_seen_time
                state.prev_error_x = 0
                state.prev_error_y = 0
                state.prev_time = time.time()
                if time_elapsed > config.TIME_TO_RETURN_HOME:
                    # Kiểm tra xem đã ở Home chưa
                    dist_to_home_x = abs(state.current_servo_x - config.SERVO_X_HOME)
                    dist_to_home_y = abs(state.current_servo_y - config.SERVO_Y_HOME)
                    
                    if dist_to_home_x > 2 or dist_to_home_y > 2:
                        print(f"[TRACK] Lost target for {time_elapsed:.1f}s -> Returning Home.")
                        hardware.move_servo_home()
                        
                        # Cập nhật lại thời gian để không spam lệnh move_servo_home liên tục
                        # (Nó sẽ đợi thêm 4s nữa mới gửi lệnh tiếp nếu vẫn chưa thấy ai - dù thực tế servo đã về home rồi)
                        last_seen_time = time.time() 

            # Dừng ghi hình (Tail)
            if state.recording and (time.time() - state.last_person_time > config.TAIL_LENGTH):
                recorder.stop_recording()
                hardware.led.off()

        except Exception as e:
            print(f"[TRACKING ERROR] {e}")
            try: hardware.led.off()
            except: pass