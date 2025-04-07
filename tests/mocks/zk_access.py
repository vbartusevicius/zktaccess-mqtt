from unittest.mock import MagicMock
from typing import List, Optional, Type
from datetime import datetime

from pyzkaccess.device import ZKDevice
from pyzkaccess.door import Door
from pyzkaccess.reader import Reader
from pyzkaccess.relay import Relay
from pyzkaccess.aux_input import AuxInput
from pyzkaccess.event import Event
from pyzkaccess.exceptions import ZKSDKError
from pyzkaccess.enums import RelayGroup

MockZKSDKError = ZKSDKError

class MockZKAccess:
    """
    Mock implementation of ZKAccess class from pyzkaccess
    
    This class simulates the behavior of the real ZKAccess class
    by providing mock implementations of its key methods and properties.
    It uses the actual model classes from the SDK for better test fidelity.
    """
    
    def __init__(self, connstr: str, device_model: Type[ZKDevice]):
        self.connstr = connstr
        self.device_model = device_model
        self.connected = True
        
        self.conn_params = {}
        parts = connstr.split(',')
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                self.conn_params[key.lower()] = value
        
        self.parameters = MagicMock()
        self.parameters.serial_number = f"MOCK{datetime.now().strftime('%Y%m%d')}"
        self.parameters.ip_address = self.conn_params.get('ipaddress', '127.0.0.1')
        self.parameters.datetime = datetime.now()
        self.parameters.mac_address = "00:11:22:33:44:55"
        self.parameters.firmware_version = "1.0.0"
        
        self._setup_device_components()
        
        self.events = MagicMock()
        self.events.poll = MagicMock(side_effect=self._poll_events)
        
        self.poll_call_count = 0
        self._event_queue = []
    
    def _setup_device_components(self):
        self.doors = []
        for i in range(1, 3):  # Two doors
            door = MagicMock(spec=Door)
            door.number = i
            door.parameters = MagicMock()
            door.parameters.lock_driver_time = 5 if i % 2 == 0 else 10
            door.parameters.sensor_type = 0
            door.parameters.door_name = f"Door {i}"
            self.doors.append(door)
        
        self.readers = []
        for i in range(1, 3):  # Two readers
            reader = MagicMock(spec=Reader)
            reader.number = i
            reader.parameters = MagicMock()
            reader.parameters.reader_type = 0
            reader.parameters.reader_name = f"Reader {i}"
            self.readers.append(reader)
        
        self.relays = []
        relay_groups = [RelayGroup.lock, RelayGroup.aux]
        for i in range(1, 3):  # Two relays
            relay = MagicMock(spec=Relay)
            relay.number = i
            relay.group = relay_groups[i-1]
            self.relays.append(relay)
        
        self.aux_inputs = []
        for i in range(1, 3):  # Two aux inputs
            aux_input = MagicMock(spec=AuxInput)
            aux_input.number = i
            aux_input.parameters = MagicMock()
            aux_input.parameters.aux_name = f"AUX {i}"
            aux_input.parameters.sensor_type = 0
            self.aux_inputs.append(aux_input)
    
    def add_events_to_queue(self, events: List[Event]):
        self._event_queue.extend(events)
        
    def _poll_events(self, *args, **kwargs):
        self.poll_call_count += 1
        if not self._event_queue:
            return []
        
        events_to_return = self._event_queue[:10]
        self._event_queue = self._event_queue[10:]
        return events_to_return
    
    def disconnect(self):
        self.connected = False
        
    def connect(self):
        self.connected = True
        
    def generate_fake_event(self, event_code: int, door_number: int, card_id: Optional[str] = None):
        # Create a simple mock for event type to avoid compatibility issues with EVENT_TYPES
        event_type = MagicMock()
        event_type.value = event_code
        
        if event_code == 0:
            event_type.doc = "Normal Open"
        elif event_code == 1:
            event_type.doc = "Card Authorization"
        elif event_code == 201:
            event_type.doc = "Door Closed"
        elif event_code == 220:
            event_type.doc = "Aux Input Point Disconnected"
        elif event_code == 221:
            event_type.doc = "Aux Input Point Connected"
        else:
            event_type.doc = f"Event Code {event_code}"
        
        verify_mode = None
        if card_id:
            # Create a simple mock for verify mode to avoid enum compatibility issues
            verify_mode = MagicMock()
            verify_mode.name = "Card"
        
        entry_exit = None
        if card_id:
            entry_exit = MagicMock()
            entry_exit.name = "Entry"
        
        event = MagicMock(spec=Event)
        event.event_type = event_type
        event.door = str(door_number)
        event.time = datetime.now()
        event.card = card_id
        event.pin = None
        event.verify_mode = verify_mode
        event.entry_exit = entry_exit
        
        return event
