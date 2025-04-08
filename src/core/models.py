from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from pyzkaccess.event import Event
from pyzkaccess.param import DeviceParameters
from pyzkaccess.door import Door
from pyzkaccess.reader import Reader
from pyzkaccess.relay import Relay
from pyzkaccess.aux_input import AuxInput

class DeviceDefinition:
    def __init__(
        self,
        parameters: Optional[DeviceParameters],
        doors: Optional[List[Door]],
        readers: Optional[List[Reader]],
        relays: Optional[List[Relay]],
        aux_inputs: Optional[List[AuxInput]]
    ):
        self.parameters = parameters
        self.doors = doors or []
        self.readers = readers or []
        self.relays = relays or []
        self.aux_inputs = aux_inputs or []

    @property
    def serial_number(self) -> str:
        return self.parameters.serial_number if self.parameters else "unknown"

class EventType(Enum):
    CARD_SCAN_SUCCESS = "card_scan_success"
    CARD_SCAN_DENIED = "card_scan_denied"
    CARD_SCAN_INVALID = "card_scan_invalid"
    PIN_SUCCESS = "pin_success"
    PIN_DENIED = "pin_denied"
    FINGERPRINT_SUCCESS = "fingerprint_success"
    FINGERPRINT_DENIED = "fingerprint_denied"
    FINGERPRINT_INVALID = "fingerprint_invalid"
    DOOR_OPEN = "door_open"
    DOOR_CLOSE = "door_close"
    DOOR_BUTTON = "door_button"
    AUX_INPUT_CONNECTED = "aux_input_connected"
    AUX_INPUT_DISCONNECTED = "aux_input_disconnected"
    OTHER_SUCCESS = "other_success"
    OTHER = "other"

@dataclass
class ProcessedEvent:
    event_type: EventType
    door_id: int
    reader_id: int
    timestamp: datetime
    card_id: Optional[str] = None
    pin: Optional[str] = None
    verify_mode: Optional[str] = None
    entry_exit: Optional[str] = None 
    zk_event_code: Optional[int] = None
    zk_event_desc: Optional[str] = None
    raw_event: Optional[Event] = None
    additional_attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntityState:
    entity_id: str
    state: str
    attributes: Optional[Dict[str, Any]] = None
