# Phase 4.2 Runtime Guide (Second Agent with MQTT Subscription)

This guide validates Phase 4.2 only: a downstream facility-manager agent subscribes to spectator and movement streams, then publishes queue-state and task-state updates.

## Quick Pass Criteria

Phase 4.2 is successful if all are true:
- `agent_spectator_flow.ipynb` publishes to spectator and movement topics.
- `agent_facility_manager.ipynb` subscribes to both input topics.
- `agent_facility_manager.ipynb` publishes queue-state and task-state payloads.
- Output payloads preserve source `run_id`.
- Phase 4.2 tests pass.

## 1. What Was Created

### Files updated
- `notebooks/agent_facility_manager.ipynb`
  - Subscribes to spectator and movement topics
  - Publishes queue-state and task-state payloads
- `src/simulated_city/facility_manager.py`
  - Added `process_movement_snapshot(...)`
  - Kept `process_spectator_event(...)` and updated internal canonical zone handling (`zone_1`/`zone_2`) before boundary mapping
- `src/simulated_city/mqtt_payloads.py`
  - Added `build_task_state_payload(...)`
  - Added `validate_task_state_payload(...)`
- `tests/test_phase4_agent_communication.py`
  - Added movement/task communication tests

### Library modules added
- None (existing modules were extended).

### Configuration changes (`config.yaml`)
- No new keys were added in this phase.
- Reused:
  - `mqtt.*` for broker connection
  - `halftime.capacity.shared_urinal_total` for facility state

## 2. How to Run

### Workflow A: Start publisher then subscriber
1. Start your MQTT broker.
2. Open `notebooks/agent_spectator_flow.ipynb` and run cells 1 to 7.
3. Open `notebooks/agent_facility_manager.ipynb` and run cells 1 to 5.
4. Pass if you observe in `agent_facility_manager.ipynb`:
   - spectator events received,
   - movement events received,
   - queue states published,
   - task states published.

### Workflow B: Topic monitor in terminal (recommended)
1. In terminal A, run:
   ```bash
   mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/state/queues" -v
   ```
2. In terminal B, run:
   ```bash
   mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/state/tasks" -v
   ```
3. Run both notebooks as in Workflow A.
4. Pass if both topics receive payloads while notebooks are running.

## 3. Expected Output

> Counts vary by run and broker timing. Validate text anchors and payload shape.

### `agent_spectator_flow.ipynb`

#### Cell 5
- **Purpose:** Connect publisher and print topic metadata.
- **Expected output includes exact anchors:**
  - `Connected to MQTT broker at <host>:<port>`
  - `spectator_topic: stadium/a4/halftime/events/spectator`
  - `movement_topic: stadium/a4/halftime/state/movement`

#### Cell 6
- **Purpose:** Publish spectator + movement payloads.
- **Expected output includes exact anchors:**
  - `Published spectator payloads:`
  - `Published movement payloads:`

### `agent_facility_manager.ipynb`

#### Cell 3
- **Purpose:** Load config, initialize state, connect MQTT.
- **Expected output includes exact anchors:**
  - `Connected to MQTT broker at <host>:<port>`
  - `Subscribed topics: stadium/a4/halftime/events/spectator, stadium/a4/halftime/state/movement`
  - `Publish topics: stadium/a4/halftime/state/queues, stadium/a4/halftime/state/tasks`

#### Cell 4
- **Purpose:** Register callback and subscribe to both input topics.
- **Expected output exact text:**
  - `Subscriptions started. Waiting for spectator and movement events...`

#### Cell 5
- **Purpose:** Run processing loop and print publish summary.
- **Expected output includes exact anchors:**
  - `Received spectator events:`
  - `Received movement events:`
  - `Published queue states:`
  - `Published task states:`
  - `Last queue-state payload:` (when queue publishes occur)
  - `Last task-state payload:` (when task publishes occur)
  - `Disconnected from MQTT broker.`
  - `=== Phase 4.2 Facility Manager Complete ===`

### Success vs failure
- **Success:** both publish counters (`Published queue states`, `Published task states`) are greater than 0 while publisher notebook is active.
- **Failure examples:**
  - counters remain 0: publisher not running, wrong broker/profile, or subscription never started.
  - connection line missing: broker connect failed.

### Optional strict checks
Add this temporary check in `agent_facility_manager.ipynb` after Cell 5:

```python
assert len(received_spectator_events) > 0
assert len(received_movement_events) > 0
assert len(published_queue_states) > 0
assert len(published_task_states) > 0
assert published_queue_states[-1]["run_id"] == published_task_states[-1]["run_id"]
print("Phase 4.2 communication validation passed")
```

## 4. MQTT Topics

### Subscribed by `notebooks/agent_facility_manager.ipynb`
- `stadium/a4/halftime/events/spectator`
  - Handler branch: spectator-event path
  - Processing: `process_spectator_event(...)`
- `stadium/a4/halftime/state/movement`
  - Handler branch: movement-event path
  - Processing: `process_movement_snapshot(...)`

### Published by `notebooks/agent_facility_manager.ipynb`
- `stadium/a4/halftime/state/queues`
  - Source: transformed spectator event
  - Envelope: `schema_version`, `run_id`, `timestamp_s`, `source_event_timestamp_s`, `queues`
- `stadium/a4/halftime/state/tasks`
  - Source: transformed movement snapshot
  - Envelope: `schema_version`, `run_id`, `timestamp_s`, `spectator_id`, `task`, `task_state`

### Message schema examples

#### Queue-state payload
```json
{
  "schema_version": "1.0",
  "run_id": "a4-run-1a2b3c4d",
  "timestamp_s": 120,
  "source_event_timestamp_s": 120,
  "queues": {
    "zone_a": {"toilet": 40, "cafe": 18},
    "zone_b": {"toilet": 37, "cafe": 20},
    "shared_mens_urinal": 22
  }
}
```

#### Task-state payload
```json
{
  "schema_version": "1.0",
  "run_id": "a4-run-1a2b3c4d",
  "timestamp_s": 121,
  "spectator_id": 17,
  "task": "toilet_w",
  "task_state": "service_started"
}
```

## 5. Debugging Guidance

### Enable verbose logging
Add this in notebook import cells when needed:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Common errors and solutions
- **MQTT connection timeout/error**
  - Ensure broker is running and `config.yaml` profile host/port/tls are correct.
- **No task-state publishes**
  - Ensure movement messages are arriving (`Received movement events > 0`).
- **No queue-state publishes**
  - Ensure spectator messages are arriving (`Received spectator events > 0`).
- **JSON decode issues**
  - Check incoming payload source and ensure valid JSON on input topics.

### Verify message flow quickly
- Monitor input topics:
  - `stadium/a4/halftime/events/spectator`
  - `stadium/a4/halftime/state/movement`
- Monitor output topics:
  - `stadium/a4/halftime/state/queues`
  - `stadium/a4/halftime/state/tasks`
- Confirm output `run_id` matches input `run_id`.

## 6. Verification Commands

Run from repository root:

```bash
python scripts/verify_setup.py
python scripts/validate_structure.py
python -m pytest tests/test_phase4_agent_communication.py
python -m pytest
```

## 7. Current Validation Status

Latest run status for this implementation:
- `python scripts/verify_setup.py`: passed
- `python scripts/validate_structure.py`: passed
- `python -m pytest tests/test_phase4_agent_communication.py`: passed
- `python -m pytest`: passed
