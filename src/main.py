import os
import sys
import logging
from pyzkaccess import ZKAccess
from dotenv import load_dotenv, find_dotenv

env = find_dotenv(raise_error_if_not_found=True)
print(env)
load_dotenv(env)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DEVICE_IP = os.getenv('DEVICE_IP')
DEVICE_PORT = int(os.getenv('DEVICE_PORT', 4370))
DEVICE_TIMEOUT = int(os.getenv('DEVICE_TIMEOUT', 4000))
DEVICE_PASSWORD = os.getenv('DEVICE_PASSWORD', '')

conn = None

try:
    logging.info(f"Attempting to connect to device at {DEVICE_IP}:{DEVICE_PORT} using pyzkaccess...")
    # Consult pyzkaccess docs for exact connection syntax
    # This is a guess based on typical patterns - ADJUST AS NEEDED
    zk = ZKAccess(
        connstr=f'protocol=TCP,ipaddress={DEVICE_IP},port={DEVICE_PORT},timeout={DEVICE_TIMEOUT},passwd={DEVICE_PASSWORD}',
    ) # Check password format

    logging.info("Connection object created (actual connection may happen on first command).")

    logging.info(f"Device SN: {zk.parameters.serial_number}, IP: {zk.parameters.ip_address}")

    users = zk.table('User')
    if users:
        # Process users
        for user in users[:5]:
            logging.info(f" User: {user}") # Adjust based on actual user object structure
    else:
        logging.info("No users found or failed to retrieve.")

except Exception as e:
    logging.error(f"Error connecting or communicating with device: {e}", exc_info=True)
    sys.exit(1) # Exit with error code
finally:
    if conn: # Or however pyzkaccess handles explicit disconnect if needed
        logging.info("Disconnecting (if applicable).")
        # zk.disconnect() # Check pyzkaccess docs for disconnect method
    logging.info("Script finished.")
