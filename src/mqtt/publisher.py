import json
import logging
from typing import Dict, Any, List, Optional

from mqtt import handler as mqtt_handler
from ha_integration import discovery as ha_discovery
from core.models import ProcessedEvent, EntityState

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
