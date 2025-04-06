import json
import logging
import datetime
from typing import Any, Dict, Optional
from pyzkaccess.event import Event
from zkt_handler import DeviceDefinition

import settings
import zk_handler
import mqtt_handler

log = logging.getLogger(__name__)

def publish_entity_state(
    mqtt_client: mqtt_handler.mqtt.Client,
    device: DeviceDefinition,
    component: str,
    object_id: str,
    state: str,
    attributes: Optional[Dict[str, Any]] = None
):
    base_topic = f"{settings.HA_DISCOVERY_PREFIX}/{component}/{device.parameters.serial_number}/{object_id}"
    state_topic = f"{base_topic}/state"
    attributes_topic = f"{base_topic}/attributes"

    mqtt_handler.publish_message(mqtt_client, state_topic, str(state), qos=1, retain=False)

    if attributes and isinstance(attributes, dict):
        try:
            attributes_payload = json.dumps(attributes)
            mqtt_handler.publish_message(mqtt_client, attributes_topic, attributes_payload, qos=1, retain=False)
        except (TypeError, ValueError) as e:
            log.error(f"Failed to serialize attributes for {object_id}: {attributes}. Error: {e}")


def map_zk_event_to_ha_type(event: Event) -> str:
    if not hasattr(event, 'event_type') or not hasattr(event, 'verify_mode'):
         log.warning(f"Event object missing expected attributes (event_type, verify_mode): {event}")
         return "other"

    code = getattr(event.event_type, 'value', -1)
    doc = getattr(event.event_type, 'doc', '').lower()
    vm = getattr(event.verify_mode, 'name', '').lower()

    if code == 0: return "card_scan_success"
    if code == 1: return "card_scan_success"
    if code == 6: return "card_scan_denied"
    if code == 7: return "card_scan_denied"
    if code == 11: return "card_scan_invalid"
    if code == 12: return "card_scan_denied"
    if code == 26: return "door_open"
    if code == 27: return "door_open"
    if code == 28: return "door_button"
    if code == 4: return "door_close"
    if code == 5: return "door_open"

    if "card" in vm and ("pass" in doc or "ok" in doc or "valid" in doc): return "card_scan_success"
    if "card" in vm and ("fail" in doc or "denied" in doc or "invalid" in doc): return "card_scan_denied"
    if "pin" in vm and ("pass" in doc or "ok" in doc or "valid" in doc): return "pin_success"
    if "pin" in vm and ("fail" in doc or "denied" in doc or "invalid" in doc): return "pin_denied"
    if "finger" in vm and ("pass" in doc or "ok" in doc or "valid" in doc): return "fingerprint_success"
    if "finger" in vm and ("fail" in doc or "denied" in doc or "invalid" in doc): return "fingerprint_denied"

    log.debug(f"Unmapped ZK Event: Code={code}, Doc='{doc}', VM='{vm}'. Categorizing as 'other'.")
    return "other"


def process_event_for_ha(
    mqtt_client: mqtt_handler.mqtt.Client,
    device: DeviceDefinition,
    event: Event
):
    log.info(f"Event: {event.description}")

    try:
        reader_or_door_id_str = getattr(event, 'door', None)
        if reader_or_door_id_str is None:
            log.debug(f"Event missing 'door' attribute, cannot process for HA: {event}")
            return
        reader_or_door_id = int(reader_or_door_id_str)
        timestamp_dt = getattr(event, 'time', datetime.datetime.now())
        timestamp_iso = timestamp_dt.isoformat()
        card_id = getattr(event, 'card', None)
        pin = getattr(event, 'pin', None)
        user_id = card_id if card_id and card_id != '0' else pin
        verify_mode_name = getattr(getattr(event, 'verify_mode', None), 'name', 'Unknown')
        entry_exit_name = getattr(getattr(event, 'entry_exit', None), 'name', 'Unknown')
        zk_event_code = getattr(getattr(event, 'event_type', None), 'value', -1)
        zk_event_desc = getattr(getattr(event, 'event_type', None), 'doc', 'Unknown')
    except (TypeError, ValueError, AttributeError) as e:
        log.error(f"Error extracting data from event object: {event}. Error: {e}")
        return


    ha_event_type = map_zk_event_to_ha_type(event)
    event_payload = {
        "event_type": ha_event_type,
        "card_id": card_id if card_id and card_id != '0' else None,
        "pin": pin if pin and pin != '0' else None,
        "user_id": user_id if user_id and user_id != '0' else None,
        "door_id": reader_or_door_id,
        "reader_id": reader_or_door_id,
        "timestamp": timestamp_iso,
        "verify_mode": verify_mode_name,
        "entry_exit": entry_exit_name,
        "zk_event_code": zk_event_code,
        "zk_event_desc": zk_event_desc,
    }
    object_id = f"reader_{reader_or_door_id}_event"
    event_topic = f"{settings.HA_DISCOVERY_PREFIX}/event/{device.parameters.serial_number}/{object_id}/trigger"
    log.info(f"    HA Event: Publishing to {event_topic}")
    log.debug(f"    Payload: {event_payload}")
    try:
        payload_json = json.dumps({k: v for k, v in event_payload.items() if v is not None})
        mqtt_handler.publish_message(mqtt_client, event_topic, payload_json, qos=1, retain=False)
    except (TypeError, ValueError) as e:
        log.error(f"    Failed to serialize event payload for {event_topic}: {e}")

    door_state = None
    if zk_event_code in [5, 26, 27]: door_state = "ON"
    elif zk_event_code == 4: door_state = "OFF"

    if door_state is not None:
        object_id = f"door_{reader_or_door_id}"
        log.info(f"    HA Update: Door {reader_or_door_id} state -> {door_state}")
        publish_entity_state(mqtt_client, device, "binary_sensor", object_id, door_state)
    else:
        log.debug(f"    Event type {zk_event_code}/{zk_event_desc} does not map to a door state change.")


def polling_job(mqtt_client: mqtt_handler.mqtt.Client, device: DeviceDefinition):
    log.info("--- Running Polling Job ---")
    raw_events = zk_handler.poll_zkteco_changes()

    if raw_events is None:
        log.warning("Polling job skipped due to error retrieving events from device.")
        return

    if raw_events:
        log.info(f"Found {len(raw_events)} new event(s). Processing...")
        for event in raw_events:
            process_event_for_ha(mqtt_client, device, event)

            if settings.MQTT_GENERAL_EVENT_TOPIC:
                try:
                    general_payload = {
                         "timestamp": getattr(event, 'time', datetime.datetime.now()).isoformat(),
                         "door": getattr(event, 'door', None),
                         "card": getattr(event, 'card', None),
                         "pin": getattr(event, 'pin', None),
                         "event_code": getattr(getattr(event, 'event_type', None), 'value', -1),
                         "event_desc": getattr(getattr(event, 'event_type', None), 'doc', 'Unknown'),
                         "verify_mode": getattr(getattr(event, 'verify_mode', None), 'name', 'Unknown'),
                         "entry_exit": getattr(getattr(event, 'entry_exit', None), 'name', 'Unknown'),
                    }
                    payload_str = json.dumps({k: v for k, v in general_payload.items() if v is not None})
                    log.info(f"  Publishing raw event to general topic: {settings.MQTT_GENERAL_EVENT_TOPIC}")
                    mqtt_handler.publish_message(mqtt_client,
                                               settings.MQTT_GENERAL_EVENT_TOPIC,
                                               payload_str,
                                               qos=0, retain=False)
                except Exception as e:
                    log.error(f"  Failed to serialize or publish event to general topic: {e}")

    else:
        log.info("No new events found during this poll.")
    log.info("--- Polling Job Complete ---")
