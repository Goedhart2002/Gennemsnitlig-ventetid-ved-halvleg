# Simulated City (Workshop Template)

This template is for a workshop where students learn **agent-based programming in Python** by building pieces of a simple "simulated city"—a lightweight starting point for an **urban digital twin**.

The goal is to keep the code:

- Small enough to read in one sitting
- Modular enough to extend (agents, places, sensors, movement rules)
- Practical for notebook-driven exploration



## Repo overview

- `src/simulated_city/`: the library students import
- `notebooks/`: Section A4 agent notebooks
  - `agent_spectator_flow.ipynb` — publishes spectator halftime events
  - `agent_facility_manager.ipynb` — consumes spectator events and publishes queue state
  - `agent_congestion.ipynb` — consumes queue state and publishes congestion state
  - `agent_metrics.ipynb` — consumes spectator events and publishes KPI metrics
  - `dashboard_a4.ipynb` — consumes queue/KPI/congestion and renders anymap-ts dashboard
- `docs/`: workshop handouts and exercises
- `tests/`: small sanity checks

## Library modules

- `simulated_city.config`: load settings from `config.yaml` + optional `.env`
- `simulated_city.mqtt`: build topics, connect, and publish MQTT messages
- `simulated_city.geo` (optional): CRS transforms for real-world coordinates
  - Enable with: `python -m pip install -e ".[geo]"`
  - Includes beginner-friendly helpers like `wgs2utm(...)` / `utm2wgs(...)`


## Docs index

Module docs:

- `docs/config.md` — `simulated_city.config`
- `docs/mqtt.md` — `simulated_city.mqtt`
- `docs/geo.md` — `simulated_city.geo` (optional)
- `docs/__init__.md` — top-level package API (`simulated_city`)
- `docs/__main__.md` — CLI smoke (`python -m simulated_city`)

Developer docs:

- `docs/testing.md` — test suite overview and how to run tests

Workshop docs:

- `docs/setup.md` — environment setup + optional extras
- `docs/demos.md` — script demos (same ideas as the notebook)
- `docs/maplibre_anymap.md` — mapping in notebooks (anymap-ts / MapLibre)
- `docs/exercises.md` — student exercises (build the simulation)

## Recommended run order (for reproducible behavior)

Run notebook agents in this order:

1. `notebooks/agent_facility_manager.ipynb`
2. `notebooks/agent_congestion.ipynb`
3. `notebooks/agent_metrics.ipynb`
4. `notebooks/dashboard_a4.ipynb`
5. `notebooks/agent_spectator_flow.ipynb`

Reason: `agent_spectator_flow.ipynb` is the main publisher. Starting it last ensures subscriber notebooks and dashboard listeners are already active.

## KPI interpretation for instructor review

Use KPI output to evaluate halftime flow quality without changing simulation logic:

- `average_wait_s`: overall queue pressure indicator.
- `wait_percentiles_s` (`P01`..`P100`): distribution shape and tail risk.
- `missed_kickoff_count`: rule-based outcome for spectators exceeding halftime time budget.

A practical review pattern is:

- Compare `P50` vs `P95` and `P99` to see if long waits are concentrated in a minority.
- Check whether `missed_kickoff_count` is non-zero under congestion-heavy runs.
- Cross-check with dashboard queue trend points to confirm timing and spikes.

## Section A4 zone model

The current halftime setup uses two zones simultaneously:

- Zone 1: 6 men's toilets, 6 women's toilets, café with 8 lines
- Zone 2: 6 men's toilets, 6 women's toilets, café with 8 lines
- Shared men's urinal between zones with capacity 16

Spectator demand is distributed across both zones at runtime so both zones can be active in the same halftime window.
By default, only about 70% of spectators leave their seats during halftime (`behavior.seat_leave_rate: 0.70`), while the rest remain seated.
