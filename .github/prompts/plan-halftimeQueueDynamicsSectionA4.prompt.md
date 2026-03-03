## Implementation Plan: Section A4 Halftime Queue Simulation

This plan implements the approved design in small, testable phases. Each phase adds one capability and keeps the architecture aligned with workshop rules: one notebook per agent, MQTT communication, `config.yaml`-driven behavior, and `anymap-ts` dashboard visualization. The final system will report queue behavior for toilet/café, full wait-time percentile distribution (`P01..P100`), and missed kickoff count at halftime end (`900` seconds).

---

### Phase 1: Minimal Working Example (Single Agent, No MQTT)

**Goal:** Build one standalone notebook that simulates spectator flow and basic queueing logic without inter-agent communication.

**New Files:**
- `notebooks/agent_spectator_flow.ipynb` (notebook, create)
- `src/simulated_city/simulation_core.py` (library module, create)
- `tests/test_phase1_core.py` (test file, create)

**Implementation Details:**
- Implement core data structures for spectator state, queue state, and simulation tick state.
- Implement deterministic loop (with seed) for:
  - spectator departures
  - queue joins
  - queue service progression
  - return-to-seat timing
- Start with fixed in-notebook parameters (no config load yet).
- Output basic KPIs in notebook cells:
  - `max_queue_length`
  - `average_wait_s`
  - `missed_kickoff_count`

**Dependencies:**
- None expected (use existing dependencies only).

**Verification:**
- Run `python scripts/verify_setup.py`
- Run `python -m pytest`
- Manual:
  - Open `notebooks/agent_spectator_flow.ipynb`
  - Run all cells
  - Confirm KPI values are produced and simulation completes

**Investigation:**
- Validate that halftime timing (`900s`) and service-time assumptions produce realistic queue growth.
- Confirm baseline behavior before adding config or MQTT complexity.

---

### Phase 2: Add Configuration Integration

**Goal:** Move simulation parameters from hardcoded values into `config.yaml` and use `simulated_city.config.load_config()`.

**New Files:**
- `config.yaml` (config file, modify)
- `src/simulated_city/config_models.py` (library module/dataclasses, create)
- `src/simulated_city/simulation_core.py` (library module, modify)
- `tests/test_phase2_config_integration.py` (test file, create)
- `docs/config.md` (documentation, modify)

**Implementation Details:**
- Add/validate config groups from concepts:
  - capacity and facilities (including shared urinal total)
  - timing/service distributions
  - behavior thresholds
  - blocking threshold
  - KPI percentile settings (`1..100`)
- Use typed config models and pass config into simulation core.
- Ensure defaults and validation are explicit for beginner readability.

**Dependencies:**
- None expected (PyYAML already present).

**Verification:**
- Run `python scripts/verify_setup.py`
- Run `python -m pytest`
- Manual:
  - Change one config value (e.g., spectator count)
  - Re-run notebook and confirm outputs change accordingly

**Investigation:**
- Confirm config schema is stable enough for all later agents.
- Validate consistency of naming with concepts and MQTT schemas.

---

### Phase 3: Add MQTT Publishing (Single Publishing Agent)

**Goal:** Enable one agent notebook to publish simulation state/events to MQTT topics.

**New Files:**
- `notebooks/agent_spectator_flow.ipynb` (notebook, modify)
- `src/simulated_city/topic_schema.py` (library module, create)
- `src/simulated_city/mqtt_payloads.py` (library module, create)
- `tests/test_phase3_mqtt_publish.py` (test file, create)
- `docs/mqtt.md` (documentation, modify)

**Implementation Details:**
- Use `simulated_city.mqtt.connect_mqtt()` and `publish_json_checked()`.
- Publish to:
  - `stadium/a4/halftime/events/spectator`
- Include required envelope fields:
  - `schema_version`, `run_id`, `timestamp_s`
- Add JSON payload validation helpers before publish.

**Dependencies:**
- None expected (`paho-mqtt` already present).

**Verification:**
- Run `python scripts/verify_setup.py`
- Run `python -m pytest`
- Manual:
  - Run MQTT broker
  - Run notebook
  - Confirm events are published on the expected topic

**Investigation:**
- Confirm publish frequency and payload size are practical.
- Validate message schema stability before adding subscriber agents.

---

### Phase 4: Add Second Agent with MQTT Subscription

**Goal:** Introduce inter-agent communication where one agent subscribes to published events and emits queue state.

**New Files:**
- `notebooks/agent_facility_manager.ipynb` (notebook, create)
- `notebooks/agent_spectator_flow.ipynb` (notebook, modify)
- `src/simulated_city/facility_manager.py` (library module, create)
- `tests/test_phase4_agent_communication.py` (test file, create)

**Implementation Details:**
- `agent_facility_manager.ipynb` subscribes to:
  - `stadium/a4/halftime/events/spectator`
- `agent_facility_manager.ipynb` publishes:
  - `stadium/a4/halftime/state/queues`
- Implement queue state logic for:
  - café/toilet per zone
  - shared men’s urinal queue
- Keep each notebook independent and restart-safe.

**Dependencies:**
- None expected.

**Verification:**
- Run `python scripts/verify_setup.py`
- Run `python -m pytest`
- Manual:
  - Start broker
  - Run spectator agent + facility manager agent
  - Confirm queue state messages update as events arrive

**Investigation:**
- Confirm agent decoupling and restart behavior.
- Validate shared urinal modeling across both zones.

---

### Phase 5: Add Dashboard Visualization (anymap-ts)

**Goal:** Build a dashboard notebook that subscribes to agent topics and visualizes queue/wait outcomes over halftime.

**New Files:**
- `notebooks/dashboard_a4.ipynb` (notebook, create)
- `src/simulated_city/dashboard_views.py` (library module, create)
- `tests/test_phase5_dashboard_data_shapes.py` (test file, create)
- `docs/maplibre_anymap.md` (documentation, modify)

**Implementation Details:**
- Subscribe to:
  - `stadium/a4/halftime/state/queues`
  - `stadium/a4/halftime/metrics/kpi`
  - `stadium/a4/halftime/state/congestion` (if available by this phase)
- Render:
  - queue length trends by facility
  - wait-time distribution from `wait_percentiles_s` (`P01..P100`)
  - missed kickoff count
- Use `anymap-ts` only (no folium/plotly/matplotlib for live map use).

**Dependencies:**
- None expected if notebooks extras already installed.
- If missing: ensure `anymap-ts[all]` is in `pyproject.toml` notebooks extras.

**Verification:**
- Run `python scripts/verify_setup.py`
- Run `python -m pytest`
- Manual:
  - Start publisher/subscriber agents
  - Open dashboard notebook and run all cells
  - Confirm charts/map update from live MQTT stream

**Investigation:**
- Confirm dashboard readability and refresh cadence.
- Ensure displayed KPIs match raw payloads.

---

### Phase 6+: Congestion, Metrics Agent, and Final Scenario Quality

**Goal:** Complete advanced behavior: congestion agent, full KPI aggregation, and final scenario validation.

**New Files:**
- `notebooks/agent_congestion.ipynb` (notebook, create)
- `notebooks/agent_metrics.ipynb` (notebook, create)
- `src/simulated_city/congestion.py` (library module, create)
- `src/simulated_city/metrics.py` (library module, create)
- `tests/test_phase6_congestion_metrics.py` (test file, create)
- `docs/testing.md` (documentation, modify)

**Implementation Details:**
- Congestion agent:
  - subscribe to queue state
  - apply per-zone total café blocking rule
  - publish congestion state
- Metrics agent:
  - aggregate full run KPIs
  - publish `average_wait_s`, `wait_percentiles_s`, `missed_kickoff_count`
- Enforce final decisions:
  - missed kickoff at exactly `900s`
  - no external disruption events
  - controlled group coordination policy

**Dependencies:**
- None expected.

**Verification:**
- Run `python scripts/verify_setup.py`
- Run `python scripts/validate_structure.py`
- Run `python -m pytest`
- Manual:
  - Start all agent notebooks + dashboard
  - Run one full halftime scenario
  - Confirm outputs include:
    - toilet/café waiting behavior
    - full percentile profile (`P01..P100`)
    - missed kickoff count

**Investigation:**
- Compare multiple scenarios by changing config inputs.
- Check sensitivity to early-peak arrivals, blocking threshold, and group coordination share.

---

### Phase 7 (Optional): Packaging, Usability, and Instructor Review Readiness

**Goal:** Make execution and review smoother without changing core simulation logic.

**New Files:**
- `docs/setup.md` (documentation, modify)
- `docs/overview.md` (documentation, modify)
- `docs/mqtt.md` (documentation, modify)
- `README.md` (modify, phase links and usage summary)

**Implementation Details:**
- Add clear “run order” for notebooks.
- Add troubleshooting for broker connectivity and topic verification.
- Add a short KPI interpretation guide for instructor review.

**Dependencies:**
- None.

**Verification:**
- Run `python scripts/verify_setup.py`
- Run `python -m pytest`
- Manual:
  - Follow docs from clean restart and confirm reproducibility

**Investigation:**
- Ensure a new student can run the system from docs only.
- Ensure all docs match actual topic names and config keys.
