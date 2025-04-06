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
from scheduler import polling_job

log_level_name = settings.LOG_LEVEL
numeric_level = getattr(logging, log_level_name, logging.INFO)
logging.basicConfig(level=numeric_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

shutdown_requested = False
def handle_signal(signum, frame): 
    global shutdown_requested
    if not shutdown_requested: 
        log.info(f"Received signal {signum}. Shutting down...")
        shutdown_requested = True
    else: 
        log.info("Shutdown already requested.")

def safe_get_attr(obj: Any, attr_name: str, default: Any = None) -> Any:
    return getattr(obj, attr_name, default) if obj else default

def main():
    log.info("=========================================")
    log.info(" Starting ZKTeco to MQTT Bridge Service")
    log.info(f" Log Level: {log_level_name}")
    log.info("=========================================")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    device_definition: Optional[zkt_handler.DeviceDefinition] = None
    try: 
        device_definition = zkt_handler.get_device_definition()
    except Exception as e: 
        log.exception(f"Critical error fetching definition: {e}. Exiting.", exc_info=True)
        sys.exit(1)

    serial_number = safe_get_attr(device_definition.parameters, 'serial_number')
    resolved_ha_identifier = f"zkt_{serial_number}"

    mqtt_client = mqtt_handler.setup_mqtt_client(resolved_ha_identifier)
    if not mqtt_client: 
        log.critical("Fatal: Failed MQTT init.")
        sys.exit(1)
    mqtt_client.loop_start()
    log.info("MQTT client loop started.")
    log.info("Waiting for MQTT connection...")
    connection_timeout_seconds = 15
    wait_start_time = time.monotonic()

    while not mqtt_client.is_connected():
        if shutdown_requested: 
            log.warning("Shutdown during MQTT connect.")
            mqtt_client.loop_stop()
            sys.exit(1)
        if time.monotonic() - wait_start_time > connection_timeout_seconds: 
            log.critical(f"Fatal: MQTT timeout ({connection_timeout_seconds}s).")
            mqtt_client.loop_stop()
            sys.exit(1)
        time.sleep(0.5)
    log.info("MQTT Connected.")

    if not shutdown_requested:
        ha_discovery.publish_discovery_messages(mqtt_client, device_definition, resolved_ha_identifier)
        schedule.every(settings.POLLING_INTERVAL_SECONDS).seconds.do(polling_job, mqtt_client=mqtt_client, ha_identifier=resolved_ha_identifier)

    log.info("Starting scheduler loop. Ctrl+C to exit.")
    while not shutdown_requested: 
        schedule.run_pending()
        time.sleep(min(1.0, schedule.idle_seconds() if schedule.next_run else 1.0))


    log.info("Scheduler loop exited. Cleaning up.")
    schedule.clear()
    log.info("Stopping MQTT loop.")
    mqtt_client.loop_stop()
    log.info("Disconnecting MQTT...")
    mqtt_client.disconnect()
    log.info("Application stopped gracefully.")
    log.info("=========================================")
    sys.exit(0)

if __name__ == "__main__":
    main()