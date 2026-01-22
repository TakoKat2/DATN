# mqtt_client.py
import paho.mqtt.client as mqtt
from threading import Thread
import time
import json
import datetime
import config
import state
import notifications
import hardware
import board
import adafruit_dht

dht_sensor = None
mqtt_client = None  # module-level để thread publish sử dụng
DHT_GPIO = board.D17

try:
    dht_sensor = adafruit_dht.DHT22(DHT_GPIO)
    print(f"[DHT] Initialized DHT22 on pin: {config.DHT_PIN}")
except (AttributeError, ValueError):
    print(f"[DHT INIT ERROR] Invalid pin: {config.DHT_PIN}")
except Exception as e:
    print(f"[DHT INIT ERROR] Unable to initialize sensor: {e}")
    
def stop_dht():
    global dht_sensor
    if dht_sensor is not None:
        try:
            dht_sensor.exit()
            print("[DHT] Sensor cleanup complete.")
        except Exception as e:
            print(f"[DHT CLEANUP ERROR] {e}")
        finally:
            dht_sensor = None

def reset_fire_alarm():
    """Reset lại hệ thống báo cháy."""
    state.fire_detected = False
    state.stop_all_flag = False
    hardware.activate_buzzer(False)
    notifications.send_telegram_alert("Fire alarm disabled and system restored.")
    print("Fire alarm reset — system operating normally.")

def str_to_bool(value):

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 't', 'y', 'yes', 'on')
    if isinstance(value, (int, float)):
        return value != 0
    return False

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode().strip()
    print(f"[MQTT DEBUG] Topic: {topic} | Raw Payload: '{payload}'")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        print(f"[MQTT ERROR] Invalid JSON format: {e}")
        return

    if "fire_alarm_enabled" in data:

        new_state = str_to_bool(data["fire_alarm_enabled"])
        
        if state.fire_system_enabled != new_state:
            state.fire_system_enabled = new_state
            if state.fire_system_enabled:
                print("==> ACTION: Fire Alarm System ENABLED")
            else:
                print("==> ACTION: Fire Alarm System DISABLED")
                reset_fire_alarm()

    if "security_alarm_enabled" in data:
        new_state = str_to_bool(data["security_alarm_enabled"])
        
        if state.security_system_enabled != new_state:
            state.security_system_enabled = new_state
            print(f"==> ACTION: Security System switched to: {'ENABLED' if new_state else 'DISABLED'}")

    print(f"[STATUS] Fire: {state.fire_system_enabled} | Security: {state.security_system_enabled}")

def publish_alarm_event(message, alert_type="general"):
    """
    Publish cảnh báo lên MQTT topic ALARM.
    
    Args:
        message (str): Nội dung chi tiết (VD: "Phát hiện lửa", "Có người đột nhập").
        alert_type (str): Loại cảnh báo (VD: "fire", "intruder", "warning"). Mặc định là "general".
    """
    global mqtt_client
    if mqtt_client is None:
        print(f"[MQTT ALARM] Client not ready yet, skipping publish: {message}")
        return

    payload = {
        "type": alert_type,
        "message": message,
        # "timestamp": datetime.datetime.utcnow().isoformat()
    }

    try:
        # QoS=2 để đảm bảo tin nhắn quan trọng được gửi đi chính xác
        mqtt_client.publish(
            config.MQTT_ALARM_TOPIC,
            json.dumps(payload),
            qos=2,
            retain=False
        )
        print(f"[MQTT ALARM] Published -> {config.MQTT_ALARM_TOPIC}: {json.dumps(payload)}")
    except Exception as e:
        print(f"[MQTT ALARM ERROR] Failed to publish alarm: {e}")

def publish_dht_reading(temp, hum, timestamp):
    """Publish dữ liệu DHT lên MQTT dạng JSON."""
    global mqtt_client
    if mqtt_client is None:
        print("[MQTT DHT] Client not ready yet, skipping publish")
        return

    payload = {
        "temperature": None if temp is None else round(temp, 2),
        "humidity": None if hum is None else round(hum, 2),
        # "timestamp": timestamp.isoformat()
    }
    try:
        mqtt_client.publish(
            config.MQTT_DHT_TOPIC,
            json.dumps(payload),
            qos=1,
            retain=False
        )
        print(f"[MQTT DHT] Published -> {config.MQTT_DHT_TOPIC}: {payload}")
    except Exception as e:
        print("[MQTT DHT ERROR] Failed to publish DHT:", e)

def read_dht_once():
    """Đọc cảm biến DHT22 1 lần (return temp, hum or (None, None))."""
    global dht_sensor

    if dht_sensor is None:
        print("[DHT ERROR] Sensor not initialized.")
        return None, None
        
    try:
        temperature = dht_sensor.temperature
        humidity = dht_sensor.humidity

        return temperature, humidity
        
    except RuntimeError as error:
        print(f"[DHT] Sensor read failed: {error.args[0]}")
    except Exception as e:
        print("[DHT ERROR] Unknown error while reading DHT:", e)
    return None, None

def dht_loop():
    """Thread loop: đọc DHT và publish mỗi interval."""
    while True:
        try:
            temperature, humidity = read_dht_once()
            now = datetime.datetime.utcnow()

            if temperature is not None and humidity is not None:
                state.dht_temperature = temperature
                state.dht_humidity = humidity
                state.dht_last_update = now
                state.dht_error_count = 0
                publish_dht_reading(temperature, humidity, now)
            else:
                # Không đọc được
                state.dht_error_count = getattr(state, "dht_error_count", 0) + 1
                print(f"[DHT] Read failed (count={state.dht_error_count})")
                if state.dht_error_count == 5:
                    notifications.send_telegram_alert(
                        "Warning: DHT22 sensor read failed repeatedly."
                    )
                    publish_alarm_event(
                        "DHT22 SENSOR READ ERROR",
                        alert_type="alarm_system"
                    )
            # Chờ interval (dùng sleep để đơn giản)
            time.sleep(config.DHT_PUBLISH_INTERVAL)
        except Exception as e:
            print("[DHT LOOP ERROR]", e)
            # tránh crash vòng lặp
            time.sleep(5)

def start_dht_thread():
    """Khởi chạy thread DHT"""
    t_dht = Thread(target=dht_loop, daemon=True)
    t_dht.start()
    print(f"[DHT] DHT thread started (GPIO {config.DHT_PIN})")

def start_mqtt():
    """Khởi tạo, kết nối và chạy luồng MQTT."""
    global mqtt_client
    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
    mqtt_client.on_message = on_message

    try:
        # Cấu hình SSL/TLS
        mqtt_client.tls_set(
            ca_certs=config.MQTT_CA_CERT,
            certfile=None,
            keyfile=None,
        )
        mqtt_client.tls_insecure_set(False)

        mqtt_client.connect(
            config.MQTT_BROKER_URL,
            config.MQTT_PORT,
            60
        )
        print(f"[MQTT] Securely connected to {config.MQTT_BROKER_URL}:{config.MQTT_PORT}")
        
        publish_alarm_event(
            "MQTT system started successfully!",
            alert_type="alarm_system"
        )

        mqtt_client.subscribe(config.MQTT_SYSTEM_TOPIC)
        print(f"[MQTT] Subscribed to: {config.MQTT_SYSTEM_TOPIC}")

        # Bắt đầu thread DHT sau khi client đã tạo
        if dht_sensor is not None:
            start_dht_thread()
        else:
            print("[DHT] Sensor initialization failed. Thread will not start.")

        # Chạy vĩnh viễn trong một luồng riêng
        Thread(
            target=mqtt_client.loop_forever,
            daemon=True
        ).start()

    except Exception as e:
        print(f"[MQTT ERROR] {e}")
