import pytest
import sys
import os
import logging
from unittest.mock import patch

src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

@pytest.fixture(autouse=True)
def setup_test_env():
    logging.basicConfig(level=logging.DEBUG)
    
    env_vars = {
        "ZKT_DEVICE_IP": "192.168.1.201",
        "ZKT_DEVICE_PORT": "4370",
        "ZKT_DEVICE_PASSWORD": "test",
        "ZKT_DEVICE_MODEL": "ZK400",
        "ZKT_INTERNAL_TIMEOUT": "4000",
        "MQTT_BROKER_HOST": "localhost",
        "MQTT_BROKER_PORT": "1883",
        "HA_DISCOVERY_PREFIX": "homeassistant",
        "HA_DEVICE_NAME": "Test ZKTeco Controller",
        "TIMEZONE": "UTC",
        "POLLING_INTERVAL_SECONDS": "1",
        "LOG_LEVEL": "DEBUG"
    }
    
    with patch.dict(os.environ, env_vars):
        yield
