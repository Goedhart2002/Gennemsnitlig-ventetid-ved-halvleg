from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import yaml

from simulated_city.config_models import (
    BboxConfig,
    HalftimeBehaviorConfig,
    HalftimeMapConfig,
    HalftimeBlockingConfig,
    HalftimeCapacityConfig,
    HalftimeKpiConfig,
    HalftimeSimulationConfig,
    HalftimeTimingConfig,
    MapPointConfig,
    ServiceDistributionConfig,
    ZoneNamingConfig,
)


@dataclass(frozen=True, slots=True)
class MqttConfig:
    host: str
    port: int
    tls: bool
    username: str | None
    password: str | None = field(repr=False)
    client_id_prefix: str
    keepalive_s: int
    base_topic: str


@dataclass(frozen=True, slots=True)
class AppConfig:
    mqtt: MqttConfig  # Primary (first active) MQTT broker
    mqtt_configs: dict[str, MqttConfig] = field(default_factory=dict)  # All active profiles
    simulation: "SimulationConfig | None" = None
    halftime: HalftimeSimulationConfig | None = None
    halftime_map: HalftimeMapConfig | None = None


@dataclass(frozen=True, slots=True)
class SimulationLocationConfig:
    location_id: str
    lat: float
    lon: float


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """Configuration for the rubbish-bin simulation.

    Notes
    - This section is optional; the template can be used without any simulation.
    - We keep the config immutable (frozen dataclasses) so it behaves like a
      simple value object.
    """

    timestep_minutes: int = 15
    arrival_prob: float = 0.25
    bag_fill_delta_pct: int = 2
    status_boundary_pct: int = 10
    # If true, emit a status event on every successful deposit (more frequent).
    # If false, emit only when crossing each N% boundary.
    publish_every_deposit: bool = False
    step_delay_s: float = 0.0
    # Optional: fixed simulation start timestamp (UTC) for deterministic logs.
    # If None, the simulator uses the current wall-clock time.
    start_time: datetime | None = None
    seed: int | None = None
    locations: tuple[SimulationLocationConfig, ...] = ()


def _parse_utc_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        s = value.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
    else:
        raise ValueError("simulation.start_time must be an ISO-8601 datetime string")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    # Load a local .env if present (it is gitignored by default).
    # This makes workshop setup easier while keeping secrets out of git.
    load_dotenv(override=False)

    resolved_path = _resolve_default_config_path(path)
    data = _load_yaml_dict(resolved_path)
    active_profiles = _get_active_profiles(data)
    mqtt_config_dicts = _load_mqtt_configs(data, active_profiles)
    simulation = data.get("simulation")
    halftime = data.get("halftime")
    halftime_map = data.get("halftime_map")

    # Build MqttConfig objects for all active profiles
    mqtt_configs: dict[str, MqttConfig] = {}
    primary_mqtt = None

    for profile_name, mqtt_dict in mqtt_config_dicts.items():
        mqtt_config = _dict_to_mqtt_config(mqtt_dict)
        mqtt_configs[profile_name] = mqtt_config
        if primary_mqtt is None:
            primary_mqtt = mqtt_config

    if primary_mqtt is None:
        raise ValueError("No active MQTT profiles found in config")

    sim_cfg = _parse_simulation_config(simulation)
    halftime_cfg = _parse_halftime_config(halftime)
    halftime_map_cfg = _parse_halftime_map_config(halftime_map)

    return AppConfig(
        mqtt=primary_mqtt,
        mqtt_configs=mqtt_configs,
        simulation=sim_cfg,
        halftime=halftime_cfg,
        halftime_map=halftime_map_cfg,
    )


def _select_mqtt_config(data: dict[str, Any]) -> dict[str, Any]:
    """Return the effective MQTT config mapping.

    Supported YAML shapes:

    1) Legacy (single broker):
       mqtt: {host, port, tls, ...}

    2) Profile-based:
       mqtt:
         profile: local
         profiles:
           local: {host, port, tls, ...}
           other: {...}

    The active profile can also be selected via env var:
    - SIMCITY_MQTT_PROFILE (preferred)
    - MQTT_PROFILE (fallback)
    """

    raw = data.get("mqtt") or {}
    if not isinstance(raw, dict):
        raise ValueError("Config key 'mqtt' must be a mapping")

    profiles = raw.get("profiles")
    if profiles is None:
        return raw
    if not isinstance(profiles, dict):
        raise ValueError("Config key 'mqtt.profiles' must be a mapping")

    env_profile = os.getenv("SIMCITY_MQTT_PROFILE") or os.getenv("MQTT_PROFILE")
    profile_name = env_profile or raw.get("profile") or raw.get("active_profile") or raw.get("default_profile")

    if not profile_name:
        # Sensible default: prefer a profile named 'local' if present.
        profile_name = "local" if "local" in profiles else next(iter(profiles.keys()), None)

    if not profile_name:
        raise ValueError("Config key 'mqtt.profiles' is empty; define at least one profile")

    if profile_name not in profiles:
        available = ", ".join(sorted(str(k) for k in profiles.keys()))
        raise ValueError(f"Unknown MQTT profile '{profile_name}'. Available: {available}")

    selected = profiles.get(profile_name) or {}
    if not isinstance(selected, dict):
        raise ValueError(f"Config key 'mqtt.profiles.{profile_name}' must be a mapping")

    # Merge: common mqtt settings first, then profile overrides.
    common: dict[str, Any] = {
        k: v
        for k, v in raw.items()
        if k not in {"profiles", "profile", "active_profile", "default_profile"}
    }
    return {**common, **selected}


def _get_active_profiles(data: dict[str, Any]) -> list[str]:
    """Return the list of active MQTT profile names.
    
    Supports:
    1) active_profiles: [local, mqtthq]  -> uses multiple profiles
    2) profile: local  -> uses single profile (backward compatible)
    3) profile: [local, mqtthq]  -> also accepts list (flexible)
    
    Can be overridden via env var SIMCITY_MQTT_PROFILES (comma-separated).
    """
    raw = data.get("mqtt") or {}
    if not isinstance(raw, dict):
        raise ValueError("Config key 'mqtt' must be a mapping")

    # Check for env var override (comma-separated)
    env_profiles = os.getenv("SIMCITY_MQTT_PROFILES")
    if env_profiles:
        return [p.strip() for p in env_profiles.split(",") if p.strip()]

    # Check for active_profiles list
    active = raw.get("active_profiles")
    if active is not None:
        if isinstance(active, list):
            return [str(p) for p in active if p]
        else:
            raise ValueError("Config key 'mqtt.active_profiles' must be a list")

    # Check for profile (can be string or list)
    profile = raw.get("profile") or raw.get("default_profile")
    if profile is not None:
        if isinstance(profile, list):
            return [str(p) for p in profile if p]
        else:
            return [str(profile)]
    
    # Final fallback to 'local'
    return ["local"]


def _load_mqtt_configs(data: dict[str, Any], profile_names: list[str]) -> dict[str, dict[str, Any]]:
    """Load MQTT config dicts for all requested profile names.
    
    Returns a dict mapping profile_name -> mqtt_config_dict.
    If 'local' is requested but no profiles are defined, provides sensible defaults.
    """
    raw = data.get("mqtt") or {}
    if not isinstance(raw, dict):
        raise ValueError("Config key 'mqtt' must be a mapping")

    profiles = raw.get("profiles") or {}
    if not isinstance(profiles, dict):
        raise ValueError("Config key 'mqtt.profiles' must be a mapping")

    result: dict[str, dict[str, Any]] = {}
    common: dict[str, Any] = {
        k: v
        for k, v in raw.items()
        if k not in {"profiles", "profile", "active_profiles", "active_profile", "default_profile"}
    }

    for profile_name in profile_names:
        # Special case: if 'local' is requested but no profiles exist, use defaults
        if profile_name == "local" and not profiles:
            selected = {
                "host": "localhost",
                "port": 1883,
                "tls": False,
            }
        elif profile_name not in profiles:
            available = ", ".join(sorted(str(k) for k in profiles.keys()))
            raise ValueError(f"Unknown MQTT profile '{profile_name}'. Available: {available}")
        else:
            selected = profiles.get(profile_name) or {}
            if not isinstance(selected, dict):
                raise ValueError(f"Config key 'mqtt.profiles.{profile_name}' must be a mapping")

        # Merge common settings with profile-specific overrides
        result[profile_name] = {**common, **selected}

    return result


def _dict_to_mqtt_config(mqtt_dict: dict[str, Any]) -> MqttConfig:
    """Convert a MQTT config dict to an MqttConfig object."""
    host = str(mqtt_dict.get("host") or "localhost")
    port = int(mqtt_dict.get("port") or 1883)
    tls = bool(mqtt_dict.get("tls") or False)

    username_env = mqtt_dict.get("username_env")
    password_env = mqtt_dict.get("password_env")
    username = os.getenv(str(username_env)) if username_env else None
    password = os.getenv(str(password_env)) if password_env else None

    client_id_prefix = str(mqtt_dict.get("client_id_prefix") or "simcity")
    keepalive_s = int(mqtt_dict.get("keepalive_s") or 60)
    base_topic = str(mqtt_dict.get("base_topic") or "simulated-city")

    return MqttConfig(
        host=host,
        port=port,
        tls=tls,
        username=username,
        password=password,
        client_id_prefix=client_id_prefix,
        keepalive_s=keepalive_s,
        base_topic=base_topic,
    )



def _parse_simulation_config(raw: Any) -> SimulationConfig | None:
    """Parse the optional `simulation:` section from config.yaml.

    We keep this tolerant: missing or empty simulation config returns None.
    """

    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("Config key 'simulation' must be a mapping")

    timestep_minutes = int(raw.get("timestep_minutes") or 15)
    arrival_prob = float(raw.get("arrival_prob") or 0.25)
    bag_fill_delta_pct = int(raw.get("bag_fill_delta_pct") or 2)
    status_boundary_pct = int(raw.get("status_boundary_pct") or 10)

    publish_every_deposit = bool(raw.get("publish_every_deposit") or False)

    # Optional wall-clock delay between timesteps (useful for MQTT testing).
    step_delay_raw = raw.get("step_delay_s")
    if step_delay_raw is None:
        step_delay_raw = raw.get("step_delay_seconds")
    step_delay_s = float(step_delay_raw) if step_delay_raw is not None else 0.0

    start_time_raw = raw.get("start_time")
    start_time = _parse_utc_datetime(start_time_raw) if start_time_raw is not None else None

    if "seed" in raw and raw.get("seed") is None:
        seed = None
    else:
        seed = int(raw.get("seed") if raw.get("seed") is not None else 42)

    locations_raw = raw.get("locations") or []
    if not isinstance(locations_raw, list):
        raise ValueError("Config key 'simulation.locations' must be a list")

    locations: list[SimulationLocationConfig] = []
    for item in locations_raw:
        if not isinstance(item, dict):
            raise ValueError("Each item in 'simulation.locations' must be a mapping")

        location_id = str(item.get("id") or item.get("location_id") or "").strip()
        if not location_id:
            raise ValueError("Each simulation location must have an 'id'")

        if "lat" not in item or "lon" not in item:
            raise ValueError(f"Simulation location '{location_id}' must define 'lat' and 'lon'")
        lat = float(item["lat"])
        lon = float(item["lon"])

        locations.append(SimulationLocationConfig(location_id=location_id, lat=lat, lon=lon))

    return SimulationConfig(
        timestep_minutes=timestep_minutes,
        arrival_prob=arrival_prob,
        bag_fill_delta_pct=bag_fill_delta_pct,
        status_boundary_pct=status_boundary_pct,
        publish_every_deposit=publish_every_deposit,
        step_delay_s=step_delay_s,
        start_time=start_time,
        seed=seed,
        locations=tuple(locations),
    )


def _parse_halftime_config(raw: Any) -> HalftimeSimulationConfig | None:
    """Parse typed `halftime:` configuration used by Section A4 agents."""

    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("Config key 'halftime' must be a mapping")

    seed_raw = raw.get("seed")
    seed = int(seed_raw) if seed_raw is not None else None

    capacity_raw = raw.get("capacity") or {}
    if not isinstance(capacity_raw, dict):
        raise ValueError("Config key 'halftime.capacity' must be a mapping")
    capacity = HalftimeCapacityConfig(
        spectator_count=int(capacity_raw.get("spectator_count") if capacity_raw.get("spectator_count") is not None else 1000),
        toilet_servers=int(capacity_raw.get("toilet_servers") if capacity_raw.get("toilet_servers") is not None else 15),
        cafe_servers=int(capacity_raw.get("cafe_servers") if capacity_raw.get("cafe_servers") is not None else 10),
        shared_urinal_total=int(
            capacity_raw.get("shared_urinal_total") if capacity_raw.get("shared_urinal_total") is not None else 16
        ),
    )

    timing_raw = raw.get("timing") or {}
    if not isinstance(timing_raw, dict):
        raise ValueError("Config key 'halftime.timing' must be a mapping")

    toilet_service_raw = timing_raw.get("toilet_service_s") or {}
    cafe_service_raw = timing_raw.get("cafe_service_s") or {}
    urinal_service_raw = timing_raw.get("urinal_service_s") or {}
    if not isinstance(toilet_service_raw, dict):
        raise ValueError("Config key 'halftime.timing.toilet_service_s' must be a mapping")
    if not isinstance(cafe_service_raw, dict):
        raise ValueError("Config key 'halftime.timing.cafe_service_s' must be a mapping")
    if not isinstance(urinal_service_raw, dict):
        raise ValueError("Config key 'halftime.timing.urinal_service_s' must be a mapping")

    timing = HalftimeTimingConfig(
        halftime_duration_s=int(timing_raw.get("halftime_duration_s") if timing_raw.get("halftime_duration_s") is not None else 900),
        inter_facility_walk_s=int(
            timing_raw.get("inter_facility_walk_s") if timing_raw.get("inter_facility_walk_s") is not None else 30
        ),
        walking_time_min_s=int(timing_raw.get("walking_time_min_s") if timing_raw.get("walking_time_min_s") is not None else 30),
        walking_time_mode_s=int(timing_raw.get("walking_time_mode_s") if timing_raw.get("walking_time_mode_s") is not None else 120),
        walking_time_max_s=int(timing_raw.get("walking_time_max_s") if timing_raw.get("walking_time_max_s") is not None else 300),
        toilet_service_s=ServiceDistributionConfig(
            min_s=int(toilet_service_raw.get("min") if toilet_service_raw.get("min") is not None else 60),
            max_s=int(toilet_service_raw.get("max") if toilet_service_raw.get("max") is not None else 180),
        ),
        cafe_service_s=ServiceDistributionConfig(
            min_s=int(cafe_service_raw.get("min") if cafe_service_raw.get("min") is not None else 30),
            max_s=int(cafe_service_raw.get("max") if cafe_service_raw.get("max") is not None else 60),
        ),
        urinal_service_s=ServiceDistributionConfig(
            min_s=int(urinal_service_raw.get("min") if urinal_service_raw.get("min") is not None else 20),
            max_s=int(urinal_service_raw.get("max") if urinal_service_raw.get("max") is not None else 45),
        ),
    )

    behavior_raw = raw.get("behavior") or {}
    if not isinstance(behavior_raw, dict):
        raise ValueError("Config key 'halftime.behavior' must be a mapping")
    behavior = HalftimeBehaviorConfig(
        seat_leave_rate=float(
            behavior_raw.get("seat_leave_rate") if behavior_raw.get("seat_leave_rate") is not None else 0.70
        ),
        women_ratio=float(behavior_raw.get("women_ratio") if behavior_raw.get("women_ratio") is not None else 0.30),
        queue_abandon_threshold_s=int(
            behavior_raw.get("queue_abandon_threshold_s")
            if behavior_raw.get("queue_abandon_threshold_s") is not None
            else 240
        ),
        queue_switch_threshold_people=int(
            behavior_raw.get("queue_switch_threshold_people")
            if behavior_raw.get("queue_switch_threshold_people") is not None
            else 15
        ),
        missed_kickoff_risk_window_s=int(
            behavior_raw.get("missed_kickoff_risk_window_s")
            if behavior_raw.get("missed_kickoff_risk_window_s") is not None
            else 120
        ),
    )

    blocking_raw = raw.get("blocking") or {}
    if not isinstance(blocking_raw, dict):
        raise ValueError("Config key 'halftime.blocking' must be a mapping")
    blocking = HalftimeBlockingConfig(
        queue_people_per_line_threshold=int(
            blocking_raw.get("queue_people_per_line_threshold")
            if blocking_raw.get("queue_people_per_line_threshold") is not None
            else 15
        ),
        lines_considered=int(blocking_raw.get("lines_considered") if blocking_raw.get("lines_considered") is not None else 8),
        walking_speed_factor_when_blocked=float(
            blocking_raw.get("walking_speed_factor_when_blocked")
            if blocking_raw.get("walking_speed_factor_when_blocked") is not None
            else 0.6
        ),
    )

    kpi_raw = raw.get("kpi") or {}
    if not isinstance(kpi_raw, dict):
        raise ValueError("Config key 'halftime.kpi' must be a mapping")
    percentiles_raw = kpi_raw.get("percentiles")
    if percentiles_raw is None:
        percentiles_raw = [1, 5, 10, 25, 50, 75, 90, 95, 99, 100]
    if not isinstance(percentiles_raw, list):
        raise ValueError("Config key 'halftime.kpi.percentiles' must be a list")
    percentiles = tuple(int(value) for value in percentiles_raw)
    kpi = HalftimeKpiConfig(percentiles=percentiles)

    return HalftimeSimulationConfig(
        seed=seed,
        capacity=capacity,
        timing=timing,
        behavior=behavior,
        blocking=blocking,
        kpi=kpi,
    )


def _parse_halftime_map_point(raw: Any, key_name: str) -> MapPointConfig:
    if not isinstance(raw, list) or len(raw) != 2:
        raise ValueError(f"Config key '{key_name}' must be a [lng, lat] list")
    return MapPointConfig(lng=float(raw[0]), lat=float(raw[1]))


def _parse_halftime_map_bbox(raw: Any) -> BboxConfig:
    if not isinstance(raw, list) or len(raw) != 4:
        raise ValueError("Config key 'halftime_map.seat_area_bbox' must be a [min_lng, min_lat, max_lng, max_lat] list")
    return BboxConfig(
        min_lng=float(raw[0]),
        min_lat=float(raw[1]),
        max_lng=float(raw[2]),
        max_lat=float(raw[3]),
    )


def _parse_halftime_map_config(raw: Any) -> HalftimeMapConfig | None:
    """Parse typed `halftime_map:` configuration for movement-map phases."""

    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("Config key 'halftime_map' must be a mapping")

    center_lng = float(raw.get("center_lng") if raw.get("center_lng") is not None else 12.5683)
    center_lat = float(raw.get("center_lat") if raw.get("center_lat") is not None else 55.6761)
    center = MapPointConfig(lng=center_lng, lat=center_lat)

    seat_area_bbox = _parse_halftime_map_bbox(
        raw.get("seat_area_bbox") if raw.get("seat_area_bbox") is not None else [12.5679, 55.6759, 12.5687, 55.6766]
    )

    zone_naming_raw = raw.get("zone_naming") or {}
    if not isinstance(zone_naming_raw, dict):
        raise ValueError("Config key 'halftime_map.zone_naming' must be a mapping")

    canonical_raw = zone_naming_raw.get("canonical_service_zones")
    if canonical_raw is None:
        canonical_raw = ["zone_1", "zone_2"]
    if not isinstance(canonical_raw, list) or len(canonical_raw) != 2:
        raise ValueError("Config key 'halftime_map.zone_naming.canonical_service_zones' must be a two-item list")

    aliases_raw = zone_naming_raw.get("legacy_zone_aliases")
    if aliases_raw is None:
        aliases_raw = {"zone_a": "zone_1", "zone_b": "zone_2"}
    if not isinstance(aliases_raw, dict):
        raise ValueError("Config key 'halftime_map.zone_naming.legacy_zone_aliases' must be a mapping")

    zone_naming = ZoneNamingConfig(
        canonical_service_zones=(str(canonical_raw[0]), str(canonical_raw[1])),
        legacy_zone_aliases={str(k): str(v) for k, v in aliases_raw.items()},
    )

    return HalftimeMapConfig(
        center=center,
        zoom=int(raw.get("zoom") if raw.get("zoom") is not None else 17),
        seat_area_bbox=seat_area_bbox,
        zone_1_toilet_w=_parse_halftime_map_point(
            raw.get("zone_1_toilet_w") if raw.get("zone_1_toilet_w") is not None else [12.5678, 55.6762],
            "halftime_map.zone_1_toilet_w",
        ),
        zone_1_toilet_m=_parse_halftime_map_point(
            raw.get("zone_1_toilet_m") if raw.get("zone_1_toilet_m") is not None else [12.5679, 55.67622],
            "halftime_map.zone_1_toilet_m",
        ),
        zone_1_cafe=_parse_halftime_map_point(
            raw.get("zone_1_cafe") if raw.get("zone_1_cafe") is not None else [12.5680, 55.67618],
            "halftime_map.zone_1_cafe",
        ),
        zone_2_toilet_w=_parse_halftime_map_point(
            raw.get("zone_2_toilet_w") if raw.get("zone_2_toilet_w") is not None else [12.5689, 55.6760],
            "halftime_map.zone_2_toilet_w",
        ),
        zone_2_toilet_m=_parse_halftime_map_point(
            raw.get("zone_2_toilet_m") if raw.get("zone_2_toilet_m") is not None else [12.5690, 55.67602],
            "halftime_map.zone_2_toilet_m",
        ),
        zone_2_cafe=_parse_halftime_map_point(
            raw.get("zone_2_cafe") if raw.get("zone_2_cafe") is not None else [12.5691, 55.67598],
            "halftime_map.zone_2_cafe",
        ),
        shared_urinal=_parse_halftime_map_point(
            raw.get("shared_urinal") if raw.get("shared_urinal") is not None else [12.5685, 55.6756],
            "halftime_map.shared_urinal",
        ),
        publish_interval_s=int(raw.get("publish_interval_s") if raw.get("publish_interval_s") is not None else 1),
        max_points_per_message=int(
            raw.get("max_points_per_message") if raw.get("max_points_per_message") is not None else 1000
        ),
        zone_naming=zone_naming,
    )


def _load_yaml_dict(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}

    content = p.read_text(encoding="utf-8")
    loaded = yaml.safe_load(content)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Config file {p} must contain a YAML mapping at top level")
    return loaded


def _resolve_default_config_path(path: str | Path) -> Path:
    """Resolve a config path in a notebook-friendly way.

    When `load_config()` is called with the default relative filename
    (`config.yaml`), users often run code from a subdirectory (e.g. `notebooks/`).
    In that case we search parent directories so `config.yaml` at repo root is
    still discovered.

    If a custom path is provided (including nested relative paths), we do not
    change it.
    """

    p = Path(path)

    # Absolute paths, or already-existing relative paths, are used as-is.
    if p.is_absolute() or p.exists():
        return p

    # Only apply parent-search for bare filenames like "config.yaml".
    if p.parent != Path("."):
        return p

    def search_upwards(start: Path) -> Path | None:
        for parent in [start, *start.parents]:
            candidate = parent / p.name
            if candidate.exists():
                return candidate
        return None

    found = search_upwards(Path.cwd())
    if found is not None:
        return found

    # If cwd isn't inside the project (common in some notebook setups), also
    # search relative to this installed package location.
    found = search_upwards(Path(__file__).resolve().parent)
    if found is not None:
        return found

    return p