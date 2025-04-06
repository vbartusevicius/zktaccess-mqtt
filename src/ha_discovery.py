import json
import logging

import settings
import mqtt_handler
from zkt_handler import DeviceDefinition

log = logging.getLogger(__name__)

def get_device_info(device: DeviceDefinition) -> dict:
    return {
        "identifiers": [device.parameters.serial_number],
        "name": settings.HA_DEVICE_NAME,
        "manufacturer": settings.HA_DEVICE_MANUFACTURER,
        "model": settings.ZKT_DEVICE_MODEL,
        "sw_version": settings.HA_DEVICE_SW_VERSION,
        "ip_address": device.parameters.ip_address,
    }

def publish_discovery_messages(mqtt_client, device: DeviceDefinition):
    log.info("Publishing Home Assistant MQTT discovery messages...")
    if not mqtt_client or not mqtt_client.is_connected():
        log.warning("MQTT client not connected or invalid; discovery messages might be queued or fail.")

    discovery_prefix = settings.HA_DISCOVERY_PREFIX
    device_info = get_device_info(device)
    base_component_topic = f"{discovery_prefix}/{{component}}/{device.parameters.serial_number}"

    for door in device.doors:
        try:
            door_id = int(door.id)
            door_name = door.name or f"Door {door_id}"
            unique_id = f"{device.parameters.serial_number}_door_{door_id}"
            object_id = f"door_{door_id}"
            entity_topic_prefix = base_component_topic.format(component='binary_sensor') + f"/{object_id}"

            config_payload = {
                "name": door_name,
                "unique_id": unique_id,
                "device_class": "door",
                "state_topic": f"{entity_topic_prefix}/state",
                "payload_on": "ON",
                "payload_off": "OFF",
                "device": device_info,
                "qos": 1
            }
            config_topic = f"{entity_topic_prefix}/config"
            log.info(f"  Publishing config for Door {door_id}: {config_topic}")
            payload_json = json.dumps(config_payload)
            mqtt_handler.publish_message(mqtt_client, config_topic, payload_json, qos=1, retain=True)

        except (TypeError, KeyError, ValueError) as e:
            log.error(f"Invalid door definition in HA_DOORS: {door}. Skipping. Error: {e}")
            continue

    for reader in device['readers']:
        try:
            reader_id = int(reader.get('id'))
            reader_name = reader.get('name', f"Reader {reader_id}")
            unique_id = f"{device.parameters.serial_number}_reader_{reader_id}_event"
            object_id = f"reader_{reader_id}_event"
            event_trigger_topic = base_component_topic.format(component='event') + f"/{object_id}/trigger"

            config_payload = {
                "name": f"{reader_name} Event",
                "unique_id": unique_id,
                "device": device_info,
                "device_class": "button",
                "automation_type": "trigger",
                "topic": event_trigger_topic,
                "type": "button_short_press",
                "subtype": "trigger",
                "payload_type": "json",
                "value_template": "{{ value_json.event_type }}",
                "event_types": [
                    "card_scan_success", "card_scan_denied", "card_scan_invalid",
                    "door_button",
                    "door_open", "door_close",
                    "other"
                ],
                "qos": 1,
                # "json_attributes_topic": event_trigger_topic, # Listen on same topic
                # "json_attributes_template": "{{ value_json | tojson }}", # Expose full payload
            }
            config_topic = base_component_topic.format(component='event') + f"/{object_id}/config"

            log.info(f"  Publishing config for Reader Event {reader_id}: {config_topic}")
            payload_json = json.dumps(config_payload)
            mqtt_handler.publish_message(mqtt_client, config_topic, payload_json, qos=1, retain=True)

        except (TypeError, KeyError, ValueError) as e:
            log.error(f"Invalid reader definition in HA_READERS: {reader}. Skipping. Error: {e}")
            continue

    log.info("Finished publishing discovery messages.")