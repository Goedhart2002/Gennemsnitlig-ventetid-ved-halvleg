# Concepts: Section A4 Halftime Queue Simulation

## 1. System Overview

### Project Scope
This project models crowd movement and queue behavior during a 15-minute halftime window in stadium Section A4. The system focuses on time-constrained spectator decisions, limited facility capacity, and congestion effects from queue spillover.

### Trigger (Who/What is moving?)
- **Primary agents:** Spectators in Section A4 (approximately 1,000 people).
- **Environment dynamics:**
  - Fixed halftime duration of 15 minutes.
  - Uneven walking times between seats and facilities (roughly 0.5 to 5 minutes one way).
  - Demand surge shortly after halftime starts (strong peak in first 3 to 5 minutes).
  - Behavioral variation: toilet first, café first, one activity only, or coordinated group strategy.

### Observer (What does the city see?)
The city state is observed through simulation events and queue telemetry:
- Arrival events to each service queue.
- Queue length snapshots per facility line.
- Service start and finish events.
- Path-blocking state when queue lengths exceed walkway capacity.
- Individual remaining-time estimates to decide whether a spectator can complete actions and return before kickoff.

### Control Center (The logic)
The decision and scheduling logic processes observed state to update outcomes:
- Route and sequence choice for each spectator based on demand, time remaining, and proximity.
- Queue assignment across two identical café zones.
- Stochastic service durations for realistic throughput.
- Congestion penalties when queue spillover blocks concourse movement.
- Dynamic abandonment/skip behavior when expected completion exceeds available halftime time.

### Response (What happens next?)
The system emits updated simulation state and summary metrics:
- Facility utilization and queue evolution over halftime.
- Spectator-level completion status (served/not served, returned/missed kickoff).
- Scenario KPIs:
  - Maximum queue length
  - Average waiting time
  - Missed kickoff count

---

## 2. MQTT Architecture

This simulation uses independent agent notebooks that exchange state through MQTT. Each notebook owns one responsibility and shares updates via topics instead of shared memory.

### Topic Namespace Convention
- Base topic: `stadium/a4/halftime`
- All payloads include `schema_version`, `run_id`, and `timestamp_s` for traceability.
- Topics are split by concern: events, state, control, metrics, and diagnostics.

### Topic Catalog

#### 1) `stadium/a4/halftime/events/spectator`
- **Published by:** `agent_spectator_flow.ipynb`
- **Subscribed by:**
  - `agent_facility_manager.ipynb`
  - `agent_congestion.ipynb`
  - `dashboard_a4.ipynb`
- **Purpose:** Announces spectator intent and movement events.
- **Influence on simulation:** Drives demand generation at facilities and is the primary source for queue growth.
- **Message schema (JSON):**

```json
{
  "schema_version": "1.0",
  "run_id": "string",
  "timestamp_s": 0,
  "spectator_id": "string",
  "group_id": "string|null",
  "seat_zone": "string",
  "action": "leave_seat|join_queue|abandon_queue|return_seat",
  "target_facility": "cafe|toilet_w|toilet_m|urinal",
  "zone_id": "zone_1|zone_2|shared_urinal",
  "time_remaining_s": 0
}
```

#### 2) `stadium/a4/halftime/state/queues`
- **Published by:** `agent_facility_manager.ipynb`
- **Subscribed by:**
  - `agent_spectator_flow.ipynb`
  - `agent_congestion.ipynb`
  - `dashboard_a4.ipynb`
- **Purpose:** Broadcasts queue lengths and service capacity snapshots.
- **Influence on simulation:** Controls decision logic for join/switch/abandon behavior and directly affects waiting-time estimates.
- **Message schema (JSON):**

```json
{
  "schema_version": "1.0",
  "run_id": "string",
  "timestamp_s": 0,
  "queues": [
    {
      "zone_id": "zone_1|zone_2|shared_urinal",
      "facility": "cafe|toilet_w|toilet_m|urinal",
      "line_id": "string",
      "queue_length": 0,
      "servers_total": 0,
      "servers_busy": 0,
      "estimated_wait_s": 0
    }
  ]
}
```

#### 3) `stadium/a4/halftime/state/congestion`
- **Published by:** `agent_congestion.ipynb`
- **Subscribed by:**
  - `agent_spectator_flow.ipynb`
  - `agent_facility_manager.ipynb`
  - `dashboard_a4.ipynb`
- **Purpose:** Indicates path blocking and movement slowdown factors.
- **Influence on simulation:** Increases walking time under heavy crowding, reducing effective service opportunity before kickoff.
- **Blocking trigger rule:** Blocking is evaluated by per-zone total café queue load (not per-line and not mixed logic).
- **Message schema (JSON):**

```json
{
  "schema_version": "1.0",
  "run_id": "string",
  "timestamp_s": 0,
  "zone_id": "zone_1|zone_2",
  "is_blocked": true,
  "blocking_lines": ["string"],
  "slowdown_factor": 1.0,
  "threshold_people_per_zone_cafe_total": 15
}
```

Note: `threshold_people_per_zone_cafe_total` means the sum of café queues in one zone. If the sum reaches this threshold, movement slowdown is activated for that zone.

#### 4) `stadium/a4/halftime/metrics/kpi`
- **Published by:** `agent_metrics.ipynb`
- **Subscribed by:**
  - `dashboard_a4.ipynb`
- **Purpose:** Publishes rolling and final KPI summaries.
- **Influence on simulation:** Provides run-level performance visibility and enables scenario comparisons.
- **Message schema (JSON):**

```json
{
  "schema_version": "1.0",
  "run_id": "string",
  "timestamp_s": 0,
  "is_final": false,
  "max_queue_length": 0,
  "average_wait_s": 0,
  "wait_percentiles_s": [
    { "p": 1, "wait_s": 0 },
    { "p": 2, "wait_s": 0 },
    { "p": 3, "wait_s": 0 }
  ],
  "missed_kickoff_count": 0,
  "spectators_processed": 0
}
```

Note: `wait_percentiles_s` contains the full wait-time percentile curve (`P01..P100`) so you can read both “wait less than X” and “wait more than X” behavior.

#### 5) `stadium/a4/halftime/control/run`
- **Published by:** `dashboard_a4.ipynb`
- **Subscribed by:**
  - `agent_spectator_flow.ipynb`
  - `agent_facility_manager.ipynb`
  - `agent_congestion.ipynb`
  - `agent_metrics.ipynb`
- **Purpose:** Run orchestration (start/stop/reset) for synchronized simulation runs.
- **Influence on simulation:** Ensures all agents run in the same time window and use the same seed/run identifier.
- **Message schema (JSON):**

```json
{
  "schema_version": "1.0",
  "command": "start|stop|reset",
  "run_id": "string",
  "seed": 42,
  "start_time_s": 0,
  "duration_s": 900
}
```

#### 6) `stadium/a4/halftime/debug/errors`
- **Published by:** Any agent notebook
- **Subscribed by:** `dashboard_a4.ipynb`
- **Purpose:** Operational diagnostics and validation errors.
- **Influence on simulation:** Does not change behavior directly, but improves reliability and troubleshooting speed.
- **Message schema (JSON):**

```json
{
  "schema_version": "1.0",
  "run_id": "string|null",
  "timestamp_s": 0,
  "agent": "string",
  "severity": "warning|error",
  "message": "string",
  "context": {}
}
```

### Shared Message Semantics
- `timestamp_s` starts at `0` at run start and increases through the halftime window.
- Numeric `0` values in schema examples are placeholders, not fixed production values.
- `run_id` ties all messages to one simulation execution for clean aggregation.

---

## 3. Configuration Parameters

All parameters below should be defined in `config.yaml` and loaded via `simulated_city.config.load_config()`. Keep hardcoded values out of notebooks.

### MQTT Broker Settings
- `mqtt.host`: `localhost` (broker hostname)
- `mqtt.port`: `1883` (default non-TLS port)
- `mqtt.tls`: `false` (set `true` in production/networked environments)
- `mqtt.username_env`: `MQTT_USERNAME` (env var name, not plaintext credential)
- `mqtt.password_env`: `MQTT_PASSWORD` (env var name, not plaintext credential)
- `mqtt.base_topic`: `stadium/a4/halftime` (topic namespace root)
- `mqtt.client_prefix`: `a4_sim` (client-id prefix for all agents)
- `mqtt.qos`: `1` (at-least-once delivery for reliability)
- `mqtt.keepalive_s`: `60` (connection liveness interval)

### Location / Geometry Parameters
If map visualization is used, define representative coordinates for Section A4 and facility points.
- `location.stadium_lat`: `55.6761`
- `location.stadium_lon`: `12.5683`
- `location.section_a4_lat`: `55.6765`
- `location.section_a4_lon`: `12.5688`
- `location.zone_1_lat`: `55.6766`
- `location.zone_1_lon`: `12.5689`
- `location.zone_2_lat`: `55.6764`
- `location.zone_2_lon`: `12.5687`

These coordinates are placeholders for planning and dashboard visualization. Replace with real stadium coordinates before scenario analysis.

### Capacity, Thresholds, and Limits
- `simulation.spectator_count`: `1000` (population size)
- `facilities.zones`: `2` (two identical service areas)
- `facilities.cafe_per_zone`: `1`
- `facilities.toilet_w_per_zone`: `6`
- `facilities.toilet_m_per_zone`: `6`
- `facilities.urinal_shared_total`: `12` (one shared men's urinal area for both zones)
- `queues.max_lines_total`: `8` (upper bound for concurrent active lines)
- `queues.blocking_threshold_people_per_zone_cafe_total`: `15` (blocking trigger by total café queue load within each zone)
- `movement.blocking_slowdown_factor`: `0.35` (35% walking-speed penalty under blocking)

These values drive hard capacity constraints and are the strongest levers for congestion outcomes.

Note: Keep the blocking threshold key aligned with the congestion topic field name to avoid implementation mismatches.

### Timing and Distribution Parameters
- `timing.halftime_duration_s`: `900` (15 minutes)
- `timing.walk_time_min_s`: `30`
- `timing.walk_time_avg_s`: `120`
- `timing.walk_time_max_s`: `300`
- `service.cafe_min_s`: `30`
- `service.cafe_max_s`: `60`
- `service.toilet_min_s`: `60`
- `service.toilet_max_s`: `180`
- `service.urinal_min_s`: `30`
- `service.urinal_max_s`: `90`
- `arrivals.pre_halftime_share`: `0.05`
- `arrivals.early_peak_share`: `0.75`
- `arrivals.late_share`: `0.20`

Arrival shares should sum to `1.0` and represent the expected time-distribution of departures from seats.

### Behavior Parameters
- `behavior.abandon_if_estimated_wait_over_s`: `420` (leave queue if estimated wait > 7 minutes)
- `behavior.skip_if_time_remaining_under_s`: `240` (skip new activity if < 4 minutes remain)
- `behavior.group_coordination_share`: `0.15` (share of spectators coordinating in groups)
- `behavior.no_trip_if_low_time_share`: `0.10` (share choosing to stay seated under low remaining time)
- `simulation.random_seed`: `42` (reproducibility)

Behavior parameters primarily shape realism and strategic adaptation under time pressure.

### KPI Reporting Parameters
- `kpi.percentile_min`: `1`
- `kpi.percentile_max`: `100`
- `kpi.percentile_step`: `1`
- `kpi.publish_full_percentile_profile`: `true`

These settings ensure the dashboard can show wait-time distribution for every percentile from 1% to 100%.

---

## 4. Architecture Decisions

### Notebooks to Create
One notebook per agent, plus one dashboard notebook. This keeps simulation logic modular and restart-safe.

- `notebooks/agent_spectator_flow.ipynb`
  - Generates spectator departures, route choices, and queue join/leave events.
  - Owns behavior decisions and publishes spectator events.
- `notebooks/agent_facility_manager.ipynb`
  - Manages café/toilet service queues per zone and one shared men’s urinal queue.
  - Publishes queue state snapshots and service completions.
- `notebooks/agent_congestion.ipynb`
  - Detects queue spillover and computes movement slowdown effects.
  - Publishes congestion state for movement adjustment.
- `notebooks/agent_metrics.ipynb`
  - Aggregates simulation events into KPIs and periodic summaries.
  - Publishes live and final run metrics.
- `notebooks/dashboard_a4.ipynb`
  - Subscribes to all state topics and visualizes live status (map + KPI panels via anymap-ts).
  - Sends run-control commands (`start|stop|reset`) and coordinates execution.

### Library Code (`src/simulated_city/`)
Reusable logic should stay in library modules to keep notebooks simple and focused.

#### Data Models (dataclasses)
- `SimulationRunConfig`
- `FacilityConfig`
- `BehaviorConfig`
- `SpectatorEvent`
- `QueueState`
- `CongestionState`
- `KpiSnapshot`

These models provide typed structure for config/state and reduce schema drift across notebooks.

#### Utility Functions
- Topic builders and validators (topic naming consistency).
- JSON payload validation helpers before publish/after receive.
- Time-window helpers (remaining-time, kickoff deadline checks).
- Input/output normalization for notebook-agent boundaries.

These helpers ensure all agents publish consistent payloads and simplify debugging.

#### Calculation Helpers
- Queue waiting-time estimation.
- Facility assignment scoring (zone and line choice).
- Congestion impact calculation (slowdown factor by spillover state).
- KPI aggregation functions (max queue, average wait, missed kickoff).

These calculations remain pure and testable outside notebook runtime.

### Classes vs Functions

#### Use classes for
- **Stateful agents** that keep internal mutable state across ticks/events:
  - Spectator flow agent
  - Facility manager agent
  - Congestion agent
  - Metrics agent
- **Dataclasses** for structured messages and configuration objects.

Classes are preferred where internal state changes over time and multiple updates must remain consistent.

#### Use functions for
- Pure calculations and transformations:
  - Sampling service times
  - Converting events to queue deltas
  - Updating counters
  - Computing summaries and rolling metrics
- Stateless validation and serialization helpers.

Functions are preferred where input-output behavior is deterministic and side-effect free.

---

## 5. Decisions and Open Questions

This section records confirmed decisions and remaining assumptions to validate before implementation. Keeping these explicit reduces refactoring later.

- Seating layout assumption: Section A4 is modeled as four seat blocks (upper-left, upper-right, lower-left, lower-right) connected through a shared middle stair corridor. All outbound spectator flow passes this middle corridor before reaching café/toilet zones.
- Queue switching and coordination decision: spectators are allowed to switch queues in controlled cases (not only abandon-and-retry). This is especially important for realistic group behavior.
- Group coordination behavior (confirmed requirement):
  - Typical coordinated groups are size 2–4.
  - Group members may split tasks in parallel (for example one goes to café, one goes to toilet).
  - If the café task finishes first, the café member waits and the pair returns together after the toilet task is done.
  - If the toilet task finishes first, the toilet member may join the café queue and take over queue position while the café member completes toilet service.
  - If time runs low, groups may complete only one task and abandon the second, then return together.
- Final decision: Queue handoff/switching is limited to one transfer per group member per halftime trip.
- Final decision: Coordination is enabled for groups up to 4 people, but only one active handoff pair is allowed at a time.

### Group Coordination Policy (4-Person Case)

For a coordinated group of 4 spectators, apply the following operational rules:

1. **Initial split**
  - Two group members join a toilet queue.
  - Two group members join a café queue.

2. **Swap trigger**
  - When a toilet-queue member completes toilet service, they may swap with a teammate currently holding a café-queue position.

3. **Swap priority rule**
  - Always swap with a teammate who has **not yet** been in a toilet queue.
  - This ensures toilet access is rotated fairly while preserving café queue progress.

4. **Simultaneous toilet completion**
  - If both toilet-queue members finish at the same time, both may swap into the two café positions in the same update step.
  - Both swaps must still respect the priority rule (swap with teammates who have not yet queued for toilet).

5. **Queue-space preservation rule**
  - The group should preserve café queue positions continuously through handoffs.
  - At no point should both café positions be released unless the group explicitly abandons café service.

6. **Stop conditions**
  - Stop swapping when all group members who intend to use toilets have completed toilet service, or when remaining halftime time is below abandonment threshold.

- Final decision: No unisex facility is modeled. Facility capacities are fixed as women toilets `6` per zone, men toilets `6` per zone, and one shared men’s urinal area with `12` spots total across both zones.
- Final decision: Urinal demand is modeled within men’s demand routing (men choose between men’s toilet queue and shared urinal queue).
- Final decision: Queue blocking is triggered by per-zone total café queue load (not per-line and not a combined per-line/per-zone trigger).
- Final decision: Blocking affects walking speed only; service throughput is unchanged.
- Final decision: Missed kickoff is counted strictly at `900` seconds, with no grace period.
- Final decision: KPI output includes average wait plus the full wait-time percentile profile (`P01..P100`).
- Final decision: No external disruption events (goal delay, concession outage, cleaning closure) are included in halftime scenarios.

### Suggested Validation Order
1. Confirm capacity and blocking rules (`queues.max_lines_total`, `queues.blocking_threshold_people_per_zone_cafe_total`).
2. Confirm behavior model assumptions (queue switching, abandonment, group coordination).
3. Confirm fairness and demand split assumptions (facility preference and demographic routing).
4. Confirm KPI definition and reporting precision for final evaluation (`average_wait_s`, full `wait_percentiles_s` profile from `P01..P100`).
