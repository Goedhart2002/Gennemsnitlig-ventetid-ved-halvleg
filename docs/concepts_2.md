# Concepts 2: Section A4 Halftime Map Simulation (PLAN)

This document is a design-first architecture plan for extending the current Section A4 notebooks into a movement map simulation where spectators leave seats, perform tasks in zones, and return to seats during halftime.

It follows the current project constraints:
- One notebook per agent (distributed simulation)
- MQTT communication between notebooks
- `config.yaml` as the source of runtime parameters
- `anymap-ts` for mapping

## 1. System Overview

### Trigger (event generation)
The Trigger layer is responsible for creating spectator intent and movement events during halftime.

Technical definition:
- Input: halftime parameters from `config.yaml` (`seat_leave_rate`, `women_ratio`, timing/service ranges, and capacity)
- Output: per-spectator state transitions over time
- Examples of generated events:
  - leave seat
  - choose task (`toilet_w`, `toilet_m`, `urinal`, `cafe`)
  - start walking to target zone
  - start return walk to seat

Primary source in current system:
- `notebooks/agent_spectator_flow.ipynb` (publishes spectator event stream)

### Observer (state collection)
The Observer layer receives all event streams and maintains the best current state estimate of the system.

Technical definition:
- Input: spectator events, queue snapshots, congestion snapshots, KPI snapshots
- Output: synchronized state view for operators and dashboard
- Observed entities:
  - queue lengths by zone/facility
  - congestion flags by zone
  - current/aggregate KPIs
  - (planned) per-spectator live position/state for map rendering

Primary source in current system:
- `notebooks/dashboard_a4.ipynb` + `src/simulated_city/dashboard_views.py`

### Control (decision logic)
The Control layer applies rules and thresholds to update agent behavior and route/service outcomes.

Technical definition:
- Input: queue state + congestion + remaining halftime time
- Output: updated movement/service decisions (join/switch/return)
- Existing controls:
  - queue processing (`agent_facility_manager.ipynb`)
  - congestion policy (`agent_congestion.ipynb`)
  - metrics aggregation/policies (`agent_metrics.ipynb`)
- Planned control extension:
  - movement route assignment from seat area to nearest eligible zone and back
  - state machine per spectator: `SEATED -> WALKING_TO_ZONE -> WAITING -> IN_SERVICE -> WALKING_TO_SEAT -> SEATED_DONE`

### Response (actuation/visualization)
The Response layer publishes updated state and visual feedback.

Technical definition:
- Output channels:
  - MQTT state topics (queue, congestion, KPI, movement)
  - live map layers/markers in `anymap-ts`
- Current responses:
  - queue-state topic
  - congestion-state topic
  - KPI topic
  - KPI bar charts notebook
- Planned response extension:
  - live movement map showing spectators leaving seats, moving to zones, and returning

## 2. MQTT Architecture

### 2.1 Existing topics in the repository

All existing topic constants are defined in `src/simulated_city/topic_schema.py`.

#### Topic: `stadium/a4/halftime/events/spectator`
- Published by:
  - `notebooks/agent_spectator_flow.ipynb`
- Subscribed by:
  - `notebooks/agent_facility_manager.ipynb`
  - `notebooks/agent_metrics.ipynb`
- Message schema:
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

#### Topic: `stadium/a4/halftime/state/queues`
- Published by:
  - `notebooks/agent_facility_manager.ipynb`
- Subscribed by:
  - `notebooks/agent_congestion.ipynb`
  - `notebooks/agent_metrics.ipynb`
  - `notebooks/dashboard_a4.ipynb`
- Message schema:
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

#### Topic: `stadium/a4/halftime/state/congestion`
- Published by:
  - `notebooks/agent_congestion.ipynb`
- Subscribed by:
  - `notebooks/dashboard_a4.ipynb`
- Message schema:
```json
{
  "schema_version": "1.0",
  "run_id": "a4-run-1a2b3c4d",
  "timestamp_s": 120,
  "zone_a_blocked": false,
  "zone_b_blocked": true
}
```

#### Topic: `stadium/a4/halftime/metrics/kpi`
- Published by:
  - `notebooks/agent_metrics.ipynb`
- Subscribed by:
  - `notebooks/dashboard_a4.ipynb`
- Message schema:
```json
{
  "schema_version": "1.0",
  "run_id": "a4-run-1a2b3c4d",
  "timestamp_s": 900,
  "average_wait_s": 152.4,
  "wait_percentiles_s": {
    "P01": 3.0,
    "P02": 4.0,
    "P99": 288.0,
    "P100": 300.0
  },
  "missed_kickoff_count": 143,
  "made_kickoff_count": 857,
  "stayed_seated_count": 300,
  "went_down_count": 700,
  "went_down_made_back_count": 500
}
```

### 2.2 Planned map-movement topics (new)

These topics are proposed for the moving-people map extension.
For planned movement payloads, service-zone naming is standardized to `zone_1` and `zone_2`.

#### Topic: `stadium/a4/halftime/state/movement`
- Published by:
  - `notebooks/agent_spectator_flow.ipynb` (or a new `agent_movement.ipynb`)
- Subscribed by:
  - `notebooks/dashboard_a4.ipynb` (or a new `dashboard_halftime_map.ipynb`)
- Message schema:
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

#### Topic: `stadium/a4/halftime/state/tasks`
- Published by:
  - `notebooks/agent_facility_manager.ipynb`
- Subscribed by:
  - `notebooks/dashboard_a4.ipynb`
  - `notebooks/agent_metrics.ipynb`
- Message schema:
```json
{
  "schema_version": "1.0",
  "run_id": "a4-run-1a2b3c4d",
  "timestamp_s": 121,
  "spectator_id": 1,
  "task": "toilet_w",
  "task_state": "queue_entered|service_started|service_completed"
}
```

## 3. Configuration Parameters

All parameters below should live in `config.yaml` and be loaded with `simulated_city.config.load_config()`.

### 3.1 MQTT broker settings

Use current profile-based settings:
- `mqtt.active_profiles`
- `mqtt.profiles.<profile>.host`
- `mqtt.profiles.<profile>.port`
- `mqtt.profiles.<profile>.tls`
- `mqtt.profiles.<profile>.username_env`
- `mqtt.profiles.<profile>.password_env`
- `mqtt.client_id_prefix`
- `mqtt.keepalive_s`
- `mqtt.base_topic`

Suggested defaults:
- Local profile host: `127.0.0.1`
- Local profile port: `1883`
- TLS local: `false`
- Keepalive: `60`
- Base topic: `simulated-city` (existing default)

### 3.2 GPS/map coordinates (for the movement map)

Add a dedicated map section (suggested):
- `halftime_map.center_lng`: `12.5683`
- `halftime_map.center_lat`: `55.6761`
- `halftime_map.zoom`: `17`
- `halftime_map.seat_area_bbox`: `[12.5679, 55.6759, 12.5687, 55.6766]`
- `halftime_map.zone_1_toilet_w`: `[12.5678, 55.6762]`
- `halftime_map.zone_1_toilet_m`: `[12.5679, 55.67622]`
- `halftime_map.zone_1_cafe`: `[12.5680, 55.67618]`
- `halftime_map.zone_2_toilet_w`: `[12.5689, 55.6760]`
- `halftime_map.zone_2_toilet_m`: `[12.5690, 55.67602]`
- `halftime_map.zone_2_cafe`: `[12.5691, 55.67598]`
- `halftime_map.shared_urinal`: `[12.5685, 55.6756]`

### 3.3 Thresholds and limits

Current halftime thresholds:
- `halftime.capacity.spectator_count`: `1000`
- `halftime.capacity.toilet_servers`: `24`
- `halftime.capacity.cafe_servers`: `16`
- `halftime.capacity.shared_urinal_total`: `16`
- `halftime.behavior.seat_leave_rate`: `0.70`
- `halftime.behavior.women_ratio`: `0.30`
- `halftime.behavior.queue_abandon_threshold_s`: `240`
- `halftime.behavior.queue_switch_threshold_people`: `15`
- `halftime.behavior.missed_kickoff_risk_window_s`: `120`
- `halftime.blocking.queue_people_per_line_threshold`: `15`
- `halftime.blocking.lines_considered`: `8`
- `halftime.blocking.walking_speed_factor_when_blocked`: `0.6`

### 3.4 Timing parameters

Current timing defaults:
- `halftime.seed`: `null` (new random run each time)
- `halftime.timing.halftime_duration_s`: `900`
- `halftime.timing.inter_facility_walk_s`: `30`
- `halftime.timing.walking_time_min_s`: `20`
- `halftime.timing.walking_time_mode_s`: `130`
- `halftime.timing.walking_time_max_s`: `360`
- `halftime.timing.toilet_service_s.min`: `45`
- `halftime.timing.toilet_service_s.max`: `220`
- `halftime.timing.cafe_service_s.min`: `20`
- `halftime.timing.cafe_service_s.max`: `90`
- `halftime.timing.urinal_service_s.min`: `15`
- `halftime.timing.urinal_service_s.max`: `70`

Suggested map publishing defaults:
- `halftime_map.publish_interval_s`: `1`
- `halftime_map.max_points_per_message`: `1000`

## 4. Architecture Decisions

### Phase 6.2 stream consistency rule

For all downstream consumers (congestion, metrics, dashboard state):
- lock to first valid `run_id` during a live session,
- reject other `run_id` values,
- require strictly increasing `timestamp_s` per stream.

This keeps restart/reconnect behavior stable and avoids mixing data from different runs.

### Notebooks to create

One notebook per agent is required.

Current notebooks in pipeline:
- `notebooks/agent_spectator_flow.ipynb`: trigger/spectator event generation
- `notebooks/agent_facility_manager.ipynb`: queue state + service processing
- `notebooks/agent_congestion.ipynb`: congestion state
- `notebooks/agent_metrics.ipynb`: KPI metrics
- `notebooks/dashboard_a4.ipynb`: subscriber dashboard map + KPI view
- `notebooks/kpi_bar_charts.ipynb`: single-run KPI chart diagnostics

Planned additions for movement map clarity:
- Option A (minimal change): extend `agent_spectator_flow.ipynb` + `dashboard_a4.ipynb`
- Option B (clean separation):
  - `notebooks/agent_movement.ipynb`
  - `notebooks/dashboard_halftime_map.ipynb`

### Library Code (`src/simulated_city/`)

Reusable components to keep in library modules (not in notebook cells):

#### Data models (dataclasses)
- `SpectatorPosition`
- `SpectatorTaskState`
- `MovementSnapshot`
- `MapGeometryConfig`
- existing `SimulationResult`, `SimulationTickState`, halftime config dataclasses

#### Utility functions
- config path/validation helpers
- MQTT payload builders/validators
- map coordinate normalization (`lng/lat`) helpers

#### Calculation helpers
- route interpolation between seat and zone points
- per-tick position update
- state-transition helpers for task lifecycle
- queue wait estimation helpers

### Classes vs Functions

Use classes for stateful, long-lived logic:
- Agent state containers (facility manager state, metrics aggregator state, congestion policy)
- Dashboard state and map-layer cache
- Dataclasses for payload/config models

Use functions for pure transformations/calculations:
- payload validation/build
- queue math, percentile math, wait calculations
- coordinate interpolation and movement step calculation
- topic parsing/routing helpers

### Photo-based map integration (later phase)

In a later phase, the simulation should use your A4 section photo as the visual layout reference.

- Section A4 is modeled as four seat zones with a total of 1000 spectators.
- The photo-defined stair layout is:
  - 2 upper stairs (yellow),
  - 2 lower stairs (blue),
  - 1 shared middle stairway (red circle) leading to the service concourse.
- Spectators must not go directly from seats to the shared middle stairway. They must first use their assigned local stair (yellow/blue) from their seat zone.
- After reaching the shared middle stairway, spectators continue to one of the two service zones (`zone_1` or `zone_2`) to perform toilet and/or cafe tasks based on stochastic behavior rules.
- After task completion, spectators return on the reverse route: service zone -> shared middle stairway -> original local stair -> original seat zone.
- Capacity constraints:
  - each of the four local stairs has a capacity of 250 people moving up/down,
  - the shared middle stairway has no explicit capacity limit in this model.
- Travel times from seat zone -> local stair -> shared middle stairway -> service zone are controlled by timing parameters in `config.yaml`.
- Movement remains stochastic per run, so outputs vary slightly run to run while respecting route and stair-capacity constraints.

## 5. Open Questions

Assumptions in this plan that should be validated:

- **Seat geometry:** For Phase 1.1, we use a simplified A4 seat grid (`halftime_map.seat_area_bbox` + generated seat points). Exact Parken seat coordinates are currently out of scope, but we can make the model more realistic in a later phase.
- **Zone coordinates:** Coordinates in `config.yaml` for toilet/cafe/urinal are functional simulation anchors, not surveyed stadium geometry.
- **Zone naming compatibility:** Existing queue/congestion payloads currently use `zone_a`/`zone_b`. Planned movement payloads use `zone_1`/`zone_2`. We should keep one canonical naming scheme and map legacy names during transition.
- **MQTT topic names:** We will finalize and add the new movement topics to `src/simulated_city/topic_schema.py`:
  - `stadium/a4/halftime/state/movement`
  - `stadium/a4/halftime/state/tasks`
- **Aggregate vs per-spectator events:** We keep aggregate topics for KPI reporting, and add per-spectator movement updates with throttling:
  - publish every `1s` (configurable),
  - send only changed spectators per tick,
  - cap payload size with `halftime_map.max_points_per_message` (default `1000`),
  - use one shared `run_id` across all agents for stream consistency.
- **Dashboard performance target:** The exact rendering target is still open (how many moving markers at once). The maximum possible is `1000` moving spectators, but practical load depends on scenario settings in `config.yaml` and update frequency.

## 6. Agreed run policies

- **Stochastic-run policy:** Each run uses a fresh random seed by default. Outputs vary slightly from run to run, while parameter changes in `config.yaml` drive larger, intentional shifts.
- **Run consistency policy:** All agents publish with the same `run_id` so movement map and KPI outputs show results from the same run.
- **MQTT stream consistency target:** Both `notebooks/kpi_bar_charts.ipynb` and the map dashboard should be MQTT-stream focused so they stay connected to the same run and show aligned people movement and KPI numbers.

