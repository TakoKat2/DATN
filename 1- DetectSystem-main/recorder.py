# recorder.py
import cv2
import os
from datetime import datetime
import config
import state
import notifications
from mqtt_client import publish_alarm_event


# ==========================
#   START RECORDING
# ==========================
def start_recording(frame):
    """Bắt đầu ghi file video mới."""
    if state.video_writer is not None:
        print("[RECORDER] Already recording, skipping...")
        return

    folder = datetime.now().strftime('%Y-%m-%d')
    os.makedirs(folder, exist_ok=True)

    state.current_filename = f"{folder}/{datetime.now().strftime('%H-%M-%S')}.avi"
    h, w = frame.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'XVID')

    try:
        state.video_writer = cv2.VideoWriter(state.current_filename, fourcc, 20.0, (w, h))
        state.recording = True

        # Reset lại biến
        state.record_start_time = datetime.now()
        state.last_behavior_alert_time = None
        state.sent_stranger_alert = False

        print(f"[RECORDER] Start recording: {state.current_filename}")

    except Exception as e:
        print(f"[RECORDER ERROR] {e}")
        publish_alarm_event("RECORDING SYSTEM ERROR", alert_type="alarm_system")
        state.video_writer = None
        state.recording = False

# ==========================
#    CHECK ALERTS WHILE RECORDING
# ==========================
def check_recording_alerts():
    """Kiểm tra và gửi cảnh báo trong lúc đang ghi."""
    if not state.recording or state.record_start_time is None:
        return

    elapsed = (datetime.now() - state.record_start_time).total_seconds()

    if elapsed < 60:
        if not state.sent_stranger_alert:
            notifications.send_telegram_alert("WARNING: STRANGER DETECTED!")
            publish_alarm_event("STRANGER DETECTED WARNING", alert_type="alarm_security")
            state.sent_stranger_alert = True
        return

    if (
        state.last_behavior_alert_time is None or
        (datetime.now() - state.last_behavior_alert_time).total_seconds() >= 10
    ):
        notifications.send_telegram_alert("WARNING: ABNORMAL BEHAVIOR DETECTED!")
        publish_alarm_event("ABNORMAL BEHAVIOR DETECTED WARNING", alert_type="alarm_security")

        state.last_behavior_alert_time = datetime.now()

# ==========================
#   STOP RECORDING
# ==========================
def stop_recording():
    """Dừng ghi, xử lý file video, và gửi thông báo."""
    if state.video_writer is None:
        return

    print("[RECORDER] Stop recording...")

    video_path_to_check = state.current_filename

    # Giải phóng tài nguyên
    state.video_writer.release()
    state.video_writer = None
    state.recording = False
    state.current_filename = None

    try:
        cap = cv2.VideoCapture(video_path_to_check)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = frame_count / fps if fps and fps > 0 else 0
        cap.release()

        print(f"[DEBUG] Clip {video_path_to_check} duration is approximately {duration:.1f} seconds")

        if duration < 20:
            os.remove(video_path_to_check)
            print(f"[RECORDER] Clip {video_path_to_check} is only {duration:.1f}s — deleted.")

        elif duration < 60:
            notifications.send_telegram_video(video_path_to_check, "STRANGER DETECTION CLIP")
            publish_alarm_event("CLIP SENT VIA TELEGRAM", alert_type="alarm_security")
        else:
            notifications.send_telegram_video(video_path_to_check, "ABNORMAL BEHAVIOR DETECTION CLIP")
            publish_alarm_event("CLIP SENT VIA TELEGRAM", alert_type="alarm_security")

    except Exception as e:
        print(f"[VIDEO CHECK ERROR] {e}")
        publish_alarm_event("VIDEO CHECK SYSTEM ERROR", alert_type="alarm_system")
