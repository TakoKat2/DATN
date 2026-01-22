# main.py
import os
os.environ["LIBCAMERA_LOG_LEVELS"] = "FATAL" 

import logging
from threading import Thread
from ultralytics import YOLO

import config
import hardware
import mqtt_client
import camera
import detection
import web_stream
import wifi_manager
from mqtt_client import publish_alarm_event # Import hàm alarm

def main():
    print("Starting Camera and YOLO...")

    print("[YOLO] Loading shared YOLO model...")
    try:
        shared_model = YOLO(config.YOLO_MODEL_PATH)
        print("[YOLO] Model loaded successfully.")
    except Exception as e:
        print(f"[YOLO ERROR] Model loaded failed: {e}")
        return 

    # 2. Khởi tạo phần cứng
    hardware.init_hardware()
    
    # 3. Khởi động MQTT (đã chạy trong thread riêng)
    mqtt_client.start_mqtt()

    # 4. Định nghĩa các luồng
    print("Starting background threads...")
    t_cam = Thread(target=camera.camera_thread, daemon=True)
    t_fire = Thread(target=detection.fire_detection_thread, args=(shared_model,), daemon=True)
    t_person = Thread(target=detection.person_detection_thread, args=(shared_model,), daemon=True)

    # 5. Bắt đầu các luồng
    t_cam.start()
    t_fire.start()
    t_person.start()

    # 6. Bắt đầu Web Server (chạy ở luồng chính, blocking)
    address = ('0.0.0.0', config.STREAM_PORT)
    server = web_stream.StreamingServer(address, web_stream.StreamingHandler)
    
    print("==================================================")
    print(f"Server started. Open browser and go to:")
    print(f"http:172.20.10.2:{config.STREAM_PORT}")
    print("==================================================")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        
    finally:
        # Dọn dẹp
        hardware.stop_hardware()
        print("System shut down cleanly.")
        publish_alarm_event("SHUT DOWN THE SYSTEM", alert_type="alarm_system")

if __name__ == "__main__":
    main()