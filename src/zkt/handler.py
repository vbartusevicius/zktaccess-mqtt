import logging
from typing import List, Optional
from c3 import C3
from c3.rtlog import EventRecord

import settings
from core.models import DeviceDefinition

log = logging.getLogger(__name__)

panel: Optional[C3] = None

def poll_zkteco_changes() -> Optional[List[EventRecord]]:
    global panel
    log.info(f"Polling ZKTeco device at {settings.ZKT_DEVICE_IP}:{settings.ZKT_DEVICE_PORT}...")
    new_events: List[EventRecord] = []
    
    try:
        if not ensure_connection():
            return None
        
        new_events = panel.get_rt_log()
        log.info(f"Retrieved {len(new_events)} events from device")
        return new_events
    except ConnectionRefusedError: 
        log.error(f"Polling: Connection refused by ZKTeco device {settings.ZKT_DEVICE_IP}:{settings.ZKT_DEVICE_PORT}")
        return None
    except TimeoutError: 
        log.error(f"Polling: Connection timeout to ZKTeco device {settings.ZKT_DEVICE_IP}:{settings.ZKT_DEVICE_PORT}")
        return None
    except Exception as e: 
        log.exception(f"Unexpected error during ZKTeco polling: {e}", exc_info=True)
        return None

def ensure_connection() -> bool:
    global panel
    
    try:
        if panel is not None:
            try:
                panel.get_device_param(["~SerialNumber"])
                return True
            except Exception:
                close_zkteco_connection()
        
        log.info(f"Connecting to ZKTeco device at {settings.ZKT_DEVICE_IP}:{settings.ZKT_DEVICE_PORT}...")
        panel = C3(settings.ZKT_DEVICE_IP, settings.ZKT_DEVICE_PORT)
        
        if settings.ZKT_DEVICE_PASSWORD:
            connected = panel.connect(settings.ZKT_DEVICE_PASSWORD)
        else:
            connected = panel.connect()
            
        if connected:
            log.info("Successfully connected to ZKTeco device")
            return True
        else:
            panel = None
            raise Exception("Failed to connect to ZKTeco device")
            
    except Exception as e:
        log.exception(f"Error establishing connection to device: {e}")
        panel = None
        raise

def get_device_definition() -> Optional[DeviceDefinition]:
    global panel
    definition: Optional[DeviceDefinition] = None
    
    try:
        ensure_connection()
            
        # Retrieve device parameters using C3 library
        params = [
            "~SerialNumber",  # Serial number
            "LockCount",      # Number of doors/locks
            "ReaderCount",    # Number of readers
            "AuxInCount",     # Number of auxiliary inputs
            "AuxOutCount",    # Number of auxiliary outputs
            "FirmVer"         # Firmware version
        ]
        
        parameters = panel.get_device_param(params)
        log.debug(f"Retrieved parameters: {parameters}")
        
        serial_number = parameters.get("~SerialNumber", "N/A")
        lock_count = int(parameters.get("LockCount", 0))
        reader_count = int(parameters.get("ReaderCount", 0))
        aux_in_count = int(parameters.get("AuxInCount", 0))
        aux_out_count = int(parameters.get("AuxOutCount", 0))
        firmware_version = parameters.get("FirmVer", "N/A")
        
        doors = [{'number': i+1, 'name': f'Door {i+1}'} for i in range(lock_count)]
        readers = [{'number': i+1, 'name': f'Reader {i+1}'} for i in range(reader_count)]
        relays = [{'number': i+1, 'name': f'Relay {i+1}'} for i in range(aux_out_count)]
        aux_inputs = [{'number': i+1, 'name': f'AuxInput {i+1}'} for i in range(aux_in_count)]
        
        param_obj = {
            'serial_number': serial_number,
            'firmware_version': firmware_version
        }
        
        definition = DeviceDefinition(param_obj, doors, readers, relays, aux_inputs)
        
        log.info(f"Fetched Definition: SN={serial_number}, Doors={lock_count}, "
                 f"Readers={reader_count}, Relays={aux_out_count}, AuxInputs={aux_in_count}")
        
        log.debug(f"Definition: {definition}")

        return definition

    except Exception as e: 
        log.exception(f"Unexpected error fetching device definition: {e}", exc_info=True)
        raise

def close_zkteco_connection():
    global panel
    if panel is not None:
        try:
            panel.disconnect()
        except Exception as e:
            log.warning(f"Error when disconnecting from ZKTeco device: {e}")
        finally:
            panel = None
            log.debug("Closed connection to ZKTeco device")
