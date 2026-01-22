# camera.py
import time
import cv2
import state
import config
import recorder
from picamera2 import Picamera2
from libcamera import Transform
from mqtt_client import publish_alarm_event  # Import alarm function

def camera_thread():
    """Camera thread: captures frames and updates shared state."""
    picam2 = Picamera2()
    cam_config = picam2.create_preview_configuration(
        main={"size": (config.FRAME_WIDTH, config.FRAME_HEIGHT), "format": "RGB888"},
        transform=Transform(hflip=True, vflip=False),
        buffer_count=4,
        controls={
            "AwbEnable": True,
            "AeEnable": True,
            "Sharpness": 1.5,
            "Contrast": 1.2,
            "Brightness": 0.0,
            "Saturation": 1.3,
            "NoiseReductionMode": 3,
        },
    )
    picam2.configure(cam_config)
    picam2.start()
    print("[CAMERA] Camera thread started.")

    while True:
        try:
            frame = picam2.capture_array()
            state.frame_counter += 1

            # Update shared frame (for YOLO)
            with state.frame_lock:
                state.latest_frame = frame

            # Write video if recording is enabled
            if state.recording and state.video_writer is not None:
                state.video_writer.write(frame)
                recorder.check_recording_alerts()

            # Provide frame for web streaming
            ret, jpeg = cv2.imencode(".jpg", frame)
            if ret:
                state.streaming_output.set_frame(jpeg.tobytes())

            time.sleep(0.03)  # ~30 fps

        except Exception as e:
            print(f"[CAMERA ERROR] {e}")
            publish_alarm_event(
                "CAMERA SYSTEM ERROR",
                alert_type="alarm_system"
            )
            time.sleep(1)
