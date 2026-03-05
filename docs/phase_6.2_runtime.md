# Phase 6.2 Runtime Guide (Run Consistency Hardening)

This guide validates Phase 6.2 only: hardening congestion, metrics, and dashboard ingestion against mixed runs and stale messages.

## Quick Pass Criteria

Phase 6.2 is successful if all are true:
- Congestion ignores queue messages from stale timestamps and mismatched `run_id`.
- Metrics ignores stale spectator/queue timestamps and mismatched `run_id`.
- KPI finalization enforces matching `run_id` and `timestamp_s >= halftime_duration_s`.
- Dashboard state ignores stale timestamps per stream.
- Phase 6.2 tests pass.

## 1. What Was Updated

### Files updated
- `src/simulated_city/congestion.py`
  - Added `CongestionAgentState`
  - Added run-id + timestamp acceptance guard for queue input
  - Added queue extraction compatibility helper used before congestion decision
- `src/simulated_city/metrics.py`
  - Added per-stream stale timestamp guards (`spectator` and `queue`)
  - Added stricter `finalize_kpi_payload(...)` guard checks
- `src/simulated_city/dashboard_views.py`
  - Added per-stream stale-message rejection in `update_dashboard_state_from_topic(...)`
- `tests/test_phase6_congestion_metrics.py`
  - Added hardening coverage for run lock, stale rejection, finalize guards
- `tests/test_phase5_dashboard_data_shapes.py`
  - Added stale timestamp state-update coverage
- `tests/test_phase4_agent_communication.py`
  - Added out-of-order movement snapshot assertion

## 2. How to Run

### Workflow A: tests only (recommended)
1. Run setup checks:
   ```bash
   python scripts/verify_setup.py
   python scripts/validate_structure.py
   ```
2. Run focused phase tests:
   ```bash
   python -m pytest tests/test_phase3_mqtt_publish.py tests/test_phase4_agent_communication.py tests/test_phase5_dashboard_data_shapes.py tests/test_phase6_congestion_metrics.py
   ```
3. Run full test suite:
   ```bash
   python -m pytest
   ```

### Workflow B: notebook smoke check
1. Start `agent_spectator_flow.ipynb` and `agent_facility_manager.ipynb`.
2. Start `agent_congestion.ipynb`, `agent_metrics.ipynb`, and `dashboard_a4.ipynb`.
3. Re-run one payload with the same timestamp to simulate reconnect replay.
4. Confirm counters/state do not move on stale replay.

## 3. Expected Output Anchors

### Test run output
- Focused run should end with:
  - `... [100%]`
  - no failures in phase 3–6 test files.

### Behavior anchors
- Congestion:
  - stale or older queue `timestamp_s` -> no new congestion publish.
  - different `run_id` after lock -> ignored.
- Metrics:
  - stale spectator/queue timestamp -> sample count unchanged.
  - finalize with wrong run -> raises `ValueError`.
  - finalize before halftime complete -> raises `ValueError`.
- Dashboard:
  - stale queue/movement update -> latest state remains unchanged.

## 4. Debugging Guidance

### If stale messages still affect state
- Confirm each consumer keeps local mutable state (`active_run_id`, last timestamp per stream).
- Confirm comparisons are strict (`timestamp_s > last_timestamp`).

### If KPI finalize fails unexpectedly
- Confirm final call uses the same `run_id` seen by the aggregator.
- Confirm final `timestamp_s` is at least halftime duration (`900` by default).

### If dashboard looks inconsistent after reconnect
- Confirm replayed payloads are not newer than the current stream timestamp.
- Confirm all streams use the same `run_id` for one simulation session.

## 5. MQTT Topics in Scope

- `stadium/a4/halftime/events/spectator`
- `stadium/a4/halftime/state/queues`
- `stadium/a4/halftime/state/congestion`
- `stadium/a4/halftime/metrics/kpi`
- `stadium/a4/halftime/state/movement`

Phase 6.2 does not add new topics; it enforces safer handling of existing ones.
