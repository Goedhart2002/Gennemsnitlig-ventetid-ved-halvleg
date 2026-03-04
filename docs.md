# `notebooks/kpi_bar_charts.ipynb` – What it does and how it works

This notebook runs the Section A4 halftime simulation and visualizes key KPIs as two bar charts.

## Purpose

The notebook gives you a quick, visual check of simulation outcomes for one run:

1. **Average wait-time KPIs** (seconds)
2. **People and service-use KPIs** (counts)

It is intended for fast reruns while adjusting `config.yaml`.

## How it works (cell by cell)

### Cell 1 (Markdown)
Explains assumptions and run order:
- If `halftime.seed: null`, each run should use a new random sequence.
- Section A4 uses `halftime.behavior.women_ratio: 0.30`.
- Recommended rerun order: **Cell 2 → Cell 3 → Cell 4**.

### Cell 2 (Simulation run)
This is the main execution cell.

It does the following:
- Imports and reloads modules from `src/simulated_city`:
  - `config_models`
  - `config`
  - `simulation_core`
- Finds `config.yaml` in current folder or parent folder.
- Loads config with `simulated_city.config.load_config()`.
- Builds simulation arguments via `app_config.halftime.to_simulation_core_kwargs()`.
- Handles randomness:
  - If configured seed is `null`, it generates a fresh run seed.
  - It avoids repeating the previous run seed in the same notebook session.
- Prints:
  - Config path
  - Config seed and run seed
  - `women_ratio`
  - A run signature (`average_wait`, `missed_kickoff`, `total_served_tasks`)
- Runs `simulate_halftime(**params)` and stores the result in `result`.

### Cell 3 (Prepare chart values)
Builds two dictionaries from `result`:
- `avg_time_values` for wait-time metrics
- `count_values` for people/service counts

These are the data sources for the charts.

### Cell 4 (Render charts)
Creates HTML/CSS-based bar charts and displays them with:
- `IPython.display.HTML`
- `display(HTML(page))`

It renders two side-by-side panels:
- **Average Time KPIs**
- **People & Service Use KPIs**

## Why numbers change between runs

Numbers change when:
- `halftime.seed` is `null` in `config.yaml`, and
- You rerun **Cell 2** (not only Cells 3/4).

If seed is fixed (for example `42`), results stay identical by design.

## Typical workflow

1. Edit `config.yaml` (capacity, timings, behavior rates, seed).
2. Run **Cell 2** (new simulation run).
3. Run **Cell 3** (refresh chart values).
4. Run **Cell 4** (render updated charts).

## Troubleshooting

If results do not change:
- Confirm `halftime.seed: null` in `config.yaml`.
- Confirm Cell 2 prints a newly generated run seed.
- Rerun in correct order: Cell 2 → Cell 3 → Cell 4.
- Restart kernel and run all cells again if stale state is suspected.
