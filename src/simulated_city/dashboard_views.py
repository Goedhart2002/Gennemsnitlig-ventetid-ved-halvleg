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


@dataclass(slots=True)
class DashboardState:
    """In-memory dashboard state updated from MQTT payloads."""

    queue_trends: list[QueueTrendPoint] = field(default_factory=list)
    latest_kpi: KpiSnapshot | None = None
    latest_congestion: CongestionSnapshot | None = None
    active_run_id: str | None = None


def _accept_run_id(state: DashboardState, payload: dict[str, Any]) -> bool:
    run_id_raw = payload.get("run_id")
    if not isinstance(run_id_raw, str) or not run_id_raw.strip():
        return False

    run_id = run_id_raw.strip()
    if state.active_run_id is None:
        state.active_run_id = run_id
        return True
    return run_id == state.active_run_id


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


def update_dashboard_state_from_topic(
    state: DashboardState,
    topic: str,
    payload: dict[str, Any],
    *,
    topic_queue_state: str,
    topic_kpi_metrics: str,
    topic_congestion_state: str,
) -> None:
    """Update dashboard state from a topic + payload pair."""

    if not _accept_run_id(state, payload):
        return

    if topic == topic_queue_state:
        state.queue_trends.append(parse_queue_state_payload(payload))
        return
    if topic == topic_kpi_metrics:
        state.latest_kpi = parse_kpi_payload(payload)
        return
    if topic == topic_congestion_state:
        state.latest_congestion = parse_congestion_payload(payload)
