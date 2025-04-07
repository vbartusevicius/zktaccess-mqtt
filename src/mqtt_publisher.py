import json
import logging
from typing import Dict, Any, List, Optional

import mqtt_handler
import ha_discovery
from models import ProcessedEvent, EntityState

log = logging.getLogger(__name__)

class MQTTPublisher:
    def __init__(self, mqtt_client: mqtt_handler.mqtt.Client, serial_number: str):
        self.mqtt_client = mqtt_client
        self.serial_number = serial_number
        
    def publish_entity_state(self, entity_id: str, state: str, attributes: Optional[Dict[str, Any]] = None):
        state_topic = ha_discovery.build_state_topic(entity_id, self.serial_number)
        attributes_topic = state_topic.replace('/state', '/attributes')

        log.debug(f"Publishing state to {state_topic}: {state}")
        mqtt_handler.publish_message(self.mqtt_client, state_topic, str(state), qos=1, retain=False)
        
        if attributes and isinstance(attributes, dict):
            try:
                payload = json.dumps(attributes)
                log.debug(f"Publishing attributes to {attributes_topic}: {payload}")
                mqtt_handler.publish_message(self.mqtt_client, attributes_topic, payload, qos=1, retain=False)
            except (TypeError, ValueError) as e: 
                log.error(f"Failed to serialize attributes for {entity_id}: {attributes}. Err: {e}")
    
    def publish_event(self, event: ProcessedEvent):
        log.info(f"Publishing event: Type={event.event_type.value}, Door={event.door_id}, Reader={event.reader_id}")
        
        timestamp_iso = event.timestamp.isoformat()
        
        event_payload = {
            "event_type": event.event_type.value,
            "door_id": event.door_id,
            "reader_id": event.reader_id,
            "timestamp": timestamp_iso,
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
        
        scan_object_id_event = f"reader_{event.reader_id}_scan"
        scan_event_topic = ha_discovery.build_state_topic(scan_object_id_event, self.serial_number)

        card_object_id_event = f"reader_{event.reader_id}_card"
        card_event_topic = ha_discovery.build_state_topic(card_object_id_event, self.serial_number)
        
        log.info(f"    HA Reader: Publishing to {scan_event_topic} and {card_event_topic}")
        
        try:
            payload_json = json.dumps({k: v for k, v in event_payload.items() if v is not None})
            mqtt_handler.publish_message(self.mqtt_client, scan_event_topic, payload_json, qos=1, retain=False)
            mqtt_handler.publish_message(self.mqtt_client, card_event_topic, payload_json, qos=1, retain=False)
        except (TypeError, ValueError) as e: 
            log.error(f"Failed to serialize event payload: {e}")
    
    def publish_raw_event(self, event: ProcessedEvent):
        try:
            raw_payload = {
                "timestamp": event.timestamp.isoformat(),
                "door": event.door_id,
                "card": event.card_id,
                "pin": event.pin,
                "event_code": event.zk_event_code,
                "event_desc": event.zk_event_desc,
                "verify_mode": event.verify_mode,
                "entry_exit": event.entry_exit
            }
            payload_str = json.dumps({k: v for k, v in raw_payload.items() if v is not None})
            log.debug("Publishing raw event to general topic")
            mqtt_handler.publish_message(
                self.mqtt_client,
                ha_discovery.build_state_topic('raw_event', self.serial_number),
                payload_str,
                qos=0,
                retain=False
            )
        except Exception as e:
            log.error(f"Failed to serialize/publish event to general topic: {e}")
    
    def publish_entity_states(self, states: List[EntityState]):
        for state in states:
            self.publish_entity_state(state.entity_id, state.state, state.attributes)
