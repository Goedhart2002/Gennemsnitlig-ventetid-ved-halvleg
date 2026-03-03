# Phase 5 Runtime Guide (Dashboard Visualization with anymap-ts)

This guide documents Phase 5 where a dashboard notebook subscribes to queue/KPI/congestion topics and visualizes live halftime outcomes.

## 1. What Was Created

### Notebooks and Scripts
- Created notebook: `notebooks/dashboard_a4.ipynb`
- Added tests: `tests/test_phase5_dashboard_data_shapes.py`

### Library Modules in `src/simulated_city/`
- Added: `dashboard_views.py`
  - `DashboardState`
  - `parse_queue_state_payload(...)`
  - `parse_kpi_payload(...)`
  - `parse_congestion_payload(...)`
  - `normalize_wait_percentiles(...)`
  - `update_dashboard_state_from_topic(...)`
- Updated: `topic_schema.py`
  - `topic_kpi_metrics()`
  - `topic_congestion_state()`

### Configuration Changes (`config.yaml`)
- No new keys required in Phase 5.
- Dashboard uses existing MQTT settings loaded via `simulated_city.config.load_config()`.

## 2. How to Run

### Workflow A: Start agents then dashboard
1. Start MQTT broker.
2. Open and run `notebooks/agent_spectator_flow.ipynb` (publisher).
3. Open and run `notebooks/agent_facility_manager.ipynb` (queue-state publisher).
4. Open and run `notebooks/dashboard_a4.ipynb` cells 1-6.

Expected behavior:
- Dashboard connects to broker.
- Dashboard subscribes to queue, KPI, and optional congestion topics.
- Dashboard map markers update when queue-state messages arrive.
- Dashboard prints queue/KPI/congestion summary after listening window.

### Workflow B: Optional KPI/congestion producers
- If KPI and congestion agents are not available yet, dashboard still runs.
- Queue markers still update from `stadium/a4/halftime/state/queues`.
- KPI/congestion summary shows “No KPI payload received …” or “No congestion payload received …”.

## 3. Expected Output

### Cell 3 (Config + MQTT + Map)
Purpose: connect to MQTT and initialize anymap-ts map.

Expected lines include:
- `Connected to MQTT broker at 127.0.0.1:1883` (for local profile)
- `Subscribing to: stadium/a4/halftime/state/queues`
- `Subscribing to: stadium/a4/halftime/metrics/kpi`
- `Subscribing to: stadium/a4/halftime/state/congestion (optional)`

If different:
- verify broker availability and active profile in `config.yaml`.

### Cell 4 (Callback Registration)
Purpose: register state-update callback for incoming MQTT payloads.

Expected line:
- `Dashboard callback registered.`

If missing:
- callback did not install; rerun Cell 4 before Cell 5.

### Cell 5 (Listening Window)
Purpose: subscribe and process topic data for 30 seconds.

Expected lines include:
- `Subscriptions active. Listening for 30 seconds...`
- periodic status lines like:
  - `t+05s | queue_points=... latest_queue_ts=...`
- `Dashboard listening window finished.`

Success means queue_points increases when upstream agents are running.

### Cell 6 (Summary)
Purpose: print queue trends and KPI/congestion summary.

Expected lines include:
- `=== Dashboard Summary ===`
- `Queue trend points: <n>`
- Either KPI values (`Average wait`, `Missed kickoff`, `Wait P50/P95/P99`) or no-KPI message
- Either congestion line or no-congestion message
- `Disconnected from MQTT broker.`

## 4. MQTT Topics

### Subscribed topics
- `stadium/a4/halftime/state/queues`
  - Required for queue trend + map marker updates.
- `stadium/a4/halftime/metrics/kpi`
  - Required for wait distribution (`P01..P100`) and missed kickoff display.
- `stadium/a4/halftime/state/congestion`
  - Optional in Phase 5.

### Published topics
- None (dashboard is subscriber-only in Phase 5).

### Expected message schemas

#### Queue state payload
```json
{
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
  "timestamp_s": 120,
  "average_wait_s": 145.2,
  "wait_percentiles_s": {
    "P01": 5.0,
    "P02": 6.0,
    "...": 0,
    "P99": 260.0,
    "P100": 300.0
  },
  "missed_kickoff_count": 133
}
```
(Requires all keys `P01..P100`.)

#### Congestion payload (optional)
```json
{
  "timestamp_s": 120,
  "zone_a_blocked": false,
  "zone_b_blocked": true
}
```

## 5. Debugging Guidance

### Enable logs
Add to Cell 2:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Common issues
- Connection timeout:
  - Start broker and verify `mqtt` host/port profile in `config.yaml`.
- Queue points stay zero:
  - Ensure both publisher notebooks are running and publishing queue-state messages.
- KPI parse errors:
  - Ensure `wait_percentiles_s` includes all keys `P01` to `P100`.

### Verify message flow
In terminal:

```bash
mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/state/queues" -v
mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/metrics/kpi" -v
mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/state/congestion" -v
```

## 6. Verification Commands

Run from repository root:

```bash
python scripts/verify_setup.py
python scripts/validate_structure.py
python -m pytest
```
