# wifi_manager.py
import subprocess
import os
import time
from mqtt_client import publish_alarm_event  # Import hàm alarm

WPA_SUPPLICANT_FILE = "/etc/wpa_supplicant/wpa_supplicant.conf"

def save_wifi_config(ssid, password):
    """
    Kết nối Wifi sử dụng NetworkManager (nmcli).
    Không cần reboot.
    """
    print(f"[WIFI] Connecting to: {ssid}")
    
    try:
        # Lệnh: nmcli device wifi connect "SSID" password "PASSWORD"
        command = [
            "sudo", "nmcli", "device", "wifi", "connect", ssid, "password", password
        ]
        
        # Chạy lệnh
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("[WIFI] Connected successfully.")
            publish_alarm_event(f"WIFI CONNECTED: {ssid}", alert_type="alarm_system")
            return True, "Connection successful!"
        else:
            error_msg = result.stderr.strip()
            print(f"[WIFI ERROR] {error_msg}")
            publish_alarm_event("WIFI CONNECTION ERROR", alert_type="alarm_system")
            return False, error_msg

    except Exception as e:
        print(f"[WIFI ERROR] {e}")
        return False, str(e)

def reboot_system():
    """Khởi động lại Raspberry Pi"""
    print("[SYSTEM] Rebooting...")
    os.system("sudo reboot")
