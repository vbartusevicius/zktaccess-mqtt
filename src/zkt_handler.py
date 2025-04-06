import logging
from typing import List, Optional, Type, Dict

from pyzkaccess import ZKAccess
from pyzkaccess.event import Event
from pyzkaccess.exceptions import ZKSDKError
from pyzkaccess.device import ZKDevice, ZK100, ZK200, ZK400
from pyzkaccess.param import DeviceParameters
from pyzkaccess.door import Door
from pyzkaccess.reader import Reader
from pyzkaccess.relay import Relay
from pyzkaccess.aux_input import AuxInput

import settings

log = logging.getLogger(__name__)

class DeviceDefinition:
    """Simple container for device parameters, doors, and readers."""
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

CONNSTR = (
    f"protocol=TCP,ipaddress={settings.ZKT_DEVICE_IP},"
    f"port={settings.ZKT_DEVICE_PORT},"
    f"timeout={settings.ZKT_INTERNAL_TIMEOUT},"
    f"passwd={settings.ZKT_DEVICE_PASSWORD}"
)

MODEL_MAP: Dict[str, Type[ZKDevice]] = {
    'ZK100': ZK100,
    'ZK200': ZK200,
    'ZK400': ZK400,
}

DEVICE_CLASS = MODEL_MAP.get(settings.ZKT_DEVICE_MODEL.upper(), ZK100)

def poll_zkteco_changes() -> Optional[List[Event]]:
    log.info(f"Polling ZKTeco device at {settings.ZKT_DEVICE_IP}:{settings.ZKT_DEVICE_PORT}...")
    new_events: List[Event] = []
    try:
        with ZKAccess(connstr=CONNSTR, device_model=DEVICE_CLASS) as zk:
            log.info("Successfully connected to ZKTeco device for polling.")
            new_events = zk.events.refresh()
            if new_events:
                log.info(f"Found {len(new_events)} new event(s).")
            else:
                log.info("No new events found during refresh.")
        log.debug("Disconnected from ZKTeco device after polling.")
        return new_events

    except ImportError as e: 
        log.critical(f"Fatal Error: ZKAccess import failed: {e}. Check pyzkaccess install & {settings.ZKT_DLL_PATH}.")
        return None
    except ZKSDKError as e: 
        log.error(f"ZK SDK Error during polling: Code={e.err}, Message={e}")
        return None
    except ConnectionRefusedError: 
        log.error(f"Polling: Connection refused by ZKTeco device {settings.ZKT_DEVICE_IP}:{settings.ZKT_DEVICE_PORT}")
        return None
    except TimeoutError: 
        log.error(f"Polling: Connection timeout to ZKTeco device {settings.ZKT_DEVICE_IP}:{settings.ZKT_DEVICE_PORT}")
        return None
    except Exception as e: 
        log.exception(f"Unexpected error during ZKTeco polling: {e}", exc_info=True)
        return None

def get_device_definition() -> Optional[DeviceDefinition]:

    log.info(f"Attempting to fetch device definition from {settings.ZKT_DEVICE_IP}...")
    definition: Optional[DeviceDefinition] = None
    try:
        with ZKAccess(connstr=CONNSTR, device_model=DEVICE_CLASS) as zk:
            log.info("Successfully connected to ZKTeco device for definition fetch.")
            parameters = getattr(zk, 'parameters', None)
            doors = getattr(zk, 'doors', [])
            readers = getattr(zk, 'readers', [])
            relays = getattr(zk, 'relays', [])
            aux_inputs = getattr(zk, 'aux_inputs', [])

            definition = DeviceDefinition(parameters, doors, readers, relays, aux_inputs)

            sn = getattr(parameters, 'serial_number', 'N/A') if parameters else 'N/A'
            num_doors = len(doors) if doors else 0
            num_readers = len(readers) if readers else 0
            num_relays = len(relays) if relays else 0
            num_aux = len(aux_inputs) if aux_inputs else 0
            log.info(f"Fetched Definition: SN={sn}, Doors={num_doors}, Readers={num_readers}, Relays={num_relays}, AuxInputs={num_aux}")

        log.debug("Disconnected from ZKTeco device after fetching definition.")
        return definition

    except ImportError as e: 
        log.critical(f"Fatal Error: ZKAccess import failed: {e}.")
        raise
    except (ZKSDKError, ConnectionRefusedError, TimeoutError) as e: 
        log.error(f"Failed to connect/communicate for device definition: {type(e).__name__} - {e}")
        raise
    except Exception as e: 
        log.exception(f"Unexpected error fetching device definition: {e}", exc_info=True)
        raise
