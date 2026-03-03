# Phase 4 Runtime Guide (Second Agent with MQTT Subscription)

This guide documents Phase 4 where a new facility-manager agent subscribes to spectator events and publishes queue-state updates.

## 1. What Was Created

### Notebooks and Scripts
- Created notebook: `notebooks/agent_facility_manager.ipynb`
- Updated notebook: `notebooks/agent_spectator_flow.ipynb`
- Added tests: `tests/test_phase4_agent_communication.py`

### Library Modules in `src/simulated_city/`
- Added: `facility_manager.py`
  - `FacilityManagerState`
  - `process_spectator_event(...)`
- Updated: `topic_schema.py`
  - `topic_queue_state()` and queue-state topic constant
- Updated: `mqtt_payloads.py`
  - `build_queue_state_payload(...)`
  - `validate_queue_state_payload(...)`

### Configuration Changes (`config.yaml`)
- No new `config.yaml` keys were required in Phase 4.
- Existing `mqtt.*` and `halftime.*` settings are reused.

## 2. How to Run

### Workflow A: Start spectator publisher then facility manager
1. Start your MQTT broker.
2. Open `notebooks/agent_spectator_flow.ipynb` and run Cells 1-6.
3. Open `notebooks/agent_facility_manager.ipynb` and run Cells 1-5.

Expected behavior:
- Spectator notebook publishes to `stadium/a4/halftime/events/spectator`.
- Facility-manager notebook subscribes to spectator events.
- Facility-manager notebook publishes queue states to `stadium/a4/halftime/state/queues`.

### Workflow B: Observe queue-state topic in terminal
1. Open a terminal and run:
   - `mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/state/queues" -v`
2. Run both notebooks as above.
3. Confirm JSON messages appear with zone and shared-urinal queues.

## 3. Expected Output

### Spectator Notebook

#### Cell 3 (Load Config)
Purpose: load and print config-driven params.

Expected lines include:
- `Loaded halftime parameters from config.yaml:`
- `spectator_count: 1000`
- `halftime_duration_s: 900`

#### Cell 5 (MQTT Connect)
Purpose: connect publisher and print metadata.

Expected lines include:
- `Connected to MQTT broker at 127.0.0.1:1883` (for local profile)
- `Publish topic: stadium/a4/halftime/events/spectator`
- `run_id: a4-run-<8 hex chars>, schema_version: 1.0`

#### Cell 6 (Publish Events)
Purpose: publish spectator events for subscriber agent.

Expected line:
- `Published 181 spectator events to stadium/a4/halftime/events/spectator`

### Facility Manager Notebook

#### Cell 3 (Config + Connect)
Purpose: initialize restart-safe state and MQTT connection.

Expected lines include:
- `Connected to MQTT broker at 127.0.0.1:1883`
- `Subscribed topic: stadium/a4/halftime/events/spectator`
- `Publish topic: stadium/a4/halftime/state/queues`

#### Cell 4 (Subscribe)
Purpose: register callback and start subscription.

Expected line:
- `Subscription started. Waiting for incoming spectator events...`

#### Cell 5 (Processing Summary)
Purpose: process events for a timed window and print results.

Expected lines include:
- `Received spectator events: <number>`
- `Published queue states: <number>`
- `Last published queue-state payload:`
- Printed payload dict with keys:
  - `schema_version`
  - `run_id`
  - `timestamp_s`
  - `source_event_timestamp_s`
  - `queues.zone_a.toilet`
  - `queues.zone_a.cafe`
  - `queues.zone_b.toilet`
  - `queues.zone_b.cafe`
  - `queues.shared_mens_urinal`

If output is different:
- If received/published is `0`, ensure spectator notebook Cell 6 runs while facility manager loop is active.
- If connect fails, check broker host/port in `config.yaml` and broker status.

## 4. MQTT Topics

### Published Topics
- `stadium/a4/halftime/events/spectator`
  - Publisher: `notebooks/agent_spectator_flow.ipynb`
  - Payload type: spectator event payload
- `stadium/a4/halftime/state/queues`
  - Publisher: `notebooks/agent_facility_manager.ipynb`
  - Payload type: queue-state payload

### Subscribed Topics
- `stadium/a4/halftime/events/spectator`
  - Subscriber: `notebooks/agent_facility_manager.ipynb`
  - Handler: notebook callback `_on_message`

### Message Schemas

#### Spectator Event Payload
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

#### Queue State Payload
```json
{
  "schema_version": "1.0",
  "run_id": "a4-run-1a2b3c4d",
  "timestamp_s": 120,
  "source_event_timestamp_s": 120,
  "queues": {
    "zone_a": {"toilet": 65, "cafe": 27},
    "zone_b": {"toilet": 65, "cafe": 27},
    "shared_mens_urinal": 81
  }
}
```

## 5. Debugging Guidance

### Enable verbose logging
Add this to notebook import cells:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Common errors and fixes
- `TimeoutError: Could not connect to MQTT broker ...`
  - Start broker and verify `mqtt.active_profiles` + selected host/port.
- JSON decode errors in facility manager callback
  - Check the producer payload format and ensure valid JSON.
- No queue-state messages
  - Ensure spectator publisher is running before or during facility-manager Cell 5 loop.

### Verify MQTT flow
- Inspect spectator topic:
  - `mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/events/spectator" -v`
- Inspect queue-state topic:
  - `mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/state/queues" -v`

## 6. Verification Commands

Run from repository root:

```bash
python scripts/verify_setup.py
python scripts/validate_structure.py
python -m pytest
```
