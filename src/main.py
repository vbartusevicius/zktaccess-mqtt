import signal
import sys
import time
import logging
from typing import Optional, Any
import schedule
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(raise_error_if_not_found=True))

import settings
import mqtt_handler
import ha_discovery
import zkt_handler
import scheduler

numeric_level = getattr(logging, settings.LOG_LEVEL)
logging.basicConfig(level=numeric_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

shutdown_requested = False
def handle_signal(signum): 
    global shutdown_requested
    shutdown_requested = True

def safe_get_attr(obj: Any, attr_name: str, default: Any = None) -> Any:
    return getattr(obj, attr_name, default) if obj else default

def main():
    log.info(" Starting ZKTeco to MQTT Bridge Service")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    device_definition: Optional[zkt_handler.DeviceDefinition] = None
    try: 
        device_definition = zkt_handler.get_device_definition()
    except Exception as e: 
        log.exception(f"Critical error fetching definition: {e}. Exiting.", exc_info=True)
        sys.exit(1)

    serial_number = device_definition.parameters.serial_number
    resolved_ha_identifier = f"zkt_{serial_number}"
    mqtt_client = mqtt_handler.setup_mqtt_client(resolved_ha_identifier)
    if not mqtt_client: 
        log.critical("Fatal: Failed MQTT init.")
        sys.exit(1)
    mqtt_client.loop_start()

    connection_timeout_seconds = 15
    wait_start_time = time.monotonic()
    while not mqtt_client.is_connected():
        if shutdown_requested: 
            mqtt_client.loop_stop()
            sys.exit(1)
        if time.monotonic() - wait_start_time > connection_timeout_seconds: 
            mqtt_client.loop_stop()
            sys.exit(1)
        time.sleep(0.5)
    log.info("MQTT Connected.")

    if not shutdown_requested:
        ha_discovery.publish_discovery_messages(mqtt_client, device_definition, resolved_ha_identifier)
        scheduler.publish_initial_state(mqtt_client, device_definition)
        schedule.every(settings.POLLING_INTERVAL_SECONDS).seconds.do(
            scheduler.polling_job, 
            mqtt_client=mqtt_client, 
            serial_number=serial_number
        )

    log.info("Starting scheduler loop. Ctrl+C to exit.")
    while not shutdown_requested: 
        schedule.run_pending()
        time.sleep(min(1.0, schedule.idle_seconds() if schedule.next_run else 1.0))

    schedule.clear()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    sys.exit(0)

if __name__ == "__main__":
    main()