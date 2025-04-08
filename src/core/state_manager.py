import logging
from typing import Dict, List, Optional

from core.models import DeviceDefinition, EntityState

log = logging.getLogger(__name__)

class StateManager:
    def __init__(self):
        self.entity_states: Dict[str, str] = {}
    
    def update_state(self, entity_id: str, state: str):
        self.entity_states[entity_id] = state
        log.debug(f"Updated state: {entity_id} -> {state}")
    
    def get_state(self, entity_id: str) -> Optional[str]:
        return self.entity_states.get(entity_id)
    
    def initialize_from_device(self, device_definition: DeviceDefinition) -> List[EntityState]:
        states = []
        
        for door in device_definition.doors:
            entity_id = f"door_{door.number}"
            # If lock_driver_time is 255, door is considered unlocked (ON)
            state = "ON" if door.parameters.lock_driver_time == 255 else "OFF"
            self.update_state(entity_id, state)
            states.append(EntityState(entity_id=entity_id, state=state))
        
        for aux_input in device_definition.aux_inputs:
            entity_id = f"aux_input_{aux_input.number}"
            # Default to OFF since we don't have initial state
            state = "OFF"
            self.update_state(entity_id, state)
            states.append(EntityState(entity_id=entity_id, state=state))
        
        for relay in device_definition.relays:
            entity_id = f"relay_{relay.group.name}_{relay.number}"
            # Default to OFF since we don't have initial state
            state = "OFF"
            self.update_state(entity_id, state)
            states.append(EntityState(entity_id=entity_id, state=state))
        
        for reader in device_definition.readers:
            entity_id = f"reader_{reader.number}_card"
            # Default card state is empty
            state = '{ "card_id": "0" }'
            self.update_state(entity_id, state)
            states.append(EntityState(entity_id=entity_id, state=state))
        
        return states

state_manager = StateManager()
