# Phase 3.2 Runtime Guide (Single-Agent MQTT Publishing)

This guide validates Phase 3.2 only: one spectator-flow agent publishes spectator and movement state events to MQTT.

## Quick Pass Criteria

Phase 3.2 is successful if all are true:
- Publisher connects to MQTT with no connection error.
- Spectator payloads are published to `stadium/a4/halftime/events/spectator`.
- Movement payloads are published to `stadium/a4/halftime/state/movement`.
- Both published streams use the same `run_id`.
- Phase 3.2 tests pass.

## 1. What Was Created

### Files updated
- `src/simulated_city/mqtt_payloads.py`
  - Added `build_movement_state_payload(...)`
  - Added `validate_movement_state_payload(...)`
- `notebooks/agent_spectator_flow.ipynb`
  - Converted from local-only mode to MQTT publisher mode
  - Publishes both spectator and movement payloads with one shared `run_id`
- `tests/test_phase3_mqtt_publish.py`
  - Added movement topic, movement payload, and movement publish assertions

### Library modules added
- None (existing modules were extended only).

### Configuration changes (`config.yaml`)
- No new keys were added in Phase 3.2.
- Publisher uses existing keys:
  - `mqtt.*` for broker connection
  - `halftime.*` for simulation
  - `halftime_map.publish_interval_s`
  - `halftime_map.max_points_per_message`

## 2. How to Run

### Workflow A: Run publisher notebook
1. Start JupyterLab:
   ```bash
   python -m jupyterlab
   ```
2. Open `notebooks/agent_spectator_flow.ipynb`.
3. Run cells 1 to 7 in order.
4. Pass criteria:
   - Cell 3 prints `Loaded halftime parameters from config.yaml (Phase 3.2 publisher mode):`
   - Cell 5 prints `Connected to MQTT broker at ...` and both topics
   - Cell 6 prints published counts for spectator and movement payloads
   - Cell 7 prints completion text and disconnect message

### Workflow B: Verify throttle and payload cap behavior
1. In `config.yaml`, set:
   - `halftime_map.publish_interval_s: 5`
   - `halftime_map.max_points_per_message: 100`
2. Re-run notebook cells 3 to 7.
3. Pass criteria:
   - Cell 5 prints the updated publish controls
   - Cell 6 reports fewer publish events due to throttle
   - Last movement payload spectator count does not exceed `100`

## 3. Expected Output

> Numeric counts can vary by run when `halftime.seed` is `null`. Validate the exact text anchors.

### Cell 3 (config load)
- **Purpose:** Load typed config and show simulation + map publish settings.
- **Expected output includes:**
  - `Loaded halftime parameters from config.yaml (Phase 3.2 publisher mode):`
  - `Loaded halftime_map publish controls:`
  - `publish_interval_s:`
  - `max_points_per_message:`
  - `canonical_service_zones: ('zone_1', 'zone_2')`

### Cell 4 (simulate)
- **Purpose:** Run simulation used as event source.
- **Expected output includes:**
  - `Running simulation from config...`
  - `Simulation complete:`
  - `=== Key Performance Indicators (KPIs) ===`

### Cell 5 (connect + topic setup)
- **Purpose:** Connect to MQTT and print envelope/topic metadata.
- **Expected output includes:**
  - `Connected to MQTT broker at <host>:<port>`
  - `run_id: a4-run-...`
  - `spectator_topic: stadium/a4/halftime/events/spectator`
  - `movement_topic: stadium/a4/halftime/state/movement`

### Cell 6 (publishing loop)
- **Purpose:** Publish spectator and movement payloads with same `run_id`.
- **Expected output includes:**
  - `Published spectator payloads:`
  - `Published movement payloads:`
  - `Last movement payload spectator count:`
  - `Last movement payload timestamp_s:`
- **Success criteria:** both publish counters are positive in a healthy broker setup.

### Cell 7 (summary + disconnect)
- **Purpose:** Final queue summary and connection shutdown.
- **Expected output includes:**
  - `=== Queue Evolution Summary ===`
  - `Disconnected from MQTT broker.`
  - `=== Phase 3.2 Publisher Complete ===`
  - `Spectator and movement payloads were published to MQTT with a shared run_id.`

### If output is different
- Missing connect line in Cell 5: broker unreachable or wrong active profile.
- Publish counts are zero: publish rejected, broker not connected, or payload validation failed.
- Missing disconnect line in Cell 7: connector object was not attached (connection setup issue).

### Optional strict checks
Add this temporary check after Cell 6 in `notebooks/agent_spectator_flow.ipynb`:

```python
assert published_spectator_count > 0
assert published_movement_count > 0
assert last_movement_payload is not None
assert last_movement_payload["run_id"] == run_id
assert len(last_movement_payload["spectators"]) <= halftime_map_cfg.max_points_per_message
print("Phase 3.2 publish validation passed")
```

## 4. MQTT Topics

### Published by `notebooks/agent_spectator_flow.ipynb`
- `stadium/a4/halftime/events/spectator`
  - Payload fields:
    - `schema_version` (string)
    - `run_id` (string)
    - `timestamp_s` (int)
    - `spectators_out_of_seat` (int)
    - `queue_lengths` object with `toilet` and `cafe`
    - optional counts: `stayed_seated_count`, `went_down_count`, `went_down_made_back_count`

- `stadium/a4/halftime/state/movement`
  - Payload fields:
    - `schema_version` (string)
    - `run_id` (string)
    - `timestamp_s` (int)
    - `spectators` (list)
  - Each spectator entry contains:
    - `spectator_id` (int)
    - `state` (string)
    - `target` (string, for example `zone_1_toilet_w`)
    - `lng` (float)
    - `lat` (float)

### Subscriptions in this phase
- None in Phase 3.2 (single publisher only).

## 5. Debugging Guidance

### Enable more visibility
- Temporarily print payloads in Cell 6 before publish:
  - `print(spectator_payload)`
  - `print(movement_payload)`
- Use a lower throttle (`publish_interval_s: 1`) during debugging.

### Common errors and fixes
- **MQTT connect failure**
  - Ensure local broker is running for `mqtt.active_profiles` primary profile.
  - Verify `config.yaml` host/port/tls values.
- **`ValueError` from movement payload validation**
  - Ensure every spectator entry contains `spectator_id`, `state`, `target`, `lng`, `lat`.
- **No publishes recorded**
  - Confirm Cell 5 connection succeeded.
  - Confirm `publish_interval_s` is not too large for test run.

### Verify MQTT message flow
- In a second terminal, subscribe with your MQTT tool/client to:
  - `stadium/a4/halftime/events/spectator`
  - `stadium/a4/halftime/state/movement`
- Confirm both topics receive messages with the same `run_id` value.

## 6. Verification Commands

Run from repository root:

```bash
python scripts/verify_setup.py
python scripts/validate_structure.py
python -m pytest tests/test_phase3_mqtt_publish.py tests/test_mqtt_profiles.py
python -m pytest
```

## 7. Current Validation Status

Latest run status for this implementation:
- `python scripts/verify_setup.py`: passed
- `python scripts/validate_structure.py`: passed
- `python -m pytest tests/test_phase3_mqtt_publish.py tests/test_mqtt_profiles.py`: passed
- `python -m pytest`: passed
