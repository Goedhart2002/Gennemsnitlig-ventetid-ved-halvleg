# Phase 3 Runtime Guide (MQTT Publishing)

This guide documents Phase 3 where the spectator agent publishes simulation events to MQTT.

## 1. What Was Created

### Notebooks and Scripts
- Updated notebook: `notebooks/agent_spectator_flow.ipynb`
- Added tests: `tests/test_phase3_mqtt_publish.py`

### Library Modules in `src/simulated_city/`
- Added: `topic_schema.py`
  - `topic_spectator_events()`
- Added: `mqtt_payloads.py`
  - `build_spectator_event_payload(...)`
  - `validate_spectator_event_payload(...)`
- Updated: `mqtt.py`
  - `connect_mqtt(mqtt_config)`
  - `publish_json_checked(client, topic, data)`

### Configuration Changes (`config.yaml`)
- No new config keys were required in Phase 3.
- MQTT connection still uses existing `mqtt.*` config and profiles.

## 2. How to Run

### Workflow A: Start broker and run publishing notebook
1. Ensure your MQTT broker is running (for local profile: `127.0.0.1:1883`).
2. Start JupyterLab from repository root:
   - `.venv/bin/python -m jupyterlab`
3. Open `notebooks/agent_spectator_flow.ipynb`.
4. Run cells 1-7 in order.

Expected behavior by cell:
- Cell 1: phase title and scope.
- Cell 2: imports MQTT/config/simulation modules.
- Cell 3: loads config and prints parameters.
- Cell 4: runs simulation and prints KPI values.
- Cell 5: connects to broker and prints topic/run metadata.
- Cell 6: publishes event payloads to MQTT.
- Cell 7: prints queue summary and disconnects MQTT client.

### Workflow B: Observe MQTT messages
1. In another terminal, run:
   - `mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/events/spectator" -v`
2. Run notebook cells 1-7.
3. Observe JSON messages in subscriber terminal for each published tick sample.

## 3. Expected Output

### Cell 3 (Config Load)
Purpose: load config and print values.

Expected lines include:
- `Loaded halftime parameters from config.yaml:`
- `seed: 42`
- `spectator_count: 1000`
- `halftime_duration_s: 900`
- `toilet_servers: 15`
- `cafe_servers: 10`

If different:
- verify `config.yaml` content
- rerun Cell 3 after config edits
- if `seed` is `null`, run-to-run differences are expected

### Cell 4 (Simulation Run)
Purpose: run simulation and print KPIs.

Expected lines include:
- `Running simulation from config...`
- `Simulation complete: 901 ticks collected`
- `Max Queue Length: 456`
- `Average Wait Time: 227.15 seconds`
- `Missed Kickoff Count: 831`
- `Total Served Tasks: 267`

If different:
- for reproducible baseline numbers, set `seed` in `halftime` section to `42`
- verify you ran Cell 3 before Cell 4

### Cell 5 (MQTT Connect)
Purpose: connect and show publish metadata.

Expected lines include:
- `Connected to MQTT broker at 127.0.0.1:1883` (for local profile)
- `Publish topic: stadium/a4/halftime/events/spectator`
- `run_id: a4-run-<8 hex chars>, schema_version: 1.0`

If different:
- broker may not be running
- active MQTT profile in `config.yaml` may point to another host/port

### Cell 6 (Publish Events)
Purpose: publish validated event messages.

Expected line:
- `Published 181 spectator events to stadium/a4/halftime/events/spectator`

Explanation:
- 901 ticks sampled every 5 seconds gives 181 events.

If different:
- check `publish_every_s` in cell
- ensure broker connectivity from Cell 5

### Cell 7 (Summary + Disconnect)
Purpose: print queue summary and disconnect.

Expected lines include:
- `=== Queue Evolution Summary ===`
- toilet queue summary line
- cafe queue summary line
- `Disconnected from MQTT broker.`
- `=== Phase 3 Complete ===`

## 4. MQTT Topics

### Published topics
- `stadium/a4/halftime/events/spectator`
  - Publisher: `notebooks/agent_spectator_flow.ipynb`
  - One message per sampled tick (`publish_every_s = 5`)

### Subscribed topics
- None in Phase 3 (single publishing agent only).

### Message schema (JSON)
Each published message has this structure:

```json
{
  "schema_version": "1.0",
  "run_id": "a4-run-1a2b3c4d",
  "timestamp_s": 120,
  "spectators_out_of_seat": 431,
  "queue_lengths": {
    "toilet": 211,
    "cafe": 54
  }
}
```

Required envelope fields:
- `schema_version`
- `run_id`
- `timestamp_s`

## 5. Debugging Guidance

### Enable more logs
You can add at top of Cell 2:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Common errors
- `TimeoutError: Could not connect to MQTT broker ...`
  - Start broker or switch to a reachable profile in `config.yaml`.
- `ValueError` from payload validation
  - Ensure required keys and types are unchanged.
- `Published 0 spectator events...`
  - Check broker connectivity and `publish_json_checked` return values.

### Verify message flow
- Use subscriber terminal command:
  - `mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/events/spectator" -v`
- Confirm `run_id` and increasing `timestamp_s` values appear.

## 6. Verification Commands

Run from repository root:

```bash
python scripts/verify_setup.py
python scripts/validate_structure.py
python -m pytest
```
