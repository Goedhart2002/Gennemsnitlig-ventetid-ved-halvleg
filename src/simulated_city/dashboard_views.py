from __future__ import annotations

"""Data-shape helpers for Phase 5 dashboard notebook."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class QueueTrendPoint:
    timestamp_s: int
    zone_a_toilet: int
    zone_a_cafe: int
    zone_b_toilet: int
    zone_b_cafe: int
    shared_mens_urinal: int


@dataclass(frozen=True, slots=True)
class KpiSnapshot:
    timestamp_s: int
    average_wait_s: float
    wait_percentiles_s: dict[str, float]
    missed_kickoff_count: int
    made_kickoff_count: int
    stayed_seated_count: int
    went_down_count: int
    went_down_made_back_count: int


@dataclass(frozen=True, slots=True)
class CongestionSnapshot:
    timestamp_s: int
    zone_a_blocked: bool
    zone_b_blocked: bool


@dataclass(frozen=True, slots=True)
class MovementPoint:
    spectator_id: int
    state: str
    target: str
    lng: float
    lat: float


@dataclass(frozen=True, slots=True)
class MovementSnapshot:
    timestamp_s: int
    spectators: tuple[MovementPoint, ...]


@dataclass(slots=True)
class DashboardState:
    """In-memory dashboard state updated from MQTT payloads."""

    queue_trends: list[QueueTrendPoint] = field(default_factory=list)
    latest_kpi: KpiSnapshot | None = None
    latest_congestion: CongestionSnapshot | None = None
    latest_movement: MovementSnapshot | None = None
    active_run_id: str | None = None
    latest_timestamps_by_stream: dict[str, int] = field(default_factory=dict)


def _accept_run_id(state: DashboardState, payload: dict[str, Any]) -> bool:
    run_id_raw = payload.get("run_id")
    if not isinstance(run_id_raw, str) or not run_id_raw.strip():
        return False

    run_id = run_id_raw.strip()
    if state.active_run_id is None:
        state.active_run_id = run_id
        return True
    return run_id == state.active_run_id


def _is_newer_for_stream(state: DashboardState, stream: str, timestamp_s: int) -> bool:
    previous = state.latest_timestamps_by_stream.get(stream)
    if previous is None:
        return True
    return timestamp_s > previous


def _require_non_negative_int(name: str, value: Any) -> int:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _require_bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def normalize_wait_percentiles(wait_percentiles_s: dict[str, Any]) -> dict[str, float]:
    """Validate and normalize required wait-percentile keys P01..P100."""

    if not isinstance(wait_percentiles_s, dict):
        raise ValueError("wait_percentiles_s must be a dict")

    normalized: dict[str, float] = {}
    for percentile in range(1, 101):
        key = f"P{percentile:02d}"
        if key not in wait_percentiles_s:
            raise ValueError(f"wait_percentiles_s missing key {key}")
        value = wait_percentiles_s[key]
        if not isinstance(value, (int, float)) or float(value) < 0:
            raise ValueError(f"wait_percentiles_s.{key} must be a non-negative number")
        normalized[key] = float(value)
    return normalized


def parse_queue_state_payload(payload: dict[str, Any]) -> QueueTrendPoint:
    """Parse queue-state payload published by facility manager."""

    if not isinstance(payload, dict):
        raise ValueError("queue-state payload must be a dict")

    timestamp_s = _require_non_negative_int("timestamp_s", payload.get("timestamp_s"))
    queues = payload.get("queues")
    if not isinstance(queues, dict):
        raise ValueError("queues must be a dict")

    zone_a = queues.get("zone_a")
    zone_b = queues.get("zone_b")
    if not isinstance(zone_a, dict):
        raise ValueError("queues.zone_a must be a dict")
    if not isinstance(zone_b, dict):
        raise ValueError("queues.zone_b must be a dict")

    return QueueTrendPoint(
        timestamp_s=timestamp_s,
        zone_a_toilet=_require_non_negative_int("queues.zone_a.toilet", zone_a.get("toilet")),
        zone_a_cafe=_require_non_negative_int("queues.zone_a.cafe", zone_a.get("cafe")),
        zone_b_toilet=_require_non_negative_int("queues.zone_b.toilet", zone_b.get("toilet")),
        zone_b_cafe=_require_non_negative_int("queues.zone_b.cafe", zone_b.get("cafe")),
        shared_mens_urinal=_require_non_negative_int(
            "queues.shared_mens_urinal", queues.get("shared_mens_urinal")
        ),
    )


def parse_kpi_payload(payload: dict[str, Any]) -> KpiSnapshot:
    """Parse KPI payload expected for dashboard metric views."""

    if not isinstance(payload, dict):
        raise ValueError("kpi payload must be a dict")

    timestamp_s = _require_non_negative_int("timestamp_s", payload.get("timestamp_s"))

    average_wait = payload.get("average_wait_s")
    if not isinstance(average_wait, (int, float)) or float(average_wait) < 0:
        raise ValueError("average_wait_s must be a non-negative number")

    missed_kickoff = _require_non_negative_int("missed_kickoff_count", payload.get("missed_kickoff_count"))
    made_kickoff = _require_non_negative_int("made_kickoff_count", payload.get("made_kickoff_count", 0))
    stayed_seated = _require_non_negative_int("stayed_seated_count", payload.get("stayed_seated_count", 0))
    went_down = _require_non_negative_int("went_down_count", payload.get("went_down_count", 0))
    went_down_made_back = _require_non_negative_int(
        "went_down_made_back_count", payload.get("went_down_made_back_count", 0)
    )

    wait_percentiles = normalize_wait_percentiles(payload.get("wait_percentiles_s"))

    return KpiSnapshot(
        timestamp_s=timestamp_s,
        average_wait_s=float(average_wait),
        wait_percentiles_s=wait_percentiles,
        missed_kickoff_count=missed_kickoff,
        made_kickoff_count=made_kickoff,
        stayed_seated_count=stayed_seated,
        went_down_count=went_down,
        went_down_made_back_count=went_down_made_back,
    )


def parse_congestion_payload(payload: dict[str, Any]) -> CongestionSnapshot:
    """Parse optional congestion-state payload for dashboard context."""

    if not isinstance(payload, dict):
        raise ValueError("congestion payload must be a dict")

    timestamp_s = _require_non_negative_int("timestamp_s", payload.get("timestamp_s"))

    zone_a_blocked = _require_bool("zone_a_blocked", payload.get("zone_a_blocked"))
    zone_b_blocked = _require_bool("zone_b_blocked", payload.get("zone_b_blocked"))

    return CongestionSnapshot(
        timestamp_s=timestamp_s,
        zone_a_blocked=zone_a_blocked,
        zone_b_blocked=zone_b_blocked,
    )


def parse_movement_payload(payload: dict[str, Any]) -> MovementSnapshot:
    """Parse movement-state payload used for live map points."""

    if not isinstance(payload, dict):
        raise ValueError("movement payload must be a dict")

    timestamp_s = _require_non_negative_int("timestamp_s", payload.get("timestamp_s"))
    spectators_raw = payload.get("spectators")
    if not isinstance(spectators_raw, list):
        raise ValueError("spectators must be a list")

    points: list[MovementPoint] = []
    for index, spectator in enumerate(spectators_raw):
        if not isinstance(spectator, dict):
            raise ValueError(f"spectators[{index}] must be a dict")

        spectator_id = spectator.get("spectator_id")
        if not isinstance(spectator_id, int) or spectator_id <= 0:
            raise ValueError(f"spectators[{index}].spectator_id must be a positive integer")

        state = spectator.get("state")
        if not isinstance(state, str) or not state.strip():
            raise ValueError(f"spectators[{index}].state must be a non-empty string")

        target = spectator.get("target")
        if not isinstance(target, str) or not target.strip():
            raise ValueError(f"spectators[{index}].target must be a non-empty string")

        lng = spectator.get("lng")
        lat = spectator.get("lat")
        if not isinstance(lng, (int, float)) or float(lng) < -180.0 or float(lng) > 180.0:
            raise ValueError(f"spectators[{index}].lng must be within -180..180")
        if not isinstance(lat, (int, float)) or float(lat) < -90.0 or float(lat) > 90.0:
            raise ValueError(f"spectators[{index}].lat must be within -90..90")

        points.append(
            MovementPoint(
                spectator_id=spectator_id,
                state=state,
                target=target,
                lng=float(lng),
                lat=float(lat),
            )
        )

    return MovementSnapshot(timestamp_s=timestamp_s, spectators=tuple(points))


def update_dashboard_state_from_topic(
    state: DashboardState,
    topic: str,
    payload: dict[str, Any],
    *,
    topic_queue_state: str,
    topic_kpi_metrics: str,
    topic_congestion_state: str,
    topic_movement_state: str | None = None,
) -> None:
    """Update dashboard state from a topic + payload pair."""

    if not _accept_run_id(state, payload):
        return

    if topic == topic_queue_state:
        queue_point = parse_queue_state_payload(payload)
        if not _is_newer_for_stream(state, "queues", queue_point.timestamp_s):
            return
        state.queue_trends.append(queue_point)
        state.latest_timestamps_by_stream["queues"] = queue_point.timestamp_s
        return
    if topic == topic_kpi_metrics:
        parsed_kpi = parse_kpi_payload(payload)
        if not _is_newer_for_stream(state, "kpi", parsed_kpi.timestamp_s):
            return
        state.latest_kpi = parsed_kpi
        state.latest_timestamps_by_stream["kpi"] = state.latest_kpi.timestamp_s
        return
    if topic == topic_congestion_state:
        parsed_congestion = parse_congestion_payload(payload)
        if not _is_newer_for_stream(state, "congestion", parsed_congestion.timestamp_s):
            return
        state.latest_congestion = parsed_congestion
        state.latest_timestamps_by_stream["congestion"] = state.latest_congestion.timestamp_s
        return
    if topic_movement_state is not None and topic == topic_movement_state:
        parsed_movement = parse_movement_payload(payload)
        if not _is_newer_for_stream(state, "movement", parsed_movement.timestamp_s):
            return
        state.latest_movement = parsed_movement
        state.latest_timestamps_by_stream["movement"] = state.latest_movement.timestamp_s
