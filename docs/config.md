# Configuration (`simulated_city.config`)

Phase 2 adds typed halftime configuration for the Section A4 queue simulation.

## What `load_config()` returns

`simulated_city.config.load_config()` now returns an `AppConfig` object with:

- `mqtt`: primary MQTT config
- `mqtt_configs`: all active MQTT profiles
- `simulation`: optional legacy template simulation config
- `halftime`: optional typed `HalftimeSimulationConfig`

## New halftime schema in `config.yaml`

Use this top-level key:

```yaml
halftime:
  seed: 42

  capacity:
    spectator_count: 1000
    toilet_servers: 15
    cafe_servers: 10
    shared_urinal_total: 16

  timing:
    halftime_duration_s: 900
    inter_facility_walk_s: 30
    walking_time_min_s: 30
    walking_time_mode_s: 120
    walking_time_max_s: 300
    toilet_service_s: {min: 60, max: 180}
    cafe_service_s: {min: 30, max: 60}
    urinal_service_s: {min: 20, max: 45}

  behavior:
    seat_leave_rate: 0.70
    queue_abandon_threshold_s: 240
    queue_switch_threshold_people: 15
    missed_kickoff_risk_window_s: 120

  blocking:
    queue_people_per_line_threshold: 15
    lines_considered: 8
    walking_speed_factor_when_blocked: 0.6

  kpi:
    percentiles: [1, 5, 10, 25, 50, 75, 90, 95, 99, 100]
```

## Validation rules

The typed dataclasses in `src/simulated_city/config_models.py` validate the following:

- `behavior.seat_leave_rate` is within `0..1`
- `capacity.spectator_count > 0`
- Facility counts are `>= 0`
- Service ranges satisfy `min <= max`
- Walking mode is inside `[walking_time_min_s, walking_time_max_s]`
- Blocking speed factor is in `(0, 1]`
- KPI percentiles are all within `1..100`

If values are invalid, `load_config()` raises `ValueError` with a beginner-friendly message.

## Use in simulation code

```python
from simulated_city.config import load_config
from simulated_city.simulation_core import simulate_halftime_from_app_config

app_config = load_config()
result = simulate_halftime_from_app_config(app_config)
```

The simulation helper reads `app_config.halftime` and maps values to `simulate_halftime(...)` automatically.
