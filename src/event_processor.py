import logging
import datetime
import pytz
from typing import Optional

from pyzkaccess.event import Event
from pyzkaccess.enums import EVENT_TYPES, RelayGroup

import settings
from models import ProcessedEvent, EventType, EntityState
from utils import safe_get_nested_attr

log = logging.getLogger(__name__)

def map_zk_event_to_ha_type(event: Event) -> EventType:
    code = safe_get_nested_attr(event, 'event_type', 'value', default=-1)
    doc = safe_get_nested_attr(event, 'event_type', 'doc', default='').lower()
    vm = safe_get_nested_attr(event, 'verify_mode', 'name', default='').lower()
    
    if code < 0 and not doc and not vm: 
        log.warning(f"Event missing expected attributes: {event}")
        return EventType.OTHER

    # Door opening events
    if code in [0, 5, 28, 200, 202, 205, 26, 37]:
        return EventType.DOOR_OPEN
    
    # Door closing events
    elif code == 201:
        return EventType.DOOR_CLOSE
    
    # Door button event
    elif code == 202:
        return EventType.DOOR_BUTTON
    
    # Aux input events
    elif code == 220:
        return EventType.AUX_INPUT_DISCONNECTED
    elif code == 221:
        return EventType.AUX_INPUT_CONNECTED
    
    # Card scan events
    elif code in [0, 1]:
        return EventType.CARD_SCAN_SUCCESS
    elif code in [20, 21, 22, 23, 24, 25, 29]:
        return EventType.CARD_SCAN_DENIED
    elif code == 27:
        return EventType.CARD_SCAN_INVALID
    
    # PIN events
    elif code in [30, 101]:
        return EventType.PIN_DENIED
    
    # Fingerprint events
    elif code == 33 or code == 103:
        return EventType.FINGERPRINT_DENIED
    elif code == 34:
        return EventType.FINGERPRINT_INVALID
    
    # Multi-purpose events
    elif code in [0, 1, 2, 3, 14, 15, 16, 17, 18, 19, 203]:
        if "card" in vm:
            return EventType.CARD_SCAN_SUCCESS
        elif "pin" in vm or "password" in vm:
            return EventType.PIN_SUCCESS
        elif "finger" in vm:
            return EventType.FINGERPRINT_SUCCESS
        else:
            return EventType.OTHER_SUCCESS

    return EventType.OTHER

def process_event(event: Event) -> Optional[ProcessedEvent]:
    log.debug(f"Processing event: {event}")

    door_id_val = safe_get_nested_attr(event, 'door')
    if door_id_val is None: 
        log.warning(f"Event missing 'door' attribute: {event}")
        return None
    
    try: 
        entity_num_id = int(door_id_val)
    except (ValueError, TypeError): 
        log.warning(f"Could not parse door/entity ID '{door_id_val}' from event: {event}")
        return None

    timestamp_dt = safe_get_nested_attr(event, 'time', default=datetime.datetime.now())
    if timestamp_dt.tzinfo is None:
        timestamp_dt = timestamp_dt.replace(tzinfo=pytz.UTC)
    try:
        local_tz = pytz.timezone(settings.TIME_ZONE)
        local_dt = timestamp_dt.astimezone(local_tz)
    except Exception as e:
        log.warning(f"Failed to convert timestamp to timezone {settings.TIME_ZONE}: {e}")
        local_dt = timestamp_dt

    card_id = safe_get_nested_attr(event, 'card')
    pin = safe_get_nested_attr(event, 'pin')
    verify_mode_name = safe_get_nested_attr(event, 'verify_mode', 'name', default='Unknown')
    entry_exit_name = safe_get_nested_attr(event, 'entry_exit', 'name', default='Unknown')
    zk_event_code = safe_get_nested_attr(event, 'event_type', 'value', default=-1)
    zk_event_desc = safe_get_nested_attr(event, 'event_type', 'doc', default=EVENT_TYPES.get(zk_event_code, 'Unknown'))

    event_type = map_zk_event_to_ha_type(event)
    
    # Normalize card_id and pin
    normalized_card_id = None if card_id is None or str(card_id) == '0' else str(card_id)
    normalized_pin = None if pin is None or str(pin) == '0' else str(pin)

    return ProcessedEvent(
        event_type=event_type,
        door_id=entity_num_id,
        reader_id=entity_num_id,
        timestamp=local_dt,
        card_id=normalized_card_id,
        pin=normalized_pin,
        verify_mode=verify_mode_name,
        entry_exit=entry_exit_name,
        zk_event_code=zk_event_code,
        zk_event_desc=zk_event_desc,
        raw_event=event
    )

def determine_door_state(event: ProcessedEvent) -> Optional[str]:
    if event.zk_event_code in [0, 5, 28, 200, 202, 205, 26, 37]:
        return "ON"
    elif event.zk_event_code == 201:
        return "OFF"
    return None

def determine_lock_relay_state(event: ProcessedEvent) -> Optional[str]:
    if event.zk_event_code in [0, 1, 2, 3, 4, 5, 8, 14, 15, 16, 17, 18, 19, 101, 103, 200, 202, 203, 205]:
        return "ON"
    elif event.zk_event_code in [9, 201, 204]:
        return "OFF"
    return None

def determine_aux_input_state(event: ProcessedEvent) -> Optional[str]:
    if event.zk_event_code == 221:
        return "ON"
    elif event.zk_event_code == 220:
        return "OFF"
    return None

def get_related_entity_states(event: ProcessedEvent):
    states = []
    
    door_state = determine_door_state(event)
    if door_state is not None:
        states.append(EntityState(
            entity_id=f"door_{event.door_id}",
            state=door_state
        ))
    
    lock_relay_state = determine_lock_relay_state(event)
    if lock_relay_state is not None:
        states.append(EntityState(
            entity_id=f"relay_{RelayGroup.lock.name}_{event.door_id}",
            state=lock_relay_state
        ))
    
    aux_input_state = determine_aux_input_state(event)
    if aux_input_state is not None:
        states.append(EntityState(
            entity_id=f"aux_input_{event.door_id}",
            state=aux_input_state
        ))
    
    return states
