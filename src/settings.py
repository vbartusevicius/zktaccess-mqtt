import os

ZKT_DEVICE_IP = os.getenv("DEVICE_IP", "192.168.1.201")
ZKT_DEVICE_PORT = int(os.getenv("DEVICE_PORT", 4370))
ZKT_DEVICE_PASSWORD = os.getenv("DEVICE_PASSWORD", "")
ZKT_DEVICE_MODEL = os.getenv("DEVICE_MODEL", "C3")

# --- MQTT Broker Settings ---
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", None)
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", None)

# --- Application Settings ---
POLLING_INTERVAL_SECONDS = int(os.getenv("POLLING_INTERVAL_SECONDS", 60))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

HA_DISCOVERY_PREFIX = os.getenv("HA_DISCOVERY_PREFIX", "homeassistant")

HA_DEVICE_NAME = os.getenv("HA_DEVICE_NAME", f"ZKTeco {ZKT_DEVICE_MODEL} Controller")
HA_DEVICE_MANUFACTURER = os.getenv("HA_DEVICE_MANUFACTURER", "ZKTeco")
HA_DEVICE_SW_VERSION = os.getenv("HA_DEVICE_SW_VERSION", "zkt_mqtt_bridge_1.0")
TIME_ZONE = os.getenv("TIME_ZONE", "UTC")
