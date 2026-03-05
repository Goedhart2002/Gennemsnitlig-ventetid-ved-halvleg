# Phase 6 Runtime Guide (Congestion + Metrics Agents)

This guide documents Phase 6 where advanced behavior is completed with a congestion agent and a metrics agent.

## Phase 6.2 hardening guarantees

Phase 6.2 adds strict stream-consistency rules:
- Congestion processing locks to the first seen `run_id` and ignores stale queue timestamps.
- Metrics aggregation locks to the first seen `run_id` and ignores stale timestamps per input stream.
- Dashboard stream updates ignore stale/out-of-order timestamps per stream.
- KPI finalization now enforces matching `run_id` and `timestamp_s >= halftime_duration_s`.

## 1. What Was Created

### Notebooks and Scripts
- Created notebook: `notebooks/agent_congestion.ipynb`
- Created notebook: `notebooks/agent_metrics.ipynb`
- Added tests: `tests/test_phase6_congestion_metrics.py`
- Corrected notebook for full multi-agent flow: `notebooks/agent_facility_manager.ipynb`

### Library Modules in `src/simulated_city/`
- Added: `congestion.py`
  - `CongestionPolicy`
  - `evaluate_zone_cafe_blocked(...)`
  - `build_congestion_from_queue_state(...)`
- Added: `metrics.py`
  - `MetricsAggregatorState`
  - `record_spectator_event(...)`
  - `record_queue_state(...)`
  - `finalize_kpi_payload(...)`
  - `enforce_final_scenario_policies(...)`
- Updated: `mqtt_payloads.py`
  - `build_congestion_state_payload(...)`
  - `validate_congestion_state_payload(...)`
  - `build_kpi_metrics_payload(...)`
  - `validate_kpi_metrics_payload(...)`

### Configuration Changes (`config.yaml`)
- No new config keys were required for Phase 6.
- Phase 6 uses existing `halftime.blocking.*` and `halftime.timing.halftime_duration_s` values.

## 2. How to Run

### Workflow A: Full agent pipeline
1. Start MQTT broker.
2. Run `notebooks/agent_spectator_flow.ipynb` (publisher).
3. Run `notebooks/agent_facility_manager.ipynb` (queue-state publisher).
4. Run `notebooks/agent_congestion.ipynb` (congestion publisher).
5. Run `notebooks/agent_metrics.ipynb` (KPI publisher).
6. Run `notebooks/dashboard_a4.ipynb` (subscriber visualization).

Expected flow:
- Spectator events -> facility manager queue states.
- Queue states -> congestion states.
- Spectator events + queue states -> final KPI payload (`P01..P100`, average wait, missed kickoff).
- Dashboard displays queue updates and consumes KPI/congestion topics.

### Workflow B: Scenario comparison
1. Change one config value in `config.yaml` (for example `halftime.blocking.queue_people_per_line_threshold`).
2. Rerun all agents and dashboard.
3. Compare congestion flags and KPI profile (`wait_percentiles_s`, missed kickoff count).

## 3. Expected Output

### `agent_congestion.ipynb`

#### Cell 3 (Config + MQTT)
Purpose: initialize blocking policy and connect broker.

Expected lines include:
- `Connected to MQTT broker at 127.0.0.1:1883`
- `Subscribed topic: stadium/a4/halftime/state/queues`
- `Publish topic: stadium/a4/halftime/state/congestion`

#### Cell 4 (Subscription)
Purpose: subscribe and convert queue-state -> congestion-state.

Expected line:
- `Congestion subscription started. Waiting for queue-state updates...`

#### Cell 5 (Summary)
Purpose: report processed messages.

Expected lines include:
- `Received queue states: <n>`
- `Published congestion states: <n>`
- `Last congestion payload:`
- payload containing `zone_a_blocked` and `zone_b_blocked`

### `agent_metrics.ipynb`

#### Cell 3 (Policy + MQTT)
Purpose: enforce final scenario decisions and connect broker.

Expected lines include:
- `Connected to MQTT broker at 127.0.0.1:1883`
- `Subscribed topics: stadium/a4/halftime/events/spectator, stadium/a4/halftime/state/queues`
- `Publish topic: stadium/a4/halftime/metrics/kpi`
- `Final scenario policy checks passed.`

#### Cell 4 (Subscription)
Purpose: start event ingestion for KPI aggregation.

Expected line:
- `Metrics subscriptions started.`

#### Cell 5 (Publish KPI)
Purpose: finalize and publish KPI payload.

Expected lines include:
- `Spectator events seen: <n>`
- `Queue states seen: <n>`
- `Published KPI payload: True`
- `KPI average_wait_s: <value>`
- `KPI missed_kickoff_count: <value>`
- `KPI percentiles available: 100`

If output is different:
- `Published KPI payload: False` means publish/ack failed.
- `KPI percentiles available` not equal to `100` means invalid KPI aggregation.

Additional Phase 6.2 validation:
- Replayed queue messages with the same or older `timestamp_s` do not increment published congestion count.
- Replayed spectator/queue messages with the same or older `timestamp_s` do not change KPI sample counts.
- Finalization before halftime (`timestamp_s < halftime_duration_s`) raises a validation error.

## 4. MQTT Topics

### Published
- `stadium/a4/halftime/state/congestion`
  - Publisher: `notebooks/agent_congestion.ipynb`
  - Schema fields: `schema_version`, `run_id`, `timestamp_s`, `zone_a_blocked`, `zone_b_blocked`
- `stadium/a4/halftime/metrics/kpi`
  - Publisher: `notebooks/agent_metrics.ipynb`
  - Schema fields: `schema_version`, `run_id`, `timestamp_s`, `average_wait_s`, `wait_percentiles_s`, `missed_kickoff_count`

### Subscribed
- `stadium/a4/halftime/state/queues`
  - Subscriber: `notebooks/agent_congestion.ipynb`
  - Handler: congestion callback in Cell 4
- `stadium/a4/halftime/events/spectator`
  - Subscriber: `notebooks/agent_metrics.ipynb`
  - Handler: metrics callback in Cell 4
- `stadium/a4/halftime/state/queues`
  - Subscriber: `notebooks/agent_metrics.ipynb`
  - Handler: metrics callback in Cell 4

### Message schema examples

#### Congestion payload
```json
{
  "schema_version": "1.0",
  "run_id": "a4-run-1a2b3c4d",
  "timestamp_s": 120,
  "zone_a_blocked": true,
  "zone_b_blocked": false
}
```

#### KPI payload
```json
{
  "schema_version": "1.0",
  "run_id": "a4-metrics-1a2b3c4d",
  "timestamp_s": 900,
  "average_wait_s": 152.4,
  "wait_percentiles_s": {
    "P01": 3.0,
    "P02": 4.0,
    "...": 0,
    "P99": 288.0,
    "P100": 300.0
  },
  "missed_kickoff_count": 143
}
```

## 5. Debugging Guidance

### Enable verbose logs
Add to import cell in any agent:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Common errors
- `TimeoutError: Could not connect to MQTT broker ...`
  - Start broker and verify `mqtt` host/port profile.
- Congestion states stay at zero messages
  - Ensure facility manager is running and publishing queue state.
- KPI payload missing percentiles
  - Confirm metrics agent prints `KPI percentiles available: 100`.
- Missed kickoff count looks wrong
  - Verify `halftime.timing.halftime_duration_s` is `900` and metrics policy check passes.

### Verify MQTT message flow
Use these subscribers in separate terminals:

```bash
mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/state/queues" -v
mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/state/congestion" -v
mosquitto_sub -h 127.0.0.1 -t "stadium/a4/halftime/metrics/kpi" -v
```

## 6. Verification Commands

Run from repository root:

```bash
python scripts/verify_setup.py
python scripts/validate_structure.py
python -m pytest
```
