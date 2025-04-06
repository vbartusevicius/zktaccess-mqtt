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

def build_state_topic(object_id: str, serial_number: str) -> str:
    return f"zkt_eco/{settings.ZKT_DEVICE_MODEL}/{serial_number}/{object_id}/state"

def publish_discovery_messages(
    mqtt_client: mqtt_handler.mqtt.Client,
    device_definition: DeviceDefinition,
    ha_identifier: str
):
    serial_number = device_definition.parameters.serial_number

    discovery_prefix = settings.HA_DISCOVERY_PREFIX
    device_info = get_device_info(device_definition)
    autoconfig_component_topic = f"{discovery_prefix}/{{component}}/{serial_number}"

    for door in device_definition.doors:
        try:
            door_id = int(safe_get_attr(door, 'number', -1))
            if door_id < 0: raise ValueError("Missing/invalid door number")
            door_name = f"Door {door_id}"
            unique_id = f"{ha_identifier}_door_{door_id}"
            object_id = f"door_{door_id}"
            
            config_payload = {
                "name": door_name, 
                "unique_id": unique_id, 
                "device_class": "door",
                "state_topic": build_state_topic(object_id, serial_number),
                "json_attributes_topic": build_state_topic(object_id, serial_number).replace('/state', '/attributes'),
                "payload_on": "ON", 
                "payload_off": "OFF",
                "device": device_info, 
                "qos": 1 
            }
            config_topic = autoconfig_component_topic.format(component='binary_sensor') + f"/{object_id}/config"
            payload_json = json.dumps(config_payload)

            mqtt_handler.publish_message(mqtt_client, config_topic, payload_json, qos=1, retain=True)
        except (TypeError, ValueError, AttributeError) as e: 
            log.error(f"Invalid door data: {door}. Skip. Err: {e}", exc_info=True)

    for reader in device_definition.readers:
        try:
            reader_id = int(safe_get_attr(reader, 'number', -1))
            if reader_id < 0: 
                raise ValueError("Missing/invalid reader number")
            reader_name = f"Reader {reader_id}"
            
            object_id = f"reader_{reader_id}_scan"
            config_payload_scan = {
                "name": f"{reader_name} Scan", 
                "unique_id": f"{ha_identifier}_reader_{reader_id}_scan", 
                "device": device_info,
                "automation_type": "trigger", 
                "state_topic": build_state_topic(object_id, serial_number),
                "json_attributes_topic": build_state_topic(object_id, serial_number),
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

            object_id = f"reader_{reader_id}_card"
            config_payload_card = {
                "name": f"{reader_name} Card", 
                "unique_id": f"{ha_identifier}_reader_{reader_id}_card", 
                "device": device_info,
                "state_topic": build_state_topic(object_id, serial_number),
                "value_template": "{{ value_json.card_id }}",
                "icon": "mdi:card-account-details",
                "json_attributes_topic": build_state_topic(object_id, serial_number),
                "qos": 1 
            }
            scan_config_topic = autoconfig_component_topic.format(component='event') + f"/{object_id}/config"
            scan_payload_json = json.dumps(config_payload_scan)

            mqtt_handler.publish_message(mqtt_client, scan_config_topic, scan_payload_json, qos=1, retain=True)
            
            card_config_topic = autoconfig_component_topic.format(component='sensor') + f"/{object_id}/config"
            card_payload_json = json.dumps(config_payload_card)

            mqtt_handler.publish_message(mqtt_client, card_config_topic, card_payload_json, qos=1, retain=True)
        except (TypeError, ValueError, AttributeError) as e:
            log.error(f"Invalid reader data: {reader}. Skip. Err: {e}", exc_info=True)

    for relay in device_definition.relays:
        try:
            relay_num = int(safe_get_attr(relay, 'number', -1))
            relay_group_enum = safe_get_attr(relay, 'group')
            if relay_num < 0 or not relay_group_enum: 
                raise ValueError("Missing/invalid relay number or group")
            relay_group_name = safe_get_attr(relay_group_enum, 'name', 'unknown').lower() # 'lock' or 'aux'
            unique_id = f"{ha_identifier}_relay_{relay_group_name}_{relay_num}"
            object_id = f"relay_{relay_group_name}_{relay_num}"
            entity_name = f"Relay {relay_group_name.capitalize()} {relay_num}"

            config_payload = {
                "name": entity_name,
                "unique_id": unique_id,
                "state_topic": build_state_topic(object_id, serial_number),
                "json_attributes_topic": build_state_topic(object_id, serial_number).replace('/state', '/attributes'),
                "payload_on": "ON", 
                "payload_off": "OFF",
                "device": device_info,
                "qos": 1,
                "icon": "mdi:electric-switch" if relay_group_name == 'lock' else "mdi:electric-switch-closed"
            }
            config_topic = f"{autoconfig_component_topic.format(component='binary_sensor')}/{object_id}/config"
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

            config_payload = {
                "name": aux_name,
                "unique_id": unique_id,
                "state_topic": build_state_topic(object_id, serial_number),
                "json_attributes_topic": build_state_topic(object_id, serial_number).replace('/state', '/attributes'),
                "payload_on": "ON", 
                "payload_off": "OFF", 
                "device": device_info,
                "qos": 1
            }
            config_topic = f"{autoconfig_component_topic.format(component='binary_sensor')}/{object_id}/config"
            payload_json = json.dumps(config_payload)
            mqtt_handler.publish_message(mqtt_client, config_topic, payload_json, qos=1, retain=True)

        except (TypeError, ValueError, AttributeError) as e:
            log.error(f"Invalid or incomplete aux input data: {aux_input}. Skipping. Error: {e}", exc_info=True)
            continue
