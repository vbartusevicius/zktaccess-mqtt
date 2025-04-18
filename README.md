# ZKTeco MQTT Bridge

A Python application that connects to ZKTeco access control devices (C3-series) and publishes their events to MQTT, with built-in Home Assistant integration through MQTT Discovery.

## Features

- 🔌 Connects to ZKTeco C3-series access control devices
- 📊 Publishes device events to MQTT
- 🏠 Home Assistant auto-discovery for easy integration
- 🚪 Monitor doors, relays, aux inputs, card readers
- 🔄 Configurable polling interval
- 🌐 Timezone support for event timestamps

## Requirements

- Python 3.10+
- MQTT Broker (like Mosquitto)
- ZKTeco access control system

## Installation

### Using Docker Compose (Recommended)

```yaml
services:
  zktaccess:
    image: valentas/zkteco-mqtt-gateway:latest
    platform: linux/amd64
    container_name: zktaccess
    environment:
      - DEVICE_IP=192.168.1.201
      - DEVICE_PORT=4370
    #   - DEVICE_PASSWORD=
    #   - MQTT_BROKER_HOST=localhost
    #   - MQTT_BROKER_PORT=1883
    #   - MQTT_USERNAME=
    #   - MQTT_PASSWORD=
    #   - MQTT_CLIENT_ID=
    #   - POLLING_INTERVAL_SECONDS=60
    #   - LOG_LEVEL=INFO
    #   - TIME_ZONE=UTC
    #   - HA_DISCOVERY_PREFIX=homeassistant
    #   - HA_DEVICE_IDENTIFIER=
    #   - HA_DEVICE_NAME=
    #   - HA_DEVICE_MANUFACTURER=ZKTeco
    #   - HA_DEVICE_SW_VERSION=zk_mqtt_bridge_1.0
```

```bash
docker compose up
```


### Building yourself

1. Clone this repository
2. Copy `dist.env` to `.env` and configure your settings
3. Build and run with Docker Compose:

```bash
docker compose up --build
```


## Configuration

All configuration is done through environment variables, which can be set in the `.env` file or passed as environment variables to the container. Below is a description of all available configuration options:

### ZKAccess Device Connection

| Variable | Description | Default |
|----------|-------------|---------|
| `DEVICE_IP` | **(Required)** IP Address of your ZKAccess controller | - |
| `DEVICE_PORT` | Port for the ZKAccess device | `4370` |
| `DEVICE_PASSWORD` | Communication Password (if set) | empty |
| `DEVICE_MODEL` | Device Model - Defaults to C3 if unset or invalid. | `C3` |

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
zkt_eco/[MODEL_NAME]/[SERIAL_NUMBER]/[ENTITY]/state
```

Where:
- MODEL_NAME: The configured device model (default: "C3")
- SERIAL_NUMBER: The device's serial number
- ENTITY: Entity type and ID (e.g., door_1, reader_2_card)

## Running tests

```bash
docker compose run --rm zktaccess pytest
```

## Build options

The project supports two build modes:

1. **Development build** - Includes testing dependencies (default for docker-compose)
   ```bash
   # Using docker-compose (automatically includes dev dependencies)
   docker compose build
   
   # Using Docker directly with dev dependencies
   docker build --build-arg INSTALL_DEV=true -t zktaccess .
   ```

2. **Production build** - Minimal footprint without dev dependencies
   ```bash
   # Default Docker build excludes dev dependencies
   docker build -t zktaccess .
   ```

## Troubleshooting

### Connection Issues

- Ensure the ZKAccess device is powered on and accessible on the network
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

- Built using the zkaccess-c3 library for ZKTeco C3-series device communication
- Inspired by other ZKTeco integration projects
