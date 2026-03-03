# MQTT

This template includes **paho-mqtt** by default and ships with a committed `config.yaml` that supports **multiple MQTT brokers simultaneously**.

This document focuses on the current Section A4 notebook agents and their MQTT flow.

## Agent/topic map

All topics are defined in `src/simulated_city/topic_schema.py`.

- `notebooks/agent_spectator_flow.ipynb`
  - publishes to `stadium/a4/halftime/events/spectator`
- `notebooks/agent_facility_manager.ipynb`
  - subscribes to `stadium/a4/halftime/events/spectator`
  - publishes to `stadium/a4/halftime/state/queues`
- `notebooks/agent_congestion.ipynb`
  - subscribes to `stadium/a4/halftime/state/queues`
  - publishes to `stadium/a4/halftime/state/congestion`
- `notebooks/agent_metrics.ipynb`
  - subscribes to `stadium/a4/halftime/events/spectator`
  - publishes to `stadium/a4/halftime/metrics/kpi`
- `notebooks/dashboard_a4.ipynb`
  - subscribes to:
    - `stadium/a4/halftime/state/queues`
    - `stadium/a4/halftime/metrics/kpi`
    - `stadium/a4/halftime/state/congestion` (optional)

## Required helper APIs

Use these APIs in notebooks and scripts:

- `mqtt.connect_mqtt(mqtt_config)`
- `mqtt.publish_json_checked(client, topic, data)`

Do not hardcode broker credentials in notebook cells. Load via `simulated_city.config.load_config()` and `.env` variables referenced by `config.yaml`.

## Payload schemas (current)

Schema validation helpers are in `src/simulated_city/mqtt_payloads.py`.

### Spectator events

Topic: `stadium/a4/halftime/events/spectator`

Required keys:

- `schema_version` (string)
- `run_id` (string)
- `timestamp_s` (int)
- `spectators_out_of_seat` (int)
- `queue_lengths.toilet` (int)
- `queue_lengths.cafe` (int)

### Queue state

Topic: `stadium/a4/halftime/state/queues`

Required keys:

- `schema_version`, `run_id`, `timestamp_s`, `source_event_timestamp_s`
- `queues.zone_a.toilet`, `queues.zone_a.cafe`
- `queues.zone_b.toilet`, `queues.zone_b.cafe`
- `queues.shared_mens_urinal`

### Congestion state

Topic: `stadium/a4/halftime/state/congestion`

Required keys:

- `schema_version`, `run_id`, `timestamp_s`
- `zone_a_blocked` (bool)
- `zone_b_blocked` (bool)

### KPI metrics

Topic: `stadium/a4/halftime/metrics/kpi`

Required keys:

- `schema_version`, `run_id`, `timestamp_s`
- `average_wait_s` (number)
- `wait_percentiles_s` with `P01` through `P100`
- `missed_kickoff_count` (int)
- `made_kickoff_count` (int)
- `stayed_seated_count` (int)
- `went_down_count` (int)
- `went_down_made_back_count` (int)

## Recommended notebook startup order

To avoid missing early events, start subscribers before the main publisher:

1. `agent_facility_manager.ipynb`
2. `agent_congestion.ipynb`
3. `agent_metrics.ipynb`
4. `dashboard_a4.ipynb`
5. `agent_spectator_flow.ipynb`

## Quick Start: Using Multiple Brokers

The configuration supports routing different messages to different brokers:

```yaml
mqtt:
  active_profiles: [local, mqtthq]  # Connect to both brokers
  profiles:
    local:
      host: "127.0.0.1"
      port: 1883
      tls: false
    mqtthq:
      host: "broker.mqttdashboard.com"
      port: 1883
      tls: false
```

Then in your code:

```python
from simulated_city.config import load_config

cfg = load_config()

# All configured brokers
for profile_name, broker_cfg in cfg.mqtt_configs.items():
    print(f"{profile_name}: {broker_cfg.host}:{broker_cfg.port}")

# Connect to the primary configured broker in notebooks
primary_cfg = cfg.mqtt
client = mqtt.connect_mqtt(primary_cfg)
```

## Single Broker Setup

If you only want one broker, set:

```yaml
mqtt:
  active_profiles: [local]  # or [mqtthq] for public broker
```

## Configure HiveMQ Cloud

1. Edit `config.yaml` and add a HiveMQ profile:

```yaml
mqtt:
  active_profiles: [local, hivemq_cloud]
  profiles:
    hivemq_cloud:
      host: "xxxxxx.s1.eu.hivemq.cloud"  # Your cluster host
      port: 8883
      tls: true
      username_env: "HIVEMQ_USERNAME"
      password_env: "HIVEMQ_PASSWORD"
```

2. Store credentials in `.env`:

```bash
HIVEMQ_USERNAME=your_username
HIVEMQ_PASSWORD=your_password
```

## Connect from Python

```python
import time
from simulated_city.config import load_config
from simulated_city import mqtt

cfg = load_config().mqtt

# Connect and publish with verification
client = mqtt.connect_mqtt(cfg)
ok = mqtt.publish_json_checked(
  client,
  "stadium/a4/halftime/events/spectator",
  {
    "schema_version": "1.0",
    "run_id": "demo-run",
    "timestamp_s": 1,
    "spectators_out_of_seat": 10,
    "queue_lengths": {"toilet": 3, "cafe": 1},
  },
)
if not ok:
  raise RuntimeError("MQTT publish verification failed")

# Disconnect when done
time.sleep(1)
connector = getattr(client, "_simcity_connector", None)
if connector is not None:
  connector.disconnect()
```

## Monitoring Messages with mosquitto_sub

Use `mosquitto_sub` (part of the mosquitto command-line tools) to monitor messages published to your broker. This is useful for debugging and verifying that agents are publishing correctly.

### Subscribe to a specific topic

To monitor a specific topic (e.g., weather data):

```bash
mosquitto_sub -h localhost -t "simulated_city/weather/rain"
```

Replace `simulated_city/weather/rain` with any topic your agents publish to. Messages appear in real time as they arrive.

### Monitor all messages

To subscribe to all messages on the broker, use the wildcard `#`:

```bash
mosquitto_sub -h localhost -t "#"
```

This displays every message published to any topic, which is helpful for seeing overall system activity.

### Monitor with topic verbosity

To see both the topic name and the message content clearly:

```bash
mosquitto_sub -h localhost -v -t "#"
```

The `-v` flag (verbose) prints the topic name before each message.

### Remote broker monitoring

If your broker is not on localhost, change the host:

```bash
mosquitto_sub -h broker.example.com -t "simulated_city/weather/rain"
```

For TLS-secured brokers, add `--cafile` or other TLS options as needed.

## Troubleshooting checklist

1. Validate setup and dependencies:

```bash
python scripts/verify_setup.py
```

2. Confirm broker profile selection in `config.yaml`:

- `mqtt.active_profiles`
- `mqtt.profiles.<profile>.host`
- `mqtt.profiles.<profile>.port`
- `mqtt.profiles.<profile>.tls`

3. If using credentials, confirm `.env` contains names referenced by:

- `mqtt.profiles.<profile>.username_env`
- `mqtt.profiles.<profile>.password_env`

4. Monitor traffic while running notebooks:

```bash
mosquitto_sub -h 127.0.0.1 -v -t "stadium/a4/halftime/#"
```

5. If dashboard shows no updates, confirm startup order and that `agent_spectator_flow.ipynb` was run last.

## Switching Between Single and Multiple Brokers

You can quickly switch your setup by editing `config.yaml`:

**For local development only:**
```yaml
mqtt:
  active_profiles: [local]
```

**For local + public sharing:**
```yaml
mqtt:
  active_profiles: [local, mqtthq]
```

**For cloud-only (production):**
```yaml
mqtt:
  active_profiles: [hivemq_cloud]
```

Your code doesn't need to change—it automatically detects all active brokers via `cfg.mqtt_configs`.

