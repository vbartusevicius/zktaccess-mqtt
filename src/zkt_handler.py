import logging
from typing import List, Optional

from pyzkaccess import ZKAccess
from pyzkaccess.event import Event
from pyzkaccess.exceptions import ZKSDKError
from pyzkaccess.device import ZK100, ZK200, ZK400
from pyzkaccess.param import DeviceParameters
from pyzkaccess.door import Door
from pyzkaccess.reader import Reader

import settings

log = logging.getLogger(__name__)

connstr = (
    f"protocol=TCP,ipaddress={settings.ZKT_DEVICE_IP},"
    f"port={settings.ZKT_DEVICE_PORT},"
    f"timeout={settings.ZKT_INTERNAL_TIMEOUT},"
    f"passwd={settings.ZKT_DEVICE_PASSWORD}"
)

model_map = {
    'ZK100': ZK100,
    'ZK200': ZK200,
    'ZK400': ZK400,
}

device_class = model_map.get(settings.ZKT_DEVICE_MODEL.upper())
if device_class is None:
    device_class = ZK100

def poll_zkteco_changes() -> Optional[List[Event]]:
    log.info(f"Polling ZKTeco device at {settings.ZKT_DEVICE_IP}:{settings.ZKT_DEVICE_PORT}...")

    new_events: List[Event] = []
    try:
        with ZKAccess(connstr=connstr, device_model=device_class) as zk:
            log.info("Successfully connected to ZKTeco device.")
            new_events = zk.events.refresh()

            if new_events:
                log.info(f"Found {len(new_events)} new event(s).")
            else:
                log.info("No new events found.")

        log.info("Disconnected from ZKTeco device.")
        return new_events

    except ImportError as e:
        log.critical(f"Fatal Error: Failed to import ZKAccess or dependency: {e}. Is pyzkaccess installed and {settings.ZKT_DLL_PATH} accessible?")
        return None
    except ZKSDKError as e:
        log.error(f"ZK SDK Error during communication: Code={e.err}, Message={e}")
        return None
    except ConnectionRefusedError:
        log.error(f"Connection refused by ZKTeco device {settings.ZKT_DEVICE_IP}:{settings.ZKT_DEVICE_PORT}")
        return None
    except TimeoutError:
        log.error(f"Connection timeout to ZKTeco device {settings.ZKT_DEVICE_IP}:{settings.ZKT_DEVICE_PORT}")
        return None
    except Exception as e:
        log.exception(f"Unexpected error during ZKTeco communication: {e}", exc_info=True)
        return None

def get_device_definition() -> DeviceDefinition:
    definition = None

    with ZKAccess(connstr=connstr, device_model=device_class) as zk:
        definition = DeviceDefinition(zk.parameters, zk.doors, zk.readers)
        
    return definition

class DeviceDefinition:
    def __init__(self, parameters: DeviceParameters, doors: List[Door], readers: List[Reader]):
        self.parameters = parameters
        self.doors = doors
        self.readers = readers
