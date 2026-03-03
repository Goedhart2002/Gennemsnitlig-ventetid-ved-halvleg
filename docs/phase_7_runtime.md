# Phase 7 Runtime Guide

This guide documents Phase 7 usability/review improvements only. Core simulation behavior is unchanged.

For a strict click-by-click order, use `docs/phase_7_step_by_step.md`.

## 1) What was created

### Files modified

- `README.md`
- `docs/setup.md`
- `docs/overview.md`
- `docs/mqtt.md`

### Files created

- `docs/phase_7_runtime.md`

### Notebooks/scripts created in Phase 7

- None

### Library modules added in `src/simulated_city/`

- None

### `config.yaml` changes

- None

## 2) How to run

Use this workflow after a clean restart.

1. Open terminal in project root.
2. Activate environment:

```bash
source .venv/bin/activate
```

3. Verify setup:

```bash
python scripts/verify_setup.py
```

4. Open notebooks and run them in this order.

### Notebook A: `notebooks/agent_facility_manager.ipynb`

- Run cell 1 to read purpose.
- Run cells 2-4 to import, load config, connect MQTT, and subscribe.
- Run cell 5 to keep listener active for 30 seconds.

Observe output (exact text format):

- `Connected to MQTT broker at <host>:<port>`
- `Subscribed topic: stadium/a4/halftime/events/spectator`
- `Publish topic: stadium/a4/halftime/state/queues`
- `Subscription started. Waiting for incoming spectator events...`

### Notebook B: `notebooks/agent_congestion.ipynb`

- Run cell 1 to read purpose.
- Run cells 2-4 to import, load config, connect MQTT, and subscribe.
- Run cell 5 to keep listener active for 30 seconds.

Observe output:

- `Connected to MQTT broker at <host>:<port>`
- `Subscribed topic: stadium/a4/halftime/state/queues`
- `Publish topic: stadium/a4/halftime/state/congestion`
- `Subscription started. Waiting for incoming queue-state events...`

### Notebook C: `notebooks/agent_metrics.ipynb`

- Run cell 1 to read purpose.
- Run cells 2-4 to import, load config, connect MQTT, and subscribe.
- Run cell 5 to publish a final KPI payload.

Observe output:

- `Connected to MQTT broker at <host>:<port>`
- `Subscribed topic: stadium/a4/halftime/events/spectator`
- `Publish topic: stadium/a4/halftime/metrics/kpi`
- `Subscription started. Waiting for incoming spectator events...`

### Notebook D: `notebooks/dashboard_a4.ipynb`

- Run cell 1 to read purpose.
- Run cells 2-5 to connect, subscribe, and keep dashboard listening.
- Run cell 6 to print summary.

Observe output:

- `Connected to MQTT broker at <host>:<port>`
- `Subscribing to: stadium/a4/halftime/state/queues`
- `Subscribing to: stadium/a4/halftime/metrics/kpi`
- `Subscribing to: stadium/a4/halftime/state/congestion (optional)`
- `Subscriptions active. Listening for 30 seconds...`

### Notebook E: `notebooks/agent_spectator_flow.ipynb`

Run this notebook last.

- Run cells 1-5 to load config, run simulation, and connect publisher.
- Run cell 6 to publish events.
- Run cell 7 for queue summary and disconnect.

Observe output:

- `Loaded halftime parameters from config.yaml:`
- `Running simulation from config...`
- `Simulation complete: <N> ticks collected`
- `Connected to MQTT broker at <host>:<port>`
- `Publish topic: stadium/a4/halftime/events/spectator`
- `Published <count> spectator events to stadium/a4/halftime/events/spectator`

Cross-notebook expected change:

- `agent_facility_manager.ipynb` cell 5 increases `Received spectator events` and `Published queue states`.
- `agent_congestion.ipynb` cell 5 increases `Received queue-state events` and may increase `Published congestion-state changes`.
- `dashboard_a4.ipynb` cell 5/6 shows increasing queue trend points and latest KPI values.

## 3) Expected output (key cells)

This section gives success criteria and failure hints.

### `agent_facility_manager.ipynb`

- Cell 3 purpose: connect and print topics.
  - Expected output lines:
    - `Connected to MQTT broker at <host>:<port>`
    - `Subscribed topic: stadium/a4/halftime/events/spectator`
    - `Publish topic: stadium/a4/halftime/state/queues`
  - If different: check `config.yaml` broker profile selection and topic helpers.
- Cell 5 purpose: report processing counts and disconnect.
  - Expected output lines:
    - `Received spectator events: <non-negative int>`
    - `Published queue states: <non-negative int>`
    - `Disconnected from MQTT broker.`
  - Success: counts are greater than 0 after spectator publisher runs.

### `agent_congestion.ipynb`

- Cell 3 purpose: connect and print topics.
  - Expected output lines:
    - `Connected to MQTT broker at <host>:<port>`
    - `Subscribed topic: stadium/a4/halftime/state/queues`
    - `Publish topic: stadium/a4/halftime/state/congestion`
- Cell 5 purpose: report congestion transitions and disconnect.
  - Expected output lines:
    - `Received queue-state events: <non-negative int>`
    - `Published congestion-state changes: <non-negative int>`
    - `Disconnected from MQTT broker.`
  - Success: received count is greater than 0 after facility manager publishes.

### `agent_metrics.ipynb`

- Cell 3 purpose: connect and print topics.
  - Expected output lines:
    - `Connected to MQTT broker at <host>:<port>`
    - `Subscribed topic: stadium/a4/halftime/events/spectator`
    - `Publish topic: stadium/a4/halftime/metrics/kpi`
- Cell 5 purpose: finalize and publish KPI payload.
  - Expected output lines:
    - `Received spectator events: <non-negative int>`
    - `Published KPI payloads: 1`
    - `Final KPI payload:` followed by a JSON-like dict
    - `Disconnected from MQTT broker.`
  - Success: payload includes `average_wait_s`, `missed_kickoff_count`, and `wait_percentiles_s` with `P01..P100`.

### `dashboard_a4.ipynb`

- Cell 3 purpose: connect and print subscription topics.
  - Expected output lines:
    - `Connected to MQTT broker at <host>:<port>`
    - `Subscribing to: stadium/a4/halftime/state/queues`
    - `Subscribing to: stadium/a4/halftime/metrics/kpi`
- Cell 6 purpose: summarize received state.
  - Expected output lines:
    - `=== Dashboard Summary ===`
    - `Queue trend points: <non-negative int>`
    - `Average wait (s): <float>`
    - `Missed kickoff count: <int>`
  - Success: queue trend points and KPI fields are present after publisher run.

### `agent_spectator_flow.ipynb`

- Cell 3 purpose: print loaded halftime config.
  - Expected output starts with:
    - `Loaded halftime parameters from config.yaml:`
- Cell 6 purpose: publish sampled events.
  - Expected output line:
    - `Published <count> spectator events to stadium/a4/halftime/events/spectator`
- Cell 7 purpose: finish and disconnect.
  - Expected output includes:
    - `=== Queue Evolution Summary ===`
    - `Disconnected from MQTT broker.`
    - `=== Phase 4 Publisher Complete ===`

## 4) MQTT topics

### Published topics

- `agent_spectator_flow.ipynb` -> `stadium/a4/halftime/events/spectator`
- `agent_facility_manager.ipynb` -> `stadium/a4/halftime/state/queues`
- `agent_congestion.ipynb` -> `stadium/a4/halftime/state/congestion`
- `agent_metrics.ipynb` -> `stadium/a4/halftime/metrics/kpi`

### Subscribed topics

- `agent_facility_manager.ipynb` subscribes to `stadium/a4/halftime/events/spectator`
- `agent_congestion.ipynb` subscribes to `stadium/a4/halftime/state/queues`
- `agent_metrics.ipynb` subscribes to `stadium/a4/halftime/events/spectator`
- `dashboard_a4.ipynb` subscribes to queue/KPI/congestion topics

### Message schema summary

- Spectator event:
  - `schema_version`, `run_id`, `timestamp_s`, `spectators_out_of_seat`, `queue_lengths` (`toilet`, `cafe`)
- Queue state:
  - `schema_version`, `run_id`, `timestamp_s`, `source_event_timestamp_s`, `queues` (`zone_a`, `zone_b`, `shared_mens_urinal`)
- Congestion state:
  - `schema_version`, `run_id`, `timestamp_s`, `zone_a_blocked`, `zone_b_blocked`
- KPI metrics:
  - `schema_version`, `run_id`, `timestamp_s`, `average_wait_s`, `wait_percentiles_s` (`P01..P100`), `missed_kickoff_count`

## 5) Debugging guidance

### Enable more detail in notebook output

- Keep all print cells enabled.
- Temporarily increase listening windows (for example from 30s to 60s) to capture more messages.
- Use a dedicated subscriber terminal:

```bash
mosquitto_sub -h 127.0.0.1 -v -t "stadium/a4/halftime/#"
```

### Common errors and solutions

- `Failed to connect to MQTT broker` or timeout:
  - Confirm broker is running and reachable at host/port from `config.yaml`.
  - Confirm selected first profile in `mqtt.active_profiles` is intended for current run.
- Zero received events in subscriber notebooks:
  - Start subscriber notebooks before `agent_spectator_flow.ipynb`.
  - Re-run the spectator publish cell after subscribers are active.
- No dashboard updates:
  - Confirm dashboard subscriptions print all three topic lines.
  - Confirm at least one KPI payload is published by metrics notebook.

### Verify MQTT flow explicitly

1. Start `mosquitto_sub` on `stadium/a4/halftime/#`.
2. Run notebooks in documented order.
3. Confirm message traffic appears under all four topic prefixes.
4. Cross-check notebook counts (`Received ...`, `Published ...`) are non-zero where expected.

## 6) Verification commands

```bash
python scripts/verify_setup.py
python scripts/validate_structure.py
python -m pytest
```
