import logging
import datetime
import pytz
from typing import Optional, List
import json
from c3.consts import EventType as C3EventType, VerificationMode

class RelayGroup:
    lock = "lock"
    aux = "aux"

import settings
from core.models import ProcessedEvent, EventType, EntityState

log = logging.getLogger(__name__)

def map_zk_event_to_ha_type(event) -> EventType:
    event_type = event.event_type
    verification = event.verified
    
    # Log the enum values for debugging
    log.debug(f"Event mapping: type={event_type.name}, code={event_type.value}, desc={event_type.description}, verification={verification}")
    
    # Check for invalid event type
    if event_type == C3EventType.NA:
        log.warning(f"Event has NA event type: {event}")
        return EventType.OTHER

    # Door opening events
    if event_type in [
        C3EventType.NORMAL_PUNCH_OPEN, 
        C3EventType.OPEN_NORMAL_OPEN_TZ, 
        C3EventType.OPENING_TIMEOUT, 
        C3EventType.DOOR_OPENED_CORRECT, 
        C3EventType.EXIT_BUTTON_OPEN, 
        C3EventType.REMOTE_NORMAL_OPEN, 
        C3EventType.MULTI_CARD_AUTH, 
        C3EventType.FAILED_CLOSE_NORMAL_OPEN_TZ
    ]:
        return EventType.DOOR_OPEN
    
    # Door closing events
    elif event_type == C3EventType.DOOR_CLOSED_CORRECT:
        return EventType.DOOR_CLOSE
    
    # Door button event
    elif event_type == C3EventType.EXIT_BUTTON_OPEN:
        return EventType.DOOR_BUTTON
    
    # Aux input events
    elif event_type == C3EventType.AUX_INPUT_DISCONNECT:
        return EventType.AUX_INPUT_DISCONNECTED
    elif event_type == C3EventType.AUX_INPUT_SHORT:
        return EventType.AUX_INPUT_CONNECTED
    
    # Card scan events
    elif event_type in [C3EventType.NORMAL_PUNCH_OPEN, C3EventType.PUNCH_NORMAL_OPEN_TZ] and verification == VerificationMode.CARD:
        return EventType.CARD_SCAN_SUCCESS
    elif event_type in [
        C3EventType.TOO_SHORT_PUNCH_INTERVAL, 
        C3EventType.DOOR_INACTIVE_TZ, 
        C3EventType.ILLEGAL_TZ, 
        C3EventType.ACCESS_DENIED, 
        C3EventType.ANTI_PASSBACK, 
        C3EventType.INTERLOCK, 
        C3EventType.CARD_EXPIRED
    ]:
        return EventType.CARD_SCAN_DENIED
    elif event_type == C3EventType.UNREGISTERED_CARD:
        return EventType.CARD_SCAN_INVALID
    
    # PIN events
    elif event_type in [C3EventType.PASSWORD_ERROR, C3EventType.DURESS_PASSWORD_OPEN]:
        return EventType.PIN_DENIED
    
    # Fingerprint events
    elif event_type in [C3EventType.FP_EXPIRED, C3EventType.DURESS_FP_OPEN]:
        return EventType.FINGERPRINT_DENIED
    elif event_type == C3EventType.UNREGISTERED_FP:
        return EventType.FINGERPRINT_INVALID
    
    # Multi-purpose events based on verification mode
    elif verification == VerificationMode.CARD:
        return EventType.CARD_SCAN_SUCCESS
    elif verification == VerificationMode.PASSWORD:
        return EventType.PIN_SUCCESS
    elif verification == VerificationMode.FINGER:
        return EventType.FINGERPRINT_SUCCESS
    elif verification in [VerificationMode.CARD_OR_FINGER, VerificationMode.CARD_WITH_FINGER, VerificationMode.CARD_WITH_PASSWORD]:
        return EventType.OTHER_SUCCESS

    return EventType.OTHER

def process_event(event) -> Optional[ProcessedEvent]:
    log.debug(f"Processing event: {event}")

    if not hasattr(event, 'port_nr'):
        log.warning(f"Event missing required attribute 'port_nr': {event}")
        return None
    
    door_id_val = event.port_nr
    log.debug(f"Door port number: {door_id_val}")
    
    try: 
        entity_num_id = int(door_id_val)
    except (ValueError, TypeError): 
        log.warning(f"Could not parse door ID '{door_id_val}' from event: {event}")
        return None

    timestamp_str = str(event.time_second)
    try:
        timestamp_dt = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        log.debug(f"Parsed timestamp: {timestamp_dt}")
    except Exception as e:
        log.warning(f"Failed to parse time_second '{timestamp_str}': {e}")
        timestamp_dt = datetime.datetime.now()
    
    if timestamp_dt.tzinfo is None:
        timestamp_dt = timestamp_dt.replace(tzinfo=pytz.UTC)
    try:
        local_tz = pytz.timezone(settings.TIME_ZONE)
        local_dt = timestamp_dt.astimezone(local_tz)
    except Exception as e:
        log.warning(f"Failed to convert timestamp to timezone {settings.TIME_ZONE}: {e}")
        local_dt = timestamp_dt

    card_id = event.card_no
    pin = event.pin
    verify_mode_name = str(event.verified)
    entry_exit_name = str(event.in_out_state)
    zk_event_code = event.event_type.value
    zk_event_desc = event.event_type.description
    
    log.debug(f"Extracted event data: card={card_id}, verify={verify_mode_name}, entry/exit={entry_exit_name}, code={zk_event_code}")

    event_type = map_zk_event_to_ha_type(event)
    
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
    door_open_events = [
        C3EventType.NORMAL_PUNCH_OPEN.value, 
        C3EventType.OPEN_NORMAL_OPEN_TZ.value, 
        C3EventType.OPENING_TIMEOUT.value, 
        C3EventType.DOOR_OPENED_CORRECT.value, 
        C3EventType.EXIT_BUTTON_OPEN.value, 
        C3EventType.REMOTE_NORMAL_OPEN.value, 
        C3EventType.MULTI_CARD_AUTH.value, 
        C3EventType.FAILED_CLOSE_NORMAL_OPEN_TZ.value
    ]
    
    if event.zk_event_code in door_open_events:
        return "ON"
    elif event.zk_event_code == C3EventType.DOOR_CLOSED_CORRECT.value:
        return "OFF"
    return None

def determine_lock_relay_state(event: ProcessedEvent) -> Optional[str]:
    lock_relay_on_events = [
        C3EventType.NORMAL_PUNCH_OPEN.value,
        C3EventType.PUNCH_NORMAL_OPEN_TZ.value,
        C3EventType.FIRST_CARD_NORMAL_OPEN.value,
        C3EventType.MULTI_CARD_OPEN.value,
        C3EventType.EMERGENCY_PASS_OPEN.value,
        C3EventType.OPEN_NORMAL_OPEN_TZ.value,
        C3EventType.REMOTE_OPENING.value,
        C3EventType.PRESS_FINGER_OPEN.value,
        C3EventType.MULTI_CARD_OPEN_FP.value,
        C3EventType.FP_NORMAL_OPEN_TZ.value,
        C3EventType.CARD_FP_OPEN.value,
        C3EventType.FIRST_CARD_NORMAL_OPEN_FP.value,
        C3EventType.FIRST_CARD_NORMAL_OPEN_CARD_FP.value,
        C3EventType.DURESS_PASSWORD_OPEN.value,
        C3EventType.DURESS_FP_OPEN.value,
        C3EventType.DOOR_OPENED_CORRECT.value,
        C3EventType.EXIT_BUTTON_OPEN.value,
        C3EventType.MULTI_CARD_OPEN_CARD_FP.value,
        C3EventType.REMOTE_NORMAL_OPEN.value
    ]
    
    lock_relay_off_events = [
        C3EventType.REMOTE_CLOSING.value,
        C3EventType.DOOR_CLOSED_CORRECT.value,
        C3EventType.NORMAL_OPEN_TZ_OVER.value
    ]
    
    if event.zk_event_code in lock_relay_on_events:
        return "ON"
    elif event.zk_event_code in lock_relay_off_events:
        return "OFF"
    return None

def determine_aux_input_state(event: ProcessedEvent) -> Optional[str]:
    if event.zk_event_code == C3EventType.AUX_INPUT_SHORT.value:
        return "ON"
    elif event.zk_event_code == C3EventType.AUX_INPUT_DISCONNECT.value:
        return "OFF"
    return None

def get_related_entity_states(event: ProcessedEvent) -> List[EntityState]:
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
            entity_id=f"relay_{RelayGroup.lock}_{event.door_id}",
            state=lock_relay_state
        ))
    
    aux_input_state = determine_aux_input_state(event)
    if aux_input_state is not None:
        states.append(EntityState(
            entity_id=f"aux_input_{event.door_id}",
            state=aux_input_state
        ))
    
    if hasattr(event, 'reader_id') and event.reader_id is not None:
        event_payload = {
            "event_type": event.event_type.value,
            "door_id": event.door_id,
            "reader_id": event.reader_id,
            "timestamp": event.timestamp.isoformat(),
            "zk_event_code": event.zk_event_code,
            "zk_event_desc": event.zk_event_desc
        }
        
        if event.card_id:
            event_payload["card_id"] = event.card_id
        if event.pin:
            event_payload["pin"] = event.pin
        if event.verify_mode:
            event_payload["verify_mode"] = event.verify_mode
        if event.entry_exit:
            event_payload["entry_exit"] = event.entry_exit
        
        for key, value in event.additional_attributes.items():
            event_payload[key] = value
            
        payload_json = json.dumps({k: v for k, v in event_payload.items() if v is not None})
        
        # Update card state
        states.append(EntityState(
            entity_id=f"reader_{event.reader_id}_card",
            state=payload_json
        ))
        
        # Update scan state
        states.append(EntityState(
            entity_id=f"reader_{event.reader_id}_scan",
            state=payload_json
        ))
    
    return states
