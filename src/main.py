import signal
import sys
import time
import logging
import schedule

import settings
import mqtt_handler
import ha_discovery
import zk_handler
from scheduler import polling_job

log_level_name = settings.LOG_LEVEL
numeric_level = getattr(logging, log_level_name, logging.INFO)
logging.basicConfig(level=numeric_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

shutdown_requested = False

def handle_signal(signum):
    global shutdown_requested
    if not shutdown_requested:
        log.info(f"Received signal {signum}. Initiating graceful shutdown...")
        shutdown_requested = True
    else:
        log.info("Shutdown already in progress.")

def main():
    log.info("=========================================")
    log.info(" Starting ZKTeco to MQTT Bridge Service")
    log.info("=========================================")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    device = zk_handler.get_device_definition()
    if not device:
        log.critical("Fatal: Failed to retrieve device information. Exiting.")
        sys.exit(1)

    mqtt_client = mqtt_handler.setup_mqtt_client(f"zkteco_bridge_{device.parameters.serial_number}")
    if not mqtt_client:
        log.critical("Fatal: Failed to initialize MQTT client. Exiting.")
        sys.exit(1)

    mqtt_client.loop_start()
    log.info("MQTT client loop started.")

    log.info("Waiting for MQTT connection...")
    connection_timeout_seconds = 15
    wait_start_time = time.monotonic()
    while not mqtt_client.is_connected():
        if shutdown_requested:
            log.warning("Shutdown requested while waiting for MQTT connection.")
            mqtt_client.loop_stop()
            sys.exit(1)
        if time.monotonic() - wait_start_time > connection_timeout_seconds:
            log.critical(f"Fatal: Could not connect to MQTT broker after {connection_timeout_seconds} seconds. Exiting.")
            mqtt_client.loop_stop()
            sys.exit(1)
        time.sleep(0.5)

    log.info("MQTT Connected.")

    ha_discovery.publish_discovery_messages(mqtt_client)

    schedule.every(settings.POLLING_INTERVAL_SECONDS).seconds.do(polling_job, mqtt_client=mqtt_client, device=device)

    while not shutdown_requested:
        schedule.run_pending()
        time.sleep(min(1.0, schedule.idle_seconds() if schedule.next_run else 1.0))

    log.info("Scheduler loop exited. Cleaning up...")
    schedule.clear()

    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    log.info("Application stopped gracefully.")
    log.info("=========================================")
    sys.exit(0)

if __name__ == "__main__":
    main()