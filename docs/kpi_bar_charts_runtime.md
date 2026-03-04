# KPI Bar Charts Runtime Guide (Section A4)

This guide documents how `notebooks/kpi_bar_charts.ipynb` runs the halftime simulation and renders KPI bar charts.

## 1. What Was Created

### Notebooks and Scripts
- Updated notebook: `notebooks/kpi_bar_charts.ipynb`
- Runtime doc: `docs/kpi_bar_charts_runtime.md`

### Library Modules in `src/simulated_city/`
The notebook uses existing modules:
- `config.py`
  - `load_config(...)`
- `config_models.py`
  - typed halftime config models
- `simulation_core.py`
  - `simulate_halftime(...)`

### Configuration Changes (`config.yaml`)
The notebook depends on `halftime.*` values in `config.yaml`, especially:
- `halftime.seed`
- `halftime.capacity.*`
- `halftime.timing.*`
- `halftime.behavior.women_ratio`

## 2. How to Run

### Workflow A: Run KPI notebook
1. Start JupyterLab from repository root:
   - `.venv/bin/python -m jupyterlab`
2. Open notebook:
   - `notebooks/kpi_bar_charts.ipynb`
3. Run cells 1-4 in order.

Expected behavior by cell:
- Cell 1: notebook purpose and randomness assumptions.
- Cell 2: loads config, generates run seed (if config seed is `null`), runs simulation.
- Cell 3: prepares metric dictionaries for chart rendering.
- Cell 4: renders two bar-chart panels using HTML/CSS.

### Workflow B: Re-run for a new random result
1. Keep `halftime.seed: null` in `config.yaml`.
2. Re-run Cell 2.
3. Re-run Cell 3.
4. Re-run Cell 4.

This produces a new random run each time and updates chart values.

## 3. Expected Output

### Cell 2 (Simulation Run)
Purpose: load config, run simulation, and print run metadata.

Expected lines include:
- `Using config file: .../config.yaml`
- `halftime.seed (config): null` (if random mode)
- `halftime.seed (run): <generated int> (generated)`
- `halftime.behavior.women_ratio: 0.30`
- `run.signature: <avg_wait>-<missed>-<served>`
- `Simulation complete.`

If different:
- If seed is fixed (for example `42`), numbers are reproducible.
- If path is wrong, check notebook working directory and config location.

### Cell 3 (Chart Data Build)
Purpose: map simulation results to chart-value dictionaries.

Expected objects:
- `avg_time_values`
- `count_values`

### Cell 4 (Chart Render)
Purpose: render two KPI chart panels.

Expected panels:
- `Average Time KPIs`
- `People & Service Use KPIs`

If values do not change:
- You likely reran only Cell 4.
- Re-run in order: Cell 2 → Cell 3 → Cell 4.

## 4. MQTT Topics

This notebook does not publish or subscribe to MQTT topics.

- Topics published: none
- Topics subscribed: none
- Message schemas: not applicable

## 5. Debugging Guidance

### Common issues
- Same numbers every run:
  - Ensure `halftime.seed: null` in `config.yaml`.
  - Re-run Cell 2 before Cells 3/4.
- Wrong config loaded:
  - Verify printed `Using config file: ...` path in Cell 2 output.
- Stale notebook imports:
  - Cell 2 reloads modules; if needed restart kernel and run all cells.

### Quick checks
- Confirm `run.signature` changes across repeated Cell 2 runs.
- Confirm `halftime.seed (run)` changes each random run.

## 6. Verification Commands

Run from repository root:

```bash
python scripts/verify_setup.py
python scripts/validate_structure.py
python -m pytest
```
