from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class SimulationCoreKwargs(TypedDict):
    seed: int | None
    spectator_count: int
    halftime_duration_s: int
    toilet_servers: int
    cafe_servers: int
    toilet_service_min_s: int
    toilet_service_max_s: int
    cafe_service_min_s: int
    cafe_service_max_s: int
    urinal_service_min_s: int
    urinal_service_max_s: int
    inter_facility_walk_s: int
    seat_leave_rate: float
    women_ratio: float
    shared_urinal_total: int


@dataclass(frozen=True, slots=True)
class ServiceDistributionConfig:
    """Inclusive min/max service-time range in seconds."""

    min_s: int
    max_s: int

    def __post_init__(self) -> None:
        if self.min_s < 0:
            raise ValueError("Service distribution min_s must be >= 0")
        if self.max_s < self.min_s:
            raise ValueError("Service distribution max_s must be >= min_s")


@dataclass(frozen=True, slots=True)
class HalftimeCapacityConfig:
    """Capacity and facility counts for Section A4 halftime simulation."""

    spectator_count: int
    toilet_servers: int
    cafe_servers: int
    shared_urinal_total: int

    def __post_init__(self) -> None:
        if self.spectator_count <= 0:
            raise ValueError("halftime.capacity.spectator_count must be > 0")
        if self.toilet_servers < 0:
            raise ValueError("halftime.capacity.toilet_servers must be >= 0")
        if self.cafe_servers < 0:
            raise ValueError("halftime.capacity.cafe_servers must be >= 0")
        if self.shared_urinal_total < 0:
            raise ValueError("halftime.capacity.shared_urinal_total must be >= 0")


@dataclass(frozen=True, slots=True)
class HalftimeTimingConfig:
    """Timing and service distributions used by halftime agents."""

    halftime_duration_s: int
    inter_facility_walk_s: int
    walking_time_min_s: int
    walking_time_mode_s: int
    walking_time_max_s: int
    toilet_service_s: ServiceDistributionConfig
    cafe_service_s: ServiceDistributionConfig
    urinal_service_s: ServiceDistributionConfig

    def __post_init__(self) -> None:
        if self.halftime_duration_s <= 0:
            raise ValueError("halftime.timing.halftime_duration_s must be > 0")
        if self.inter_facility_walk_s < 0:
            raise ValueError("halftime.timing.inter_facility_walk_s must be >= 0")
        if self.walking_time_min_s < 0:
            raise ValueError("halftime.timing.walking_time_min_s must be >= 0")
        if self.walking_time_max_s < self.walking_time_min_s:
            raise ValueError("halftime.timing.walking_time_max_s must be >= walking_time_min_s")
        if not (self.walking_time_min_s <= self.walking_time_mode_s <= self.walking_time_max_s):
            raise ValueError(
                "halftime.timing.walking_time_mode_s must be between walking_time_min_s and walking_time_max_s"
            )


@dataclass(frozen=True, slots=True)
class HalftimeBehaviorConfig:
    """Behavior thresholds used by spectator and facility agents."""

    seat_leave_rate: float
    women_ratio: float
    queue_abandon_threshold_s: int
    queue_switch_threshold_people: int
    missed_kickoff_risk_window_s: int

    def __post_init__(self) -> None:
        if not (0.0 <= self.seat_leave_rate <= 1.0):
            raise ValueError("halftime.behavior.seat_leave_rate must be within 0..1")
        if not (0.0 <= self.women_ratio <= 1.0):
            raise ValueError("halftime.behavior.women_ratio must be within 0..1")
        if self.queue_abandon_threshold_s < 0:
            raise ValueError("halftime.behavior.queue_abandon_threshold_s must be >= 0")
        if self.queue_switch_threshold_people < 0:
            raise ValueError("halftime.behavior.queue_switch_threshold_people must be >= 0")
        if self.missed_kickoff_risk_window_s < 0:
            raise ValueError("halftime.behavior.missed_kickoff_risk_window_s must be >= 0")


@dataclass(frozen=True, slots=True)
class HalftimeBlockingConfig:
    """Queue blocking threshold controls for concourse congestion logic."""

    queue_people_per_line_threshold: int
    lines_considered: int
    walking_speed_factor_when_blocked: float

    def __post_init__(self) -> None:
        if self.queue_people_per_line_threshold < 0:
            raise ValueError("halftime.blocking.queue_people_per_line_threshold must be >= 0")
        if self.lines_considered <= 0:
            raise ValueError("halftime.blocking.lines_considered must be > 0")
        if not (0.0 < self.walking_speed_factor_when_blocked <= 1.0):
            raise ValueError("halftime.blocking.walking_speed_factor_when_blocked must be in (0, 1]")


@dataclass(frozen=True, slots=True)
class HalftimeKpiConfig:
    """KPI reporting settings, including required percentile list (1..100)."""

    percentiles: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.percentiles:
            raise ValueError("halftime.kpi.percentiles must not be empty")

        invalid = [value for value in self.percentiles if value < 1 or value > 100]
        if invalid:
            raise ValueError("halftime.kpi.percentiles values must be within 1..100")


@dataclass(frozen=True, slots=True)
class HalftimeSimulationConfig:
    """Typed halftime configuration shared by all later agents."""

    seed: int | None
    capacity: HalftimeCapacityConfig
    timing: HalftimeTimingConfig
    behavior: HalftimeBehaviorConfig
    blocking: HalftimeBlockingConfig
    kpi: HalftimeKpiConfig

    def to_simulation_core_kwargs(self) -> SimulationCoreKwargs:
        """Return kwargs for the current Phase 1/2 simulation core API."""

        return {
            "seed": self.seed,
            "spectator_count": self.capacity.spectator_count,
            "halftime_duration_s": self.timing.halftime_duration_s,
            "toilet_servers": self.capacity.toilet_servers,
            "cafe_servers": self.capacity.cafe_servers,
            "toilet_service_min_s": self.timing.toilet_service_s.min_s,
            "toilet_service_max_s": self.timing.toilet_service_s.max_s,
            "cafe_service_min_s": self.timing.cafe_service_s.min_s,
            "cafe_service_max_s": self.timing.cafe_service_s.max_s,
            "urinal_service_min_s": self.timing.urinal_service_s.min_s,
            "urinal_service_max_s": self.timing.urinal_service_s.max_s,
            "inter_facility_walk_s": self.timing.inter_facility_walk_s,
            "seat_leave_rate": self.behavior.seat_leave_rate,
            "women_ratio": self.behavior.women_ratio,
            "shared_urinal_total": self.capacity.shared_urinal_total,
        }


@dataclass(frozen=True, slots=True)
class MapPointConfig:
    """Longitude/latitude pair used for map anchors."""

    lng: float
    lat: float

    def __post_init__(self) -> None:
        if not (-180.0 <= self.lng <= 180.0):
            raise ValueError("Map point longitude must be within -180..180")
        if not (-90.0 <= self.lat <= 90.0):
            raise ValueError("Map point latitude must be within -90..90")


@dataclass(frozen=True, slots=True)
class BboxConfig:
    """Bounding box in [min_lng, min_lat, max_lng, max_lat] format."""

    min_lng: float
    min_lat: float
    max_lng: float
    max_lat: float

    def __post_init__(self) -> None:
        if not (-180.0 <= self.min_lng <= 180.0 and -180.0 <= self.max_lng <= 180.0):
            raise ValueError("halftime_map.seat_area_bbox longitude values must be within -180..180")
        if not (-90.0 <= self.min_lat <= 90.0 and -90.0 <= self.max_lat <= 90.0):
            raise ValueError("halftime_map.seat_area_bbox latitude values must be within -90..90")
        if self.max_lng <= self.min_lng:
            raise ValueError("halftime_map.seat_area_bbox max_lng must be greater than min_lng")
        if self.max_lat <= self.min_lat:
            raise ValueError("halftime_map.seat_area_bbox max_lat must be greater than min_lat")


@dataclass(frozen=True, slots=True)
class ZoneNamingConfig:
    """Service-zone naming policy for planned movement data.

    Canonical names are `zone_1` and `zone_2`. Legacy aliases keep
    compatibility with older queue/congestion naming (`zone_a`, `zone_b`).
    """

    canonical_service_zones: tuple[str, str]
    legacy_zone_aliases: dict[str, str]

    def __post_init__(self) -> None:
        expected = ("zone_1", "zone_2")
        if self.canonical_service_zones != expected:
            raise ValueError("halftime_map.canonical_service_zones must be ['zone_1', 'zone_2']")

        required_aliases = {"zone_a": "zone_1", "zone_b": "zone_2"}
        for legacy, canonical in required_aliases.items():
            mapped = self.legacy_zone_aliases.get(legacy)
            if mapped != canonical:
                raise ValueError(
                    f"halftime_map.legacy_zone_aliases must map '{legacy}' to '{canonical}'"
                )


@dataclass(frozen=True, slots=True)
class HalftimeMapConfig:
    """Typed config for planned halftime movement-map settings."""

    center: MapPointConfig
    zoom: int
    seat_area_bbox: BboxConfig
    zone_1_toilet_w: MapPointConfig
    zone_1_toilet_m: MapPointConfig
    zone_1_cafe: MapPointConfig
    zone_2_toilet_w: MapPointConfig
    zone_2_toilet_m: MapPointConfig
    zone_2_cafe: MapPointConfig
    shared_urinal: MapPointConfig
    publish_interval_s: int
    max_points_per_message: int
    zone_naming: ZoneNamingConfig

    def __post_init__(self) -> None:
        if self.zoom < 0:
            raise ValueError("halftime_map.zoom must be >= 0")
        if self.publish_interval_s <= 0:
            raise ValueError("halftime_map.publish_interval_s must be > 0")
        if self.max_points_per_message <= 0:
            raise ValueError("halftime_map.max_points_per_message must be > 0")
