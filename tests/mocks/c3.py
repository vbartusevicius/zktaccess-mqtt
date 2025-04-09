from c3.consts import EventType as C3EventType, VerificationMode, InOutDirection
import datetime

class MockEventRecord:
    """Mock implementation of C3's EventRecord"""
    def __init__(
        self, 
        port_nr=1, 
        card_no=0, 
        pin=0, 
        event_type=C3EventType.NORMAL_PUNCH_OPEN, 
        verified=VerificationMode.CARD, 
        in_out_state=InOutDirection.ENTRY
    ):
        self.port_nr = port_nr
        self.card_no = card_no
        self.pin = pin
        self.event_type = event_type
        self.verified = verified
        self.in_out_state = in_out_state
        self.time_second = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    def __repr__(self):
        return (f"Realtime Event:\n"
                f"time_second {self.time_second}\n"
                f"event_type {self.event_type.value} {self.event_type}\n"
                f"in_out_state {self.in_out_state.value} {self.in_out_state}\n"
                f"verified {self.verified.value} {self.verified}\n"
                f"card_no {self.card_no}\n"
                f"port_no {self.port_nr}")

class MockC3:
    """Mock implementation of C3 class"""
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.connected = False
        self.serial_number = "TEST123456"
        self._event_queue = []
        
    def connect(self, password=None):
        self.connected = True
        return True
        
    def disconnect(self):
        self.connected = False
        
    def get_device_param(self, params):
        return {
            "~SerialNumber": self.serial_number,
            "LockCount": "2",
            "ReaderCount": "2",
            "AuxInCount": "2",
            "AuxOutCount": "2"
        }
        
    def add_events_to_queue(self, events):
        self._event_queue.extend(events)
        
    def get_rt_log(self):
        if not self._event_queue:
            return []
        events = self._event_queue.copy()
        self._event_queue = []
        return events
        
    def generate_event(self, port_nr=1, card_no=0, event_type=C3EventType.NORMAL_PUNCH_OPEN, verified=VerificationMode.CARD):
        return MockEventRecord(port_nr=port_nr, card_no=card_no, event_type=event_type, verified=verified)