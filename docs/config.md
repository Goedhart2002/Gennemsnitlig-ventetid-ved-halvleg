# Configuration (`simulated_city.config`)

Phase 2 adds typed halftime configuration for the Section A4 queue simulation.

## What `load_config()` returns

`simulated_city.config.load_config()` now returns an `AppConfig` object with:

- `mqtt`: primary MQTT config
- `mqtt_configs`: all active MQTT profiles
- `simulation`: optional legacy template simulation config
- `halftime`: optional typed `HalftimeSimulationConfig`
- `halftime_map`: optional typed `HalftimeMapConfig`

## New halftime schema in `config.yaml`

Use this top-level key:

```yaml
halftime:
  # Use null for a new random run each time.
  # Set a number only when you want reproducible results.
  seed: null

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
    women_ratio: 0.30
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
- `behavior.women_ratio` is within `0..1`
- `capacity.spectator_count > 0`
- Facility counts are `>= 0`
- Service ranges satisfy `min <= max`
- Walking mode is inside `[walking_time_min_s, walking_time_max_s]`
- Blocking speed factor is in `(0, 1]`
- KPI percentiles are all within `1..100`
- Map coordinates stay inside valid longitude/latitude ranges
- `halftime_map.seat_area_bbox` must be a valid `[min_lng, min_lat, max_lng, max_lat]` box
- `halftime_map.publish_interval_s > 0`
- `halftime_map.max_points_per_message > 0`
- Canonical movement zone names must be `zone_1` and `zone_2`
- Legacy aliases must map `zone_a -> zone_1` and `zone_b -> zone_2`

If values are invalid, `load_config()` raises `ValueError` with a beginner-friendly message.

## Movement-map schema (`halftime_map`)

Use this top-level key for movement dashboard/map phases:

```yaml
halftime_map:
  center_lng: 12.5683
  center_lat: 55.6761
  zoom: 17

  seat_area_bbox: [12.5679, 55.6759, 12.5687, 55.6766]

  zone_1_toilet_w: [12.5678, 55.6762]
  zone_1_toilet_m: [12.5679, 55.67622]
  zone_1_cafe: [12.5680, 55.67618]
  zone_2_toilet_w: [12.5689, 55.6760]
  zone_2_toilet_m: [12.5690, 55.67602]
  zone_2_cafe: [12.5691, 55.67598]
  shared_urinal: [12.5685, 55.6756]

  publish_interval_s: 1
  max_points_per_message: 1000

  zone_naming:
    canonical_service_zones: [zone_1, zone_2]
    legacy_zone_aliases:
      zone_a: zone_1
      zone_b: zone_2
```

## Use in simulation code

```python
from simulated_city.config import load_config
from simulated_city.simulation_core import simulate_halftime_from_app_config

app_config = load_config()
result = simulate_halftime_from_app_config(app_config)
```

The simulation helper reads `app_config.halftime` and maps values to `simulate_halftime(...)` automatically.
