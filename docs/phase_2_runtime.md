# Phase 2 Runtime Guide (Configuration Integration)

This guide documents the Phase 2 implementation where halftime simulation parameters are loaded from `config.yaml` via `simulated_city.config.load_config()`.

## 1. What Was Created

### Notebooks and Scripts
- Updated notebook: `notebooks/agent_spectator_flow.ipynb`
- Updated config file: `config.yaml`
- Added test file: `tests/test_phase2_config_integration.py`

### Library Modules in `src/simulated_city/`
- Added: `config_models.py`
  - `ServiceDistributionConfig`
  - `HalftimeCapacityConfig`
  - `HalftimeTimingConfig`
  - `HalftimeBehaviorConfig`
  - `HalftimeBlockingConfig`
  - `HalftimeKpiConfig`
  - `HalftimeSimulationConfig`
- Updated: `config.py`
  - `AppConfig.halftime` field added
  - Typed parser and validation for `halftime.*` config group
- Updated: `simulation_core.py`
  - `simulate_halftime_with_config(...)`
  - `simulate_halftime_from_app_config(...)`

### Configuration Changes (`config.yaml`)
Added top-level `halftime` group with:
- `capacity` and facilities (including `shared_urinal_total`)
- `timing` and service distributions
- `behavior` thresholds
- `blocking` threshold settings
- `kpi.percentiles` with range requirement `1..100`

## 2. How to Run

### Workflow A: Notebook runtime
1. Start JupyterLab from repository root:
   - `.venv/bin/python -m jupyterlab`
2. Open notebook:
   - `notebooks/agent_spectator_flow.ipynb`
3. Run cells in order.

Expected behavior by cell:
- Cell 1: introduces Phase 2 config-driven workflow.
- Cell 2: imports config and simulation helpers.
- Cell 3: prints loaded parameters from `config.yaml`.
- Cell 4: runs simulation from config.
- Cell 5: prints KPI metrics.
- Cell 6: prints queue summary and completion message.

### Workflow B: Manual config-change check
1. Open `config.yaml` and change one value, for example:
   - `halftime.capacity.spectator_count: 1000` -> `800`
2. Return to notebook and rerun Cells 3-6.
3. Confirm Cell 3 prints `spectator_count: 800`.
4. Confirm KPI outputs in Cells 5-6 change from the previous run.

## 3. Expected Output

The values below assume a deterministic run (for example seed `42`) and spectator count `1000`.

### Cell 3 (Load Config)
Purpose: Load typed config and print simulation parameter values.

Expected text includes:
- `Loaded halftime parameters from config.yaml:`
- `seed: 42`
- `spectator_count: 1000`
- `halftime_duration_s: 900`
- `toilet_servers: 15`
- `cafe_servers: 10`
- `toilet_service_min_s: 60`
- `toilet_service_max_s: 180`
- `cafe_service_min_s: 30`
- `cafe_service_max_s: 60`
- `shared_urinal_total: 16`
- `kpi.percentiles: (1, 5, 10, 25, 50, 75, 90, 95, 99, 100)`

If different:
- Verify `config.yaml` was saved.
- Verify notebook kernel uses project environment.
- Verify Cell 3 was rerun after editing config.
- If `seed` is `null`, each run can differ (expected).

### Cell 4 (Run Simulation)
Purpose: Execute simulation from loaded app config.

Expected text:
- `Running simulation from config...`
- `Simulation complete: 901 ticks collected`

If different:
- If it errors with missing halftime section, add `halftime:` group in `config.yaml`.
- If ticks differ, check `halftime.timing.halftime_duration_s`.

### Cell 5 (KPI Print)
Purpose: Print main KPI values.

Expected values with current defaults:
- `Max Queue Length: 456`
- `Average Wait Time: 227.15 seconds`
- `Missed Kickoff Count: 831`
- `Total Served Tasks: 267`
- `Service Rate: 26.70%`

If different:
- For reproducible baseline numbers, set `seed: 42` in `halftime` config.
- Ensure no config values were changed after baseline.

### Cell 6 (Queue Summary)
Purpose: Show queue max/average/peak-time summary.

Expected structure:
- `=== Queue Evolution Summary ===`
- One line for toilet queue stats
- One line for cafe queue stats
- Final line stating config integration is active

If values differ, this is expected when config values change.

## 4. MQTT Topics (if applicable)

Phase 2 does not add MQTT publish/subscribe behavior.

- Topics published: none
- Topics subscribed: none
- Message schemas: not applicable

## 5. Debugging Guidance

### Verbose checks
- Re-run Cell 3 to inspect currently loaded values.
- Print `app_config.halftime` in notebook to inspect full typed config.

### Common errors
- `ValueError: Config key 'halftime' must be a mapping`
  - Fix YAML indentation under `halftime:`.
- `ValueError` about `percentiles` range
  - Ensure all `halftime.kpi.percentiles` values are between `1` and `100`.
- `ValueError` about service ranges
  - Ensure each service config has `min <= max`.

### Verify config-driven behavior
- Change one config value (for example `spectator_count`), rerun Cells 3-6, and confirm output changes.

## 6. Verification Commands

Run these from repository root:

```bash
python scripts/verify_setup.py
python scripts/validate_structure.py
python -m pytest
```
