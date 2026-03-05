# Phase 2.2 Runtime Guide (Configuration + `halftime_map` Integration)

This guide validates Phase 2.2 only: typed loading of simulation settings and movement-map settings from `config.yaml`.

## Quick Pass Criteria

Phase 2.2 is successful if all are true:
- `load_config()` returns `AppConfig` with `halftime_map` populated.
- `halftime_map.zone_naming.canonical_service_zones == ('zone_1', 'zone_2')`.
- `halftime_map.zone_naming.legacy_zone_aliases == {'zone_a': 'zone_1', 'zone_b': 'zone_2'}`.
- Phase 2.2 tests pass.

## 1. What Was Created

### Files updated
- `src/simulated_city/config_models.py`
  - Added typed map config models:
    - `MapPointConfig`
    - `BboxConfig`
    - `ZoneNamingConfig`
    - `HalftimeMapConfig`
- `src/simulated_city/config.py`
  - Added `AppConfig.halftime_map`
  - Added parser support for top-level `halftime_map` section
  - Added explicit parsing helpers for map points and bbox
- `config.yaml`
  - Added top-level `halftime_map` defaults and zone naming compatibility block
- `tests/test_phase2_config_integration.py`
  - Added parsing and validation tests for `halftime_map`
- `tests/test_config.py`
  - Added general config tests for `halftime_map` and optional behavior
- `docs/config.md`
  - Added schema and validation documentation for `halftime_map`

### Notebooks/scripts created
- None in this phase.
- Existing notebook used for manual validation: `notebooks/agent_spectator_flow.ipynb`.

### Configuration entries added (`config.yaml`)
Added `halftime_map` with:
- map center: `center_lng`, `center_lat`, `zoom`
- layout geometry: `seat_area_bbox`
- facility anchors: `zone_1_*`, `zone_2_*`, `shared_urinal`
- stream limits: `publish_interval_s`, `max_points_per_message`
- naming policy:
  - `canonical_service_zones: [zone_1, zone_2]`
  - `legacy_zone_aliases: {zone_a: zone_1, zone_b: zone_2}`

## 2. How to Run

### Workflow A: Notebook validation
1. Start JupyterLab:
   ```bash
   python -m jupyterlab
   ```
2. Open `notebooks/agent_spectator_flow.ipynb`.
3. Run cells 1 to 3.
4. Add one temporary code cell and run:
   ```python
   print(app_config.halftime_map)
   print(app_config.halftime_map.zone_naming.canonical_service_zones)
   print(app_config.halftime_map.zone_naming.legacy_zone_aliases)
   ```
5. Pass if you observe:
   - a `HalftimeMapConfig(...)` object is printed,
   - canonical names are `('zone_1', 'zone_2')`,
   - legacy aliases map `zone_a` to `zone_1` and `zone_b` to `zone_2`.

### Workflow B: Validate config-driven change
1. Edit `config.yaml` and change one map value, for example:
   - `halftime_map.publish_interval_s: 1` -> `2`
2. Re-run notebook cell 3 and the temporary check cell.
3. Pass if printed config reflects the new value (`publish_interval_s=2`).

## 3. Expected Output

### Notebook cell 3 (existing)
- **Purpose:** Load typed app config and print halftime simulation kwargs.
- **Expected exact text anchor:**
  - `Loaded halftime parameters from config.yaml (Phase 1.2 local mode):`
- **Success condition:** no error while loading config.
- **If different:**
  - errors about mapping/type indicate malformed YAML.

### Temporary check cell (added in workflow)
- **Purpose:** Confirm `halftime_map` typed parsing.
- **Expected exact output fragments:**
  - `HalftimeMapConfig(`
  - `canonical_service_zones=('zone_1', 'zone_2')`
  - `legacy_zone_aliases={'zone_a': 'zone_1', 'zone_b': 'zone_2'}`
- **Success condition:** all three fragments appear.
- **Failure examples:**
  - `None` for `app_config.halftime_map` means section missing or not loaded.
  - `ValueError` mentioning `canonical_service_zones` means invalid zone naming policy.

### Optional strict check snippet
Use this snippet for a hard pass/fail assertion:

```python
assert app_config.halftime_map is not None
assert app_config.halftime_map.zone_naming.canonical_service_zones == ("zone_1", "zone_2")
assert app_config.halftime_map.zone_naming.legacy_zone_aliases == {
    "zone_a": "zone_1",
    "zone_b": "zone_2",
}
print("Phase 2.2 map config validation passed")
```

## 4. MQTT Topics (if applicable)

Not applicable in Phase 2.2.

- Published topics: none
- Subscribed topics: none
- Message schemas: none in this phase

Phase 2.2 only adds typed configuration integration. MQTT behavior starts in later phases.

## 5. Debugging Guidance

### Common errors and fixes
- **`Config key 'halftime_map' must be a mapping`**
  - Ensure `halftime_map:` is a YAML object (not a list/string).
- **`Config key 'halftime_map.seat_area_bbox' must be a [min_lng, min_lat, max_lng, max_lat] list`**
  - Ensure list has exactly 4 numeric values in this order.
- **`halftime_map.publish_interval_s must be > 0`**
  - Set `publish_interval_s` to a positive integer.
- **`halftime_map.max_points_per_message must be > 0`**
  - Set to a positive integer (for example `1000`).
- **`halftime_map.canonical_service_zones must be ['zone_1', 'zone_2']`**
  - Keep canonical names exactly as specified.

### Verbose inspection
Use a quick local snippet:
```python
from simulated_city.config import load_config
cfg = load_config()
print(cfg.halftime_map)
```

### MQTT message flow checks
- Not applicable in this phase.

## 6. Verification Commands

Run from repository root:

```bash
python scripts/verify_setup.py
python scripts/validate_structure.py
python -m pytest tests/test_phase2_config_integration.py tests/test_config.py
python -m pytest
```

## 7. Current Validation Status

Latest run status for this implementation:
- `python scripts/verify_setup.py`: passed
- `python scripts/validate_structure.py`: warnings only (non-blocking)
- `python -m pytest tests/test_phase2_config_integration.py tests/test_config.py`: passed
- `python -m pytest`: passed
