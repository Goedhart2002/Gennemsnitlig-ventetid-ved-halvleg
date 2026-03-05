# Phase 1.2 Runtime Guide

This guide validates Phase 1.2 only: one local spectator-flow notebook with no MQTT communication.

## 1. What Was Created

### Files changed
- Updated notebook: `notebooks/agent_spectator_flow.ipynb`
- Added runtime guide: `docs/phase_1.2_runtime.md`

### Library changes
- No new library modules were added in `src/simulated_city/` for this phase.
- Phase 1.2 reuses existing logic via `simulate_halftime_from_app_config()`.

### Configuration changes
- No new keys were added to `config.yaml` in this phase.
- Notebook runtime values are loaded with `simulated_city.config.load_config()`.

## 2. How to Run

### Pre-check
From repository root:

```bash
python scripts/verify_setup.py
```

### Main workflow
1. Start JupyterLab:

   ```bash
   python -m jupyterlab
   ```

2. Open `notebooks/agent_spectator_flow.ipynb`.
3. Run cells 1 to 7 in order.
4. Confirm pass criteria:
   - config metadata prints,
   - KPI section prints,
   - local movement/task structures print with `zone_1` and `zone_2`,
   - shape checks are `True`,
   - final line confirms no MQTT connection.

### Variability check (`halftime.seed: null`)
1. Re-run cell 3 then cell 4.
2. Re-run cell 5.
3. Confirm KPI values and `example_seed_for_local_shapes` can change between runs.

## 3. Expected Output (Cell-by-Cell)

Numeric values can vary when `halftime.seed` is `null`. Validate the fixed text anchors below.

### Cell 1
- Purpose: title/context.
- Pass if header includes: `Phase 1.2: Spectator Flow Agent (Local, No MQTT)`.

### Cell 2
- Purpose: imports.
- Pass if there is no output and no import error.

### Cell 3
- Purpose: load config and print local run metadata.
- Pass if output contains:
  - `Loaded halftime parameters from config.yaml (Phase 1.2 local mode):`
  - `run_id: a4-local-...`
  - `seed_mode: random each run (seed=null)` (or fixed seed mode)
  - keys including `spectator_count`, `halftime_duration_s`, `women_ratio`.

### Cell 4
- Purpose: run local simulation and print KPIs.
- Pass if output contains:
  - `Running local simulation from config...`
  - `Simulation complete:`
  - `=== Key Performance Indicators (KPIs) ===`
  - `Max Queue Length:`
  - `Average Wait Time (overall):`
  - `Missed Kickoff Count:`
  - `Total Served Tasks:`

### Cell 5
- Purpose: build in-memory local movement/task snapshots.
- Pass if output contains:
  - `Local data structures created (no MQTT publishing):`
  - `movement_snapshot keys: ['schema_version', 'run_id', 'timestamp_s', 'spectators']`
  - `task_events count:`
  - `naming convention: zone_1 / zone_2`

### Cell 6
- Purpose: print samples and validate shape.
- Pass if output contains:
  - `First 3 movement records:`
  - `First 3 task records:`
  - `Shape checks:`
  - `movement shape valid: True`
  - `task shape valid: True`

### Cell 7
- Purpose: print queue summary and local completion.
- Pass if output contains:
  - `=== Queue Evolution Summary ===`
  - `=== Phase 1.2 Local Agent Complete ===`
  - `No MQTT connection was created. All movement/task outputs stayed in notebook memory.`

## 4. MQTT Topics (Phase 1.2)

Not applicable in this phase.

- Published topics: none
- Subscribed topics: none
- Message handlers: none
- MQTT schema contracts: none

If MQTT connection or publish output appears, the notebook is not in the intended Phase 1.2 state.

## 5. Debugging Guidance

### Common failures
- `Missing halftime section in config.yaml`
  - Ensure `halftime:` exists and is valid YAML.
- `ModuleNotFoundError: simulated_city`
  - Run cell 2 first and confirm notebook executes from the repository context.
- Shape check shows `False`
  - Verify movement rows include `spectator_id`, `state`, `target`, `zone`.
  - Verify task rows include `spectator_id`, `task`, `task_state`, `zone`.

### Local inspection tips
- Re-run cells 3 to 6 in order.
- Temporarily print full structures in cell 5:
  - `print(movement_snapshot)`
  - `print(task_events[:5])`

## 6. Verification Commands

Run from repository root:

```bash
python scripts/verify_setup.py
python scripts/validate_structure.py
python -m pytest tests/test_phase1_core.py
python -m pytest
```

## 7. Current Validation Status

Latest run results for this implementation:
- `python scripts/verify_setup.py`: passed
- `python scripts/validate_structure.py`: warnings only (expected for no-MQTT Phase 1.2 notebook)
- `python -m pytest tests/test_phase1_core.py`: passed
- `python -m pytest`: passed
