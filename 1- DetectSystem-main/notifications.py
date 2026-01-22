# notifications.py
import requests
import config


def send_telegram_alert(message):
    """Gửi tin nhắn cảnh báo"""
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
    data = {"chat_id": config.CHAT_ID, "text": message}
    try:
        requests.post(url, data=data, timeout=5)
        print(f"[TELEGRAM] Alert sent: {message}")
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")
        from mqtt_client import publish_alarm_event 
        publish_alarm_event("TELEGRAM MESSAGE SEND ERROR", alert_type="alarm_system")

def send_telegram_video(video_path, caption):
    """Gửi video qua Telegram"""
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendVideo"
    try:
        with open(video_path, 'rb') as video:
            files = {'video': video}
            data = {"chat_id": config.CHAT_ID, "caption": caption}
            requests.post(url, data=data, files=files, timeout=30)
            print(f"[TELEGRAM] Video sent: {video_path}")
    except Exception as e:
        print(f"[TELEGRAM VIDEO ERROR] {e}")
        from mqtt_client import publish_alarm_event 
        publish_alarm_event("TELEGRAM VIDEO SEND ERROR", alert_type="alarm_system")
