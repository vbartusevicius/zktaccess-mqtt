import logging
import paho.mqtt.client as mqtt

import settings

log = logging.getLogger(__name__)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        log.info("Connected successfully to MQTT Broker")
    else:
        log.error(f"Failed to connect to MQTT Broker, return code {rc}")

def on_disconnect(client, userdata, rc, properties=None):
    if rc == 0:
        log.info("Gracefully disconnected from MQTT Broker")
    else:
        log.warning(f"Unexpectedly disconnected from MQTT Broker with result code {rc}. Reconnection might be attempted by loop.")

def on_publish(client, userdata, mid, properties=None, reason_codes=None):
    log.debug(f"Published message ID: {mid}")
    pass

def setup_mqtt_client(client_id: str) -> Optional[mqtt.Client]:
    log.info("Setting up MQTT client...")
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    except Exception as e:
        log.exception(f"Error creating MQTT client instance: {e}", exc_info=True)
        return None

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish

    if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
        try:
            client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
            log.info("MQTT Username/Password configured.")
        except Exception as e:
            log.exception(f"Error setting MQTT username/password: {e}", exc_info=True)
            return None

    # TODO: Add TLS configuration via environment variables if needed
    
    try:
        log.info(f"Connecting to MQTT broker at {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}...")
        client.connect_async(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, keepalive=60)
    except Exception as e:
        log.exception(f"Error initiating connection to MQTT broker: {e}", exc_info=True)
        return None

    return client

def publish_message(client: mqtt.Client, topic: str, payload: str, qos: int = 1, retain: bool = False) -> bool:
    if not client:
        log.error(f"Cannot publish to {topic}, MQTT client is invalid.")
        return False

    if not client.is_connected():
        log.warning(f"MQTT client not connected, message to {topic} will be queued.")

    try:
        result = client.publish(topic, payload, qos=qos, retain=retain)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            return True
        else:
            log.error(f"-> Failed to queue message for {topic} (Error code: {result.rc})")
            return False
    except Exception as e:
        log.exception(f"Error during MQTT publish attempt to {topic}: {e}", exc_info=True)
        return False