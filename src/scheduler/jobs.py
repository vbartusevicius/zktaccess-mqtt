import logging

from zkt import handler as zkt_handler
from core.event_processor import process_event, get_related_entity_states
from mqtt.publisher import MQTTPublisher
from core.state_manager import state_manager
from core.models import EntityState
from c3.rtlog import EventRecord

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

    def _process_single_event(self, raw_event: EventRecord):
        self._update_state(raw_event)

        last_event = state_manager.get_last_event()
        all_states = state_manager.get_states()
        entity_states = [
            EntityState(entity_id=entity_id, state=state) for entity_id, state in all_states.items()
        ]

        self.publisher.publish_entity_states(entity_states)
        if  last_event:
            self.publisher.publish_event(last_event)
            self.publisher.publish_raw_event(last_event)

    def _update_state(self, raw_event: EventRecord):
        try:
            processed_event = process_event(raw_event)
            if not processed_event:
                log.warning(f"Failed to process event: {raw_event}")
                return

            state_manager.update_last_event(processed_event)
            related_states = get_related_entity_states(processed_event)
            for state in related_states:
                state_manager.update_state(state.entity_id, state.state)
        except Exception as e:
            log.exception(f"Error processing event: {e}")
    
    def initialize_states(self, device_definition):
        log.info("--- Initializing Entity States ---")
        
        states = state_manager.initialize_from_device(device_definition)
        self.publisher.publish_entity_states(states)
        
        log.info(f"Published initial state for {len(states)} entities")
