import json
import logging
import os
from typing import Dict, List, Optional

from core.models import DeviceDefinition, EntityState, ProcessedEvent

log = logging.getLogger(__name__)

class StateManager:
    def __init__(self, state_file_path: str = 'state.json'):
        self.state_file_path = state_file_path
        self.entity_states: Dict[str, str] = {}
        self.last_event: Optional[ProcessedEvent] = None
        
        self.load_state()
    
    def update_state(self, entity_id: str, state: str):
        self.entity_states[entity_id] = state
        log.debug(f"Updated state: {entity_id} -> {state}")

        self.save_state()

    def update_last_event(self, event: ProcessedEvent):
        self.last_event = event

        self.save_state()
    
    def get_state(self, entity_id: str) -> Optional[str]:
        return self.entity_states.get(entity_id)

    def get_states(self) -> Dict[str, str]:
        return self.entity_states

    def get_last_event(self) -> Optional[ProcessedEvent]:
        return self.last_event
    
    def load_state(self):
        try:
            if os.path.exists(self.state_file_path):
                with open(self.state_file_path, 'r') as f:
                    data = json.load(f)
                    self.entity_states = data.get('entity_states', {})
                    log.info(f"Loaded state from {self.state_file_path}")
        except Exception as e:
            log.error(f"Error loading state from file: {e}")
    
    def save_state(self):
        try:
            data = {
                'entity_states': self.entity_states
            }
            with open(self.state_file_path, 'w') as f:
                json.dump(data, f, indent=4)
            log.debug(f"Saved state to {self.state_file_path}")
        except Exception as e:
            log.error(f"Error saving state to file: {e}")
    
    def initialize_from_device(self, device_definition: DeviceDefinition) -> List[EntityState]:
        states = []
        
        for door in device_definition.doors:
            door_number = door['number']
            entity_id = f"door_{door_number}"
            state = self.entity_states.get(entity_id, "OFF")
            
            if entity_id not in self.entity_states:
                self.update_state(entity_id, state)
            states.append(EntityState(entity_id=entity_id, state=state))
        
        for aux_input in device_definition.aux_inputs:
            aux_number = aux_input['number']
            entity_id = f"aux_input_{aux_number}"
            state = self.entity_states.get(entity_id, "OFF")
            
            if entity_id not in self.entity_states:
                self.update_state(entity_id, state)
            states.append(EntityState(entity_id=entity_id, state=state))
        
        for relay in device_definition.relays:
            relay_number = relay['number']
            relay_group = "lock"
            entity_id = f"relay_{relay_group}_{relay_number}"

            state = self.entity_states.get(entity_id, "OFF")
            if entity_id not in self.entity_states:
                self.update_state(entity_id, state)
            states.append(EntityState(entity_id=entity_id, state=state))
        
        for reader in device_definition.readers:
            reader_number = reader['number']
            entity_id = f"reader_{reader_number}_card"
            state = self.entity_states.get(entity_id, '{ "card_id": "0" }')
            
            if entity_id not in self.entity_states:
                self.update_state(entity_id, state)
            states.append(EntityState(entity_id=entity_id, state=state))
        
        return states
