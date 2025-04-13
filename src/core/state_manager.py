import logging
from typing import Dict, List, Optional

from core.models import DeviceDefinition, EntityState, ProcessedEvent

log = logging.getLogger(__name__)

class StateManager:
    def __init__(self):
        self.entity_states: Dict[str, str] = {}
        self.last_event: Optional[ProcessedEvent] = None
    
    def update_state(self, entity_id: str, state: str):
        self.entity_states[entity_id] = state
        log.debug(f"Updated state: {entity_id} -> {state}")

    def update_last_event(self, event: ProcessedEvent):
        self.last_event = event
    
    def get_state(self, entity_id: str) -> Optional[str]:
        return self.entity_states.get(entity_id)

    def get_states(self) -> Dict[str, str]:
        return self.entity_states

    def get_last_event(self) -> Optional[ProcessedEvent]:
        return self.last_event
    
    def initialize_from_device(self, device_definition: DeviceDefinition) -> List[EntityState]:
        states = []
        
        for door in device_definition.doors:
            door_number = door['number']
            entity_id = f"door_{door_number}"
            # Default to OFF since we don't have reliable lock driver time info now
            state = "OFF"
            self.update_state(entity_id, state)
            states.append(EntityState(entity_id=entity_id, state=state))
        
        for aux_input in device_definition.aux_inputs:
            aux_number = aux_input['number']
            entity_id = f"aux_input_{aux_number}"
            # Default to OFF since we don't have initial state
            state = "OFF"
            self.update_state(entity_id, state)
            states.append(EntityState(entity_id=entity_id, state=state))
        
        for relay in device_definition.relays:
            relay_number = relay['number']
            # For simplicity, assume all relays are in the 'lock' group for now
            relay_group = "lock"
            entity_id = f"relay_{relay_group}_{relay_number}"
            # Default to OFF since we don't have initial state
            state = "OFF"
            self.update_state(entity_id, state)
            states.append(EntityState(entity_id=entity_id, state=state))
        
        for reader in device_definition.readers:
            reader_number = reader['number']
            entity_id = f"reader_{reader_number}_card"
            # Default card state is empty
            state = '{ "card_id": "0" }'
            self.update_state(entity_id, state)
            states.append(EntityState(entity_id=entity_id, state=state))
        
        return states

state_manager = StateManager()
