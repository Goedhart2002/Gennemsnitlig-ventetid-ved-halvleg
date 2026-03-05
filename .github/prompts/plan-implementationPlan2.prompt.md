## Plan: A4 Movement Implementation 2 Track

This plan uses the approved design in [docs/concepts_2.md](docs/concepts_2.md) and defines a new 1.2–6.2+ delivery track. It keeps the workshop constraints intact: distributed notebooks, MQTT communication, config-first runtime, and anymap-ts visualization. The sequence starts with a local minimal agent (no MQTT), then adds config loading, publishing, multi-agent communication, dashboard map rendering, and finally hardening/performance phases. Existing runtime modules and tests are reused as references to reduce risk and keep changes teachable.

### Phase 1.2: Minimal working example (single agent, no MQTT)

**Goal:** Produce one runnable notebook that simulates halftime movement/task intent locally and outputs deterministic data shapes without network messaging.

**New Files:**
- Modify notebook: [notebooks/agent_spectator_flow.ipynb](notebooks/agent_spectator_flow.ipynb) (notebook)
- Reuse library logic from [src/simulated_city/simulation_core.py](src/simulated_city/simulation_core.py) (library module)
- Optional helper doc update: [docs/phase_1_runtime.md](docs/phase_1_runtime.md) (doc)

**Implementation Details:**
- Implement a minimal per-spectator lifecycle using existing `simulate_halftime` behavior as baseline.
- Keep outputs in notebook memory only (no MQTT client calls).
- Normalize planned movement naming for this track to `zone_1` and `zone_2` in local output examples.
- Use existing timing/behavior semantics from config defaults as reference values.

**Dependencies:**
- No new package required.

**Verification:**
- Run `python scripts/verify_setup.py`
- Run `python -m pytest tests/test_phase1_core.py`
- Manual: open [notebooks/agent_spectator_flow.ipynb](notebooks/agent_spectator_flow.ipynb), run all cells, confirm local tick/state output appears and varies when seed is `null`.

**Investigation:**
- Understand how current spectator states are represented in `simulation_core`.
- Confirm the minimal state machine mapping for this track before adding transport.

---

### Phase 2.2: Add configuration file integration

**Goal:** Load all simulation and movement-map settings from `config.yaml` via typed config models.

**New Files:**
- Modify config parser/model: [src/simulated_city/config_models.py](src/simulated_city/config_models.py) (library module)
- Modify loader: [src/simulated_city/config.py](src/simulated_city/config.py) (library module)
- Modify defaults: [config.yaml](config.yaml) (config)
- Add/extend tests: [tests/test_phase2_config_integration.py](tests/test_phase2_config_integration.py), [tests/test_config.py](tests/test_config.py) (tests)
- Optional docs sync: [docs/config.md](docs/config.md), [docs/phase_2_runtime.md](docs/phase_2_runtime.md) (docs)

**Implementation Details:**
- Add typed `halftime_map.*` fields (center, zoom, coordinates, publish interval, payload cap).
- Keep validation explicit (bounds, required keys, positive intervals).
- Record zone naming compatibility decision (`zone_1`/`zone_2` canonical for movement track).
- Preserve existing halftime behavior parsing (`seed`, `women_ratio`, timing/capacity).

**Dependencies:**
- No new package required.

**Verification:**
- Run `python scripts/verify_setup.py`
- Run `python -m pytest tests/test_phase2_config_integration.py tests/test_config.py`
- Manual: print loaded config in notebook and confirm `halftime_map` keys parse correctly.

**Investigation:**
- Decide where compatibility mapping from `zone_a`/`zone_b` to `zone_1`/`zone_2` lives (config adapter vs payload adapter).

---

### Phase 3.2: Add MQTT publishing (single agent publishes)

**Goal:** Publish spectator/movement state events from one agent to defined A4 topics.

**New Files:**
- Modify/extend topics: [src/simulated_city/topic_schema.py](src/simulated_city/topic_schema.py) (library module, constants already present for movement/task)
- Modify payload validation/builders: [src/simulated_city/mqtt_payloads.py](src/simulated_city/mqtt_payloads.py) (library module)
- Modify publisher notebook: [notebooks/agent_spectator_flow.ipynb](notebooks/agent_spectator_flow.ipynb) (notebook)
- Add/extend tests: [tests/test_phase3_mqtt_publish.py](tests/test_phase3_mqtt_publish.py) (test)
- Optional docs sync: [docs/mqtt.md](docs/mqtt.md), [docs/phase_3_runtime.md](docs/phase_3_runtime.md) (docs)

**Implementation Details:**
- Use `connect_mqtt` and `publish_json_checked`.
- Publish to spectator event topic and movement state topic with shared `run_id`.
- Add schema fields: `schema_version`, `timestamp_s`, `spectator_id`, `state`, `target`, `lng`, `lat`.
- Enforce publish throttle and payload caps from config.

**Dependencies:**
- No new package required (`paho-mqtt` already present).

**Verification:**
- Run `python scripts/verify_setup.py`
- Run `python -m pytest tests/test_phase3_mqtt_publish.py tests/test_mqtt_profiles.py`
- Manual: run publisher notebook and verify messages appear on broker with expected topic/payload shape.

**Investigation:**
- Confirm topic policy relative to `mqtt.base_topic` vs fixed `stadium/a4/...` constants.

---

### Phase 4.2: Add second agent with MQTT subscription

**Goal:** Enable two-agent communication where a downstream agent consumes published events and updates queue/task state.

**New Files:**
- Modify subscriber notebook: [notebooks/agent_facility_manager.ipynb](notebooks/agent_facility_manager.ipynb) (notebook)
- Reuse/update state logic: [src/simulated_city/facility_manager.py](src/simulated_city/facility_manager.py) (library module)
- Extend payload helpers: [src/simulated_city/mqtt_payloads.py](src/simulated_city/mqtt_payloads.py) (library module)
- Add/extend tests: [tests/test_phase4_agent_communication.py](tests/test_phase4_agent_communication.py) (test)
- Optional docs sync: [docs/phase_4_runtime.md](docs/phase_4_runtime.md) (doc)

**Implementation Details:**
- Subscribe facility manager to spectator/movement topics.
- Emit queue/task state updates with same `run_id`.
- Apply canonical naming internally and map legacy names only at boundaries if needed.
- Keep agent loops simple and explicit for teachability.

**Dependencies:**
- No new package required.

**Verification:**
- Run `python scripts/verify_setup.py`
- Run `python -m pytest tests/test_phase4_agent_communication.py`
- Manual: start publisher and subscriber notebooks; confirm subscriber reacts to live messages and publishes queue/task updates.

**Investigation:**
- Validate state transition timing assumptions between movement and queue entry.

---

### Phase 5.2: Add dashboard visualization (anymap-ts)

**Goal:** Render live movement + queue/KPI state on dashboard using anymap-ts.

**New Files:**
- Modify dashboard notebook: [notebooks/dashboard_a4.ipynb](notebooks/dashboard_a4.ipynb) (notebook)
- Optional new dashboard notebook: [notebooks/dashboard_halftime_map.ipynb](notebooks/dashboard_halftime_map.ipynb) (notebook, if separation chosen)
- Reuse parser/state helpers: [src/simulated_city/dashboard_views.py](src/simulated_city/dashboard_views.py), [src/simulated_city/maplibre_live.py](src/simulated_city/maplibre_live.py) (library modules)
- Add/extend tests: [tests/test_phase5_dashboard_data_shapes.py](tests/test_phase5_dashboard_data_shapes.py), [tests/test_maplibre_live.py](tests/test_maplibre_live.py) (tests)
- Optional docs sync: [docs/maplibre_anymap.md](docs/maplibre_anymap.md), [docs/phase_5_runtime.md](docs/phase_5_runtime.md) (docs)

**Implementation Details:**
- Subscribe to movement, queue, congestion, and KPI topics.
- Render moving points with update throttling and map geometry from `halftime_map`.
- Keep map stack on anymap-ts only for live visualization.
- Display run metadata (`run_id`, timestamps) for stream consistency checks.

**Dependencies:**
- No new package required (`anymap-ts[all]` already present).

**Verification:**
- Run `python scripts/verify_setup.py`
- Run `python -m pytest tests/test_phase5_dashboard_data_shapes.py tests/test_maplibre_live.py`
- Manual: run agents + dashboard, verify live movement appears and aligns with queue/KPI stream values.

**Investigation:**
- Measure rendering behavior under high marker counts and tune publish interval/payload size.

---

### Phase 6.2+: Integration hardening, congestion/metrics alignment, and performance

**Goal:** Stabilize full multi-agent runtime, resolve naming/topic consistency, and document operational limits.

**New Files:**
- Modify congestion/metrics logic: [src/simulated_city/congestion.py](src/simulated_city/congestion.py), [src/simulated_city/metrics.py](src/simulated_city/metrics.py) (library modules)
- Extend tests: [tests/test_phase6_congestion_metrics.py](tests/test_phase6_congestion_metrics.py), plus integration assertions in phase 3–5 tests
- Update docs: [docs/phase_6_runtime.md](docs/phase_6_runtime.md), [docs/testing.md](docs/testing.md), [docs/mqtt.md](docs/mqtt.md), [docs/concepts_2.md](docs/concepts_2.md)

**Implementation Details:**
- Ensure one shared `run_id` across all agents and dashboards.
- Finalize canonical zone naming and compatibility mapping strategy.
- Enforce payload-size and publish-rate limits for dashboard performance.
- Add robustness checks for late subscribers/reconnect and message ordering assumptions.

**Dependencies:**
- No new package required unless profiling tooling is explicitly added later.

**Verification:**
- Run `python scripts/verify_setup.py`
- Run `python scripts/validate_structure.py`
- Run `python -m pytest`
- Manual: execute end-to-end notebook sequence and confirm movement, queue, congestion, and KPI stay synchronized for one run.

**Investigation:**
- Determine practical max moving markers and acceptable update interval on target hardware.
- Confirm whether topic constants should remain fixed `stadium/a4/...` or derive from `mqtt.base_topic`.
