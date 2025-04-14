import signal
import sys
import time
import logging
from typing import Optional
import schedule
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(raise_error_if_not_found=True))

import settings
from zkt import handler as zkt_handler
from mqtt import handler as mqtt_handler
from ha_integration import discovery as ha_discovery
from scheduler.jobs import JobScheduler
from mqtt.publisher import MQTTPublisher
from core.models import DeviceDefinition

numeric_level = getattr(logging, settings.LOG_LEVEL)
logging.basicConfig(level=numeric_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

shutdown_requested = False

def handle_signal(signum, frame):
    global shutdown_requested
    log.info(f"Received signal {signum}, initiating shutdown")
    shutdown_requested = True

def main():
    log.info("Starting ZKTeco to MQTT Bridge Service")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    device_definition: Optional[DeviceDefinition] = None
    try: 
        device_definition = zkt_handler.get_device_definition()
    except Exception as e: 
        log.exception(f"Critical error fetching device definition: {e}. Exiting.", exc_info=True)
        sys.exit(1)

    serial_number = device_definition.serial_number
    device_identifier = f"zkt_{serial_number}"
    
    mqtt_client = mqtt_handler.setup_mqtt_client(device_identifier)
    if not mqtt_client: 
        log.critical("Fatal: Failed to initialize MQTT client.")
        sys.exit(1)
    
    mqtt_client.loop_start()

    connection_timeout_seconds = 15
    wait_start_time = time.monotonic()
    while not mqtt_client.is_connected():
        if shutdown_requested: 
            mqtt_client.loop_stop()
            sys.exit(1)
        if time.monotonic() - wait_start_time > connection_timeout_seconds: 
            log.critical(f"MQTT connection timeout after {connection_timeout_seconds} seconds")
            mqtt_client.loop_stop()
            sys.exit(1)
        time.sleep(0.5)
    log.info("MQTT Connected.")

    if not shutdown_requested:
        ha_discovery.publish_discovery_messages(mqtt_client, device_definition, device_identifier)
        
        publisher = MQTTPublisher(mqtt_client, serial_number)
        job_scheduler = JobScheduler(publisher)
        
        job_scheduler.initialize_states(device_definition)
        
        schedule.every(settings.POLLING_INTERVAL_SECONDS).seconds.do(job_scheduler.polling_job)
        schedule.every(1).days.do(job_scheduler.time_update_job)

    log.info("Starting scheduler loop. Ctrl+C to exit.")
    while not shutdown_requested: 
        schedule.run_pending()
        time.sleep(min(1.0, schedule.idle_seconds() if schedule.next_run else 1.0))

    log.info("Shutting down...")
    schedule.clear()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    zkt_handler.close_zkteco_connection()
    log.info("Shutdown complete")
    sys.exit(0)

if __name__ == "__main__":
    main()