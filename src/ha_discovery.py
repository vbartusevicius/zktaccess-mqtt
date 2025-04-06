import json
import logging
from typing import Any

import settings
import mqtt_handler
from zkt_handler import DeviceDefinition

log = logging.getLogger(__name__)

def safe_get_attr(obj: Any, attr_name: str, default: Any = None) -> Any:
    return getattr(obj, attr_name, default) if obj else default

def get_device_info(device_definition: DeviceDefinition) -> dict:
    info = {
        "identifiers": [device_definition.parameters.serial_number],
        "name": settings.HA_DEVICE_NAME,
        "manufacturer": settings.HA_DEVICE_MANUFACTURER,
        "model": settings.ZKT_DEVICE_MODEL,
        "sw_version": settings.HA_DEVICE_SW_VERSION,
    }
    ip_address = None
    if device_definition and device_definition.parameters:
        ip_address = safe_get_attr(device_definition.parameters, 'ip_address')
    if ip_address:
        info["connections"] = [["ip", str(ip_address)]]

    return info

def publish_discovery_messages(
    mqtt_client: mqtt_handler.mqtt.Client,
    device_definition: DeviceDefinition,
    ha_identifier: str
):
    if not settings.HA_ENABLED:
        log.info("Home Assistant discovery is disabled in settings.")
        return

    if not mqtt_client or not mqtt_client.is_connected():
        log.warning("MQTT client not connected; discovery messages might be queued or fail.")

    discovery_prefix = settings.HA_DISCOVERY_PREFIX
    device_info = get_device_info(device_definition)
    base_component_topic = f"{discovery_prefix}/{{component}}/{device_definition.parameters.serial_number}"

    for door in device_definition.doors:
        try:
            door_id = int(safe_get_attr(door, 'number', -1))
            if door_id < 0: raise ValueError("Missing/invalid door number")
            door_name = f"Door {door_id}"
            unique_id = f"{ha_identifier}_door_{door_id}"
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
        except (TypeError, ValueError, AttributeError) as e: log.error(f"Invalid door data: {door}. Skip. Err: {e}", exc_info=True)

    for reader in device_definition.readers:
        try:
            reader_id = int(safe_get_attr(reader, 'number', -1))
            if reader_id < 0: raise ValueError("Missing/invalid reader number")
            reader_name = f"Reader {reader_id}"
            unique_id = f"{ha_identifier}_reader_{reader_id}_event"
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
                "subtype": f"reader_{reader_id}", 
                "payload_type": "json",
                "value_template": "{{ value_json.event_type }}",
                "event_types": [ 
                    "card_scan_success", 
                    "card_scan_denied", 
                    "card_scan_invalid",
                    "pin_success", 
                    "pin_denied", 
                    "fingerprint_success", 
                    "fingerprint_denied",
                    "door_button", 
                    "door_open", 
                    "door_close", 
                    "other" 
                ], 
                "qos": 1 
            }
            config_topic = base_component_topic.format(component='event') + f"/{object_id}/config"
            log.info(f"  Publishing config for Reader Event {reader_id}: {config_topic}")
            payload_json = json.dumps(config_payload)
            mqtt_handler.publish_message(mqtt_client, config_topic, payload_json, qos=1, retain=True)
        except (TypeError, ValueError, AttributeError) as e: log.error(f"Invalid reader data: {reader}. Skip. Err: {e}", exc_info=True)

    for relay in device_definition.relays:
        try:
            relay_num = int(safe_get_attr(relay, 'number', -1))
            relay_group_enum = safe_get_attr(relay, 'group')
            if relay_num < 0 or not relay_group_enum: raise ValueError("Missing/invalid relay number or group")
            relay_group_name = safe_get_attr(relay_group_enum, 'name', 'unknown').lower() # 'lock' or 'aux'
            unique_id = f"{ha_identifier}_relay_{relay_group_name}_{relay_num}"
            object_id = f"relay_{relay_group_name}_{relay_num}"
            entity_name = f"Relay {relay_group_name.capitalize()} {relay_num}"
            entity_topic_prefix = base_component_topic.format(component='switch') + f"/{object_id}"

            config_payload = {
                "name": entity_name,
                "unique_id": unique_id,
                "state_topic": f"{entity_topic_prefix}/state",
                "payload_on": "ON", 
                "payload_off": "OFF",
                "device": device_info,
                "qos": 1,
                "icon": "mdi:electric-switch" if relay_group_name == 'lock' else "mdi:electric-switch-closed"
            }
            config_topic = f"{entity_topic_prefix}/config"
            log.info(f"  Publishing config for Relay {relay_group_name.capitalize()} {relay_num}: {config_topic}")
            payload_json = json.dumps(config_payload)
            mqtt_handler.publish_message(mqtt_client, config_topic, payload_json, qos=1, retain=True)

        except (TypeError, ValueError, AttributeError) as e:
            log.error(f"Invalid or incomplete relay data: {relay}. Skipping. Error: {e}", exc_info=True)
            continue

    for aux_input in device_definition.aux_inputs:
        try:
            aux_id = int(safe_get_attr(aux_input, 'number', -1))
            if aux_id < 0: raise ValueError("Missing or invalid aux input number")
            aux_name = f"Aux Input {aux_id}"

            unique_id = f"{ha_identifier}_aux_input_{aux_id}"
            object_id = f"aux_input_{aux_id}"
            entity_topic_prefix = base_component_topic.format(component='binary_sensor') + f"/{object_id}"

            config_payload = {
                "name": aux_name,
                "unique_id": unique_id,
                "state_topic": f"{entity_topic_prefix}/state",
                "payload_on": "ON", 
                "payload_off": "OFF", 
                "device_class": "problem", 
                "device": device_info,
                "qos": 1
            }
            config_topic = f"{entity_topic_prefix}/config"
            log.info(f"  Publishing config for Aux Input {aux_id}: {config_topic}")
            payload_json = json.dumps(config_payload)
            mqtt_handler.publish_message(mqtt_client, config_topic, payload_json, qos=1, retain=True)

        except (TypeError, ValueError, AttributeError) as e:
            log.error(f"Invalid or incomplete aux input data: {aux_input}. Skipping. Error: {e}", exc_info=True)
            continue

    log.info("Finished publishing discovery messages.")