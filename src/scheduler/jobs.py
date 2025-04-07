import logging

from zkt import handler as zkt_handler
from core.event_processor import process_event, get_related_entity_states
from mqtt.publisher import MQTTPublisher
from core.state_manager import state_manager

log = logging.getLogger(__name__)

class JobScheduler:   
    def __init__(self, publisher: MQTTPublisher):
        self.publisher = publisher
    
    def polling_job(self):
        log.info("--- Running Polling Job ---")
        raw_events = zkt_handler.poll_zkteco_changes()
        
        if raw_events is None:
            log.warning("No events received or error occurred during polling")
            return

        log.info(f"Found {len(raw_events)} new event(s)")
        for raw_event in raw_events:
            self._process_single_event(raw_event)
            
        log.info("--- Polling Job Complete ---")
    
    def _process_single_event(self, raw_event):
        try:
            processed_event = process_event(raw_event)
            if not processed_event:
                log.warning(f"Failed to process event: {raw_event}")
                return
                
            self.publisher.publish_event(processed_event)
            self.publisher.publish_raw_event(processed_event)
            
            related_states = get_related_entity_states(processed_event)
            for state in related_states:
                state_manager.update_state(state.entity_id, state.state)
                
            if related_states:
                self.publisher.publish_entity_states(related_states)
                
        except Exception as e:
            log.exception(f"Error processing event: {e}")
    
    def initialize_states(self, device_definition):
        log.info("--- Initializing Entity States ---")
        
        states = state_manager.initialize_from_device(device_definition)
        self.publisher.publish_entity_states(states)
        
        log.info(f"Published initial state for {len(states)} entities")
