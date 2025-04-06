# ZKTeco MQTT Bridge

A Python application that connects to ZKTeco access control devices and publishes their events to MQTT, with built-in Home Assistant integration through MQTT Discovery.

## Features

- 🔌 Connects to ZKTeco devices (C3 and C4 series)
- 📊 Publishes device events to MQTT
- 🏠 Home Assistant auto-discovery for easy integration
- 🚪 Monitor doors, relays, aux inputs, card readers
- ⏰ Time synchronization with the device
- 🔄 Configurable polling interval
- 🌐 Timezone support for event timestamps

## Requirements

- Python 3.8+
- MQTT Broker (like Mosquitto)
- ZKTeco access control system

## Installation

### Using Docker (Recommended)

1. Clone this repository
2. Copy `dist.env` to `.env` and configure your settings
3. Build and run with Docker Compose:

```bash
docker-compose up -d
```

> **IMPORTANT NOTE FOR ARM DEVICES (Apple Silicon, Raspberry Pi, etc.):**  
> The ZKTeco SDK requires Windows. It successfully works on Docker and Wine. When building on ARM devices:
> 
> **Option 1:** Build with platform flag:
> ```bash
> docker build --platform=linux/amd64 -t zkteco-mqtt .
> ```
> 
> **Option 2:** With docker-compose, you may need to disable BuildKit:
> ```bash
> DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 docker-compose up -d
> ```
> 
> These settings ensure the image builds correctly for the x86_64 architecture required by the ZKTeco SDK.


## Configuration

All configuration is done through environment variables, which can be set in the `.env` file or passed as environment variables to the container. Below is a description of all available configuration options:

### ZKTeco Device Connection

| Variable | Description | Default |
|----------|-------------|---------|
| `DEVICE_IP` | **(Required)** IP Address of your ZKTeco controller | - |
| `DEVICE_PORT` | Port for the ZKTeco device | `4370` |
| `DEVICE_PASSWORD` | Communication Password (if set) | empty |
| `DEVICE_TIMEOUT` | Communication timeout in milliseconds | `4000` |
| `DEVICE_MODEL` | Device model (ZK100, ZK200, ZK400) | `ZK100` |

### MQTT Broker Connection

| Variable | Description | Default |
|----------|-------------|---------|
| `MQTT_BROKER_HOST` | **(Required)** Address/Hostname of MQTT broker | `localhost` |
| `MQTT_BROKER_PORT` | Port for your MQTT broker | `1883` |
| `MQTT_USERNAME` | MQTT Username (if auth required) | empty |
| `MQTT_PASSWORD` | MQTT Password (if auth required) | empty |
| `MQTT_CLIENT_ID` | Custom client ID for this instance | auto-generated |

### Application Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `POLLING_INTERVAL_SECONDS` | How often to poll the device for events (seconds) | `60` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | `INFO` |
| `TIME_ZONE` | Timezone for event timestamps (IANA format) | `UTC` |

### Home Assistant Integration

| Variable | Description | Default |
|----------|-------------|---------|
| `HA_DISCOVERY_PREFIX` | Home Assistant MQTT Discovery prefix | `homeassistant` |
| `HA_DEVICE_IDENTIFIER` | Custom device identifier | `zkt_[serial_number]` |
| `HA_DEVICE_NAME` | Custom device name in Home Assistant | `ZKTeco [MODEL] Controller` |
| `HA_DEVICE_MANUFACTURER` | Manufacturer name in Home Assistant | `ZKTeco` |
| `HA_DEVICE_SW_VERSION` | Software version in Home Assistant | `zkt_mqtt_bridge_1.0` |

## Home Assistant Integration

The bridge automatically creates the following entities in Home Assistant via MQTT Discovery:

- **Door Sensors** (`binary_sensor`): Status of each door (open/closed)
- **Auxiliary Inputs** (`binary_sensor`): Status of each auxiliary input
- **Reader Events** (`event`): Card scan events at each reader
- **Reader Cards** (`sensor`): Last card number scanned at each reader
- **Relays** (`binary_sensor`): Status of each relay

All entities are grouped under a single device for easy management and automations.

## MQTT Topics Structure

All MQTT messages use the following topic structure:

```
zkt_eco/[MODEL]/[SERIAL_NUMBER]/[ENTITY]/state
```

## Troubleshooting

### Connection Issues

- Ensure the ZKTeco device is powered on and accessible on the network
- Verify the IP address, port, and password are correct
- Check firewall settings to ensure port 4370 TCP is open
- Set `LOG_LEVEL=DEBUG` for more detailed logs

### MQTT Issues

- Verify your MQTT broker is running and accessible
- Check username/password if authentication is enabled
- Ensure there are no topic conflicts with other devices

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built using the pyzkaccess library for ZKTeco device communication
- Inspired by other ZKTeco integration projects
