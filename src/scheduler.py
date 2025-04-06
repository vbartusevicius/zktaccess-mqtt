import json
import logging
import datetime
from typing import Any, Dict, Optional

import settings
import mqtt_handler
from pyzkaccess.event import Event
from pyzkaccess.enums import EVENT_TYPES, RelayGroup

log = logging.getLogger(__name__)

def safe_get_nested_attr(obj: Any, *attrs: str, default: Any = None) -> Any:
    for attr in attrs:
        if obj is None: return default
        if hasattr(obj, '__getattribute__'): obj = getattr(obj, attr, None)
        else: return default
    return obj if obj is not None else default


def publish_entity_state(
    mqtt_client: mqtt_handler.mqtt.Client,
    ha_identifier: str,
    component: str,
    object_id: str,
    state: str,
    attributes: Optional[Dict[str, Any]] = None
):
    base_topic = f"{settings.HA_DISCOVERY_PREFIX}/{component}/{ha_identifier}/{object_id}"
    state_topic = f"{base_topic}/state"
    attributes_topic = f"{base_topic}/attributes"
    log.debug(f"Publishing state to {state_topic}: {state}")
    mqtt_handler.publish_message(mqtt_client, state_topic, str(state), qos=1, retain=False)
    if attributes and isinstance(attributes, dict):
        try:
            payload = json.dumps(attributes)
            log.debug(f"Publishing attributes to {attributes_topic}: {payload}")
            mqtt_handler.publish_message(mqtt_client, attributes_topic, payload, qos=1, retain=False)
        except (TypeError, ValueError) as e: log.error(f"Failed to serialize attributes for {object_id}: {attributes}. Err: {e}")

def map_zk_event_to_ha_type(event: Event) -> str:
    code = safe_get_nested_attr(event, 'event_type', 'value', default=-1)
    doc = safe_get_nested_attr(event, 'event_type', 'doc', default='').lower()
    vm = safe_get_nested_attr(event, 'verify_mode', 'name', default='').lower()
    if code < 0 and not doc and not vm: 
        log.warning(f"Event missing expected attributes: {event}"); return "other"

    if code == 0: return "card_scan_success"
    if code == 220: return "aux_input_disconnected"
    if code == 221: return "aux_input_shorted"
    if code == 1: return "card_scan_success"
    if code == 20: return "card_scan_denied"
    if code == 21: return "card_scan_denied"
    if code == 22: return "card_scan_denied"
    if code == 23: return "card_scan_denied"
    if code == 24: return "card_scan_denied"
    if code == 25: return "card_scan_denied"
    if code == 27: return "card_scan_invalid"
    if code == 29: return "card_scan_denied"
    if code == 30: return "pin_denied"
    if code == 33: return "fingerprint_denied"
    if code == 34: return "fingerprint_invalid"
    if code == 101: return "pin_denied"
    if code == 103: return "fingerprint_denied"
    if code == 200: return "door_open"
    if code == 201: return "door_close"
    if code == 202: return "door_button"
    if code == 28: return "door_open"
    if code == 5: return "door_open"
    if code == 26: return "door_open"
    if code == 37: return "door_open"
    if code in [0, 1, 2, 3, 14, 15, 16, 17, 18, 19, 203]:
        if "card" in vm: return "card_scan_success"
        if "pin" in vm or "password" in vm: return "pin_success"
        if "finger" in vm: return "fingerprint_success"
        return "other_success"

    log.debug(f"Unmapped ZK Event: Code={code}, Desc='{doc}', VM='{vm}'. Categorizing as 'other'.")
    return "other"

def process_event_for_ha(
    mqtt_client: mqtt_handler.mqtt.Client,
    ha_identifier: str,
    event: Event
):
    door_id_val = safe_get_attr(event, 'door')
    if door_id_val is None: 
        log.debug(f"Event missing 'door' attribute: {event}"); return
    try: 
        entity_num_id = int(door_id_val)
    except (ValueError, TypeError): 
        log.warning(f"Could not parse door/entity ID '{door_id_val}' from event: {event}"); return
    timestamp_dt = safe_get_attr(event, 'time', default=datetime.datetime.now())
    timestamp_iso = timestamp_dt.isoformat()
    card_id = safe_get_attr(event, 'card')
    pin = safe_get_attr(event, 'pin')
    user_id = card_id if card_id and str(card_id) != '0' else pin
    verify_mode_name = safe_get_nested_attr(event, 'verify_mode', 'name', default='Unknown')
    entry_exit_name = safe_get_nested_attr(event, 'entry_exit', 'name', default='Unknown')
    zk_event_code = safe_get_nested_attr(event, 'event_type', 'value', default=-1)
    zk_event_desc = safe_get_nested_attr(event, 'event_type', 'doc', default=EVENT_TYPES.get(zk_event_code, 'Unknown'))

    log.info(f"Processing Event: EntityID={entity_num_id}, Type={zk_event_code}/{zk_event_desc}, User={user_id or 'N/A'}, Time={timestamp_iso}")
    if not ha_identifier: 
        log.error("Cannot process event for HA, missing identifier."); return

    ha_event_type = map_zk_event_to_ha_type(event)
    event_payload = {
        "event_type": ha_event_type, 
        "card_id": card_id if card_id and str(card_id) != '0' else None,
        "pin": pin if pin and str(pin) != '0' else None, 
        "user_id": user_id if user_id and str(user_id) != '0' else None,
        "door_id": entity_num_id, 
        "reader_id": entity_num_id, 
        "timestamp": timestamp_iso,
        "verify_mode": verify_mode_name, 
        "entry_exit": entry_exit_name,
        "zk_event_code": zk_event_code, 
        "zk_event_desc": zk_event_desc
    }
    object_id_event = f"reader_{entity_num_id}_event"
    event_topic = f"{settings.HA_DISCOVERY_PREFIX}/event/{ha_identifier}/{object_id_event}/trigger"
    log.info(f"    HA Reader Event: Publishing to {event_topic}")
    try:
        payload_json = json.dumps({k: v for k, v in event_payload.items() if v is not None})
        mqtt_handler.publish_message(mqtt_client, event_topic, payload_json, qos=1, retain=False)
    except (TypeError, ValueError) as e: 
        log.error(f"    Failed to serialize event payload for {event_topic}: {e}")

    door_state = None
    if zk_event_code in [5, 28, 200, 202, 205, 26, 37]: 
        door_state = "ON"
    elif zk_event_code == 201: 
        door_state = "OFF"

    if door_state is not None:
        object_id_door = f"door_{entity_num_id}"
        log.info(f"    HA Door Update: Door {entity_num_id} state -> {door_state}")
        publish_entity_state(mqtt_client, ha_identifier, "binary_sensor", object_id_door, door_state)
        if zk_event_code == 26: 
            log.warning(f"Door {entity_num_id} forced open? (Event 26)")
        if zk_event_code == 37: 
            log.warning(f"Door {entity_num_id} failed to close (Event 37)")

    lock_relay_state = None
    if zk_event_code in [0, 1, 2, 3, 4, 5, 8, 14, 15, 16, 17, 18, 19, 101, 103, 200, 202, 203, 205]:
        lock_relay_state = "ON"
    elif zk_event_code in [9, 201, 204]:
        lock_relay_state = "OFF"

    if lock_relay_state is not None:
        object_id_relay = f"relay_{RelayGroup.lock.name}_{entity_num_id}"
        log.info(f"    HA Relay Update: Lock Relay {entity_num_id} inferred state -> {lock_relay_state} (Based on event {zk_event_code})")
        publish_entity_state(mqtt_client, ha_identifier, "switch", object_id_relay, lock_relay_state)

    aux_input_state = None
    if zk_event_code == 221:
        aux_input_state = "ON"
    elif zk_event_code == 220:
        aux_input_state = "OFF"

    if aux_input_state is not None:
        object_id_aux = f"aux_input_{entity_num_id}"
        log.info(f"    HA Aux Update: Aux Input {entity_num_id} state -> {aux_input_state} (Event {zk_event_code})")
        publish_entity_state(mqtt_client, ha_identifier, "binary_sensor", object_id_aux, aux_input_state)


def polling_job(mqtt_client: mqtt_handler.mqtt.Client, ha_identifier: str):
    log.info("--- Running Polling Job ---")
    raw_events = zk_handler.poll_zkteco_changes()
    if raw_events is None: 
        log.warning("Polling job skipped: error retrieving events.")
        return

    if raw_events:
        log.info(f"Found {len(raw_events)} new event(s). Processing...")
        for event in raw_events:
            process_event_for_ha(mqtt_client, ha_identifier, event)
            if settings.MQTT_GENERAL_EVENT_TOPIC:
                try:
                    gp = { 
                        "timestamp": safe_get_attr(event, 'time', default=datetime.datetime.now()).isoformat(),
                        "door": safe_get_attr(event, 'door'), 
                        "card": safe_get_attr(event, 'card'),
                        "pin": safe_get_attr(event, 'pin'), 
                        "event_code": safe_get_nested_attr(event, 'event_type', 'value'),
                        "event_desc": safe_get_nested_attr(event, 'event_type', 'doc'),
                        "verify_mode": safe_get_nested_attr(event, 'verify_mode', 'name'),
                        "entry_exit": safe_get_nested_attr(event, 'entry_exit', 'name'),
                    }
                    payload_str = json.dumps({k: v for k, v in gp.items() if v is not None})
                    log.debug(f"Publishing raw event to general topic: {settings.MQTT_GENERAL_EVENT_TOPIC}")
                    mqtt_handler.publish_message(mqtt_client, settings.MQTT_GENERAL_EVENT_TOPIC, payload_str, qos=0, retain=False)
                except Exception as e: log.error(f"Failed to serialize/publish event to general topic: {e}")
    else: 
        log.info("No new events found during this poll.")
    log.info("--- Polling Job Complete ---")
