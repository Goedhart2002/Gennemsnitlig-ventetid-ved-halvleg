# Phase 5.2 Runtime Guide (Dashboard Visualization with anymap-ts)

This guide validates Phase 5.2 only: the dashboard subscribes to movement, queue, KPI, and congestion streams and renders live map + stream consistency metadata.

## 1. What Was Created

### Notebooks/scripts updated
- Updated notebook: `notebooks/dashboard_a4.ipynb`
  - Subscribes to movement + queue + KPI + congestion topics
  - Renders queue overlays and moving spectator markers in anymap-ts
  - Prints stream consistency metadata (`run_id`, latest timestamps per stream)

### Library modules updated
- Updated module: `src/simulated_city/dashboard_views.py`
  - Added `MovementPoint` and `MovementSnapshot`
  - Added `parse_movement_payload(...)`
  - Extended `DashboardState` with:
    - `latest_movement`
    - `latest_timestamps_by_stream`
  - Extended `update_dashboard_state_from_topic(...)` with `topic_movement_state`

### Tests updated
- Updated: `tests/test_phase5_dashboard_data_shapes.py`
  - Added movement payload parsing and state update assertions
- Updated: `tests/test_maplibre_live.py`
  - Added guard-case assertion for missing renderer export

### Configuration changes (`config.yaml`)
- No new keys added in this phase.
- Dashboard uses existing:
  - `mqtt.*`
  - `halftime_map.*` (center, zoom, publish interval, payload cap, zone anchors)

## 2. How to Run

### Workflow A: End-to-end live dashboard
1. Start MQTT broker.
2. Start publisher notebook: `notebooks/agent_spectator_flow.ipynb` and run cells 1-7.
3. Start facility notebook: `notebooks/agent_facility_manager.ipynb` and run cells 1-5.
4. Open dashboard notebook: `notebooks/dashboard_a4.ipynb` and run cells 1-6.

Expected behavior in dashboard:
- Map appears in Cell 3.
- Cell 5 prints periodic lines with `run_id`, `queue_ts`, `movement_ts`, and `kpi_ts`.
- Cell 6 prints queue point count, latest movement point count, and timestamp dictionary.

### Workflow B: Throttle/cap check
1. In `config.yaml`, set:
   - `halftime_map.publish_interval_s: 5`
   - `halftime_map.max_points_per_message: 100`
2. Re-run dashboard cells 3-6.
3. Verify movement markers update with lower frequency and movement count in Cell 6 does not exceed `100`.

## 3. Expected Output

> Numeric counts vary by run. Validate exact text anchors.

### `notebooks/dashboard_a4.ipynb`

#### Cell 3 (setup)
- **Purpose:** Connect MQTT, initialize map geometry from config.
- **Expected text includes:**
  - `Connected to MQTT broker at <host>:<port>`
  - `Subscribing to: stadium/a4/halftime/state/movement`
  - `Subscribing to: stadium/a4/halftime/state/queues`
  - `Subscribing to: stadium/a4/halftime/metrics/kpi`
  - `Subscribing to: stadium/a4/halftime/state/congestion (optional)`
  - `Movement render cap:`
  - `Update throttle (s):`

#### Cell 4 (callback)
- **Purpose:** Register callback and map refresh handlers.
- **Expected exact text:**
  - `Dashboard callback registered.`

#### Cell 5 (listening)
- **Purpose:** Subscribe and process incoming messages.
- **Expected text includes:**
  - `Subscriptions active. Listening for 30 seconds...`
  - periodic lines in this shape:
    - `t+05s | run_id=... queue_ts=... movement_ts=... kpi_ts=...`
  - `Dashboard listening window finished.`

#### Cell 6 (summary)
- **Purpose:** Print stream consistency and disconnect.
- **Expected text includes:**
  - `=== Dashboard Summary ===`
  - `Active run_id:`
  - `Queue trend points:`
  - `Movement points (latest snapshot):`
  - `Latest stream timestamps:`
  - KPI lines or no-KPI fallback message
  - optional congestion line or no-congestion fallback message
  - `Disconnected from MQTT broker.`

### Success vs failure
- **Success:** queue and movement timestamps are populated while upstream agents are running.
- **Failure examples:**
  - `queue_ts=None` and `movement_ts=None` after full window -> no inbound traffic or wrong broker/profile.
  - map not shown in Cell 3 -> anymap-ts import/runtime issue.

## 4. MQTT Topics

### Subscribed by `notebooks/dashboard_a4.ipynb`
- `stadium/a4/halftime/state/movement`
- `stadium/a4/halftime/state/queues`
- `stadium/a4/halftime/metrics/kpi`
- `stadium/a4/halftime/state/congestion` (optional)

### Published by `notebooks/dashboard_a4.ipynb`
- None (subscriber-only dashboard).

### Message schemas consumed

#### Movement payload
```json
{
  "schema_version": "1.0",
  "run_id": "a4-run-1a2b3c4d",
  "timestamp_s": 121,
  "spectators": [
    {
      "spectator_id": 1,
      "state": "WALKING_TO_ZONE",
      "target": "zone_1_toilet_w",
      "lng": 12.56845,
      "lat": 55.67618
    }
  ]
}
```

#### Queue payload
```json
{
  "schema_version": "1.0",
  "run_id": "a4-run-1a2b3c4d",
  "timestamp_s": 120,
  "queues": {
    "zone_a": {"toilet": 40, "cafe": 18},
    "zone_b": {"toilet": 37, "cafe": 20},
    "shared_mens_urinal": 22
  }
}
```

#### KPI payload
```json
{
  "schema_version": "1.0",
  "run_id": "a4-run-1a2b3c4d",
  "timestamp_s": 900,
  "average_wait_s": 152.4,
  "wait_percentiles_s": {
    "P01": 3.0,
    "...": 0,
    "P100": 300.0
  },
  "missed_kickoff_count": 143
}
```
(Requires complete `P01..P100` keys.)

#### Congestion payload (optional)
```json
{
  "schema_version": "1.0",
  "run_id": "a4-run-1a2b3c4d",
  "timestamp_s": 120,
  "zone_a_blocked": false,
  "zone_b_blocked": true
}
```

## 5. Debugging Guidance

### Enable verbose logs in dashboard notebook
Add in Cell 2:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Common errors and fixes
- **MQTT connect failure**
  - Verify broker is running and active profile host/port/tls values in `config.yaml`.
- **No movement points rendered**
  - Verify `state.latest_timestamps_by_stream['movement']` appears in Cell 5 logs.
  - Check movement topic publisher is running.
- **KPI parse errors**
  - Ensure incoming KPI payload includes all `P01..P100` keys.

### Verify MQTT flow from terminal
```bash
mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/state/movement" -v
mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/state/queues" -v
mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/metrics/kpi" -v
mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/state/congestion" -v
```

## 6. Verification Commands

Run from repository root:

```bash
python scripts/verify_setup.py
python scripts/validate_structure.py
python -m pytest tests/test_phase5_dashboard_data_shapes.py tests/test_maplibre_live.py
python -m pytest
```
