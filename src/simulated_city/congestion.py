from __future__ import annotations

"""Congestion evaluation logic for Phase 6 congestion agent."""

from dataclasses import dataclass

from simulated_city.mqtt_payloads import (
    build_congestion_state_payload,
    validate_queue_state_payload,
)


@dataclass(frozen=True, slots=True)
class CongestionPolicy:
    """Threshold policy for per-zone cafe blocking decisions."""

    queue_people_per_line_threshold: int
    lines_considered: int

    def __post_init__(self) -> None:
        if self.queue_people_per_line_threshold < 0:
            raise ValueError("queue_people_per_line_threshold must be >= 0")
        if self.lines_considered <= 0:
            raise ValueError("lines_considered must be > 0")


@dataclass(slots=True)
class CongestionAgentState:
    """Mutable state used to harden congestion processing.

    - locks on first `run_id`
    - rejects out-of-order queue-state timestamps
    """

    active_run_id: str | None = None
    last_queue_timestamp_s: int = -1


def _zone_block_limit(policy: CongestionPolicy) -> int:
    return policy.queue_people_per_line_threshold * policy.lines_considered


def evaluate_zone_cafe_blocked(zone_cafe_queue: int, policy: CongestionPolicy) -> bool:
    """Return True when a zone is considered blocked by cafe queue demand."""

    if zone_cafe_queue < 0:
        raise ValueError("zone_cafe_queue must be >= 0")
    return zone_cafe_queue >= _zone_block_limit(policy)


def _accept_run_id_and_timestamp(
    state: CongestionAgentState,
    *,
    run_id: str,
    timestamp_s: int,
) -> bool:
    if state.active_run_id is None:
        state.active_run_id = run_id
    elif state.active_run_id != run_id:
        return False

    if timestamp_s <= state.last_queue_timestamp_s:
        return False

    state.last_queue_timestamp_s = timestamp_s
    return True


def _extract_zone_cafe_queues(queues: dict) -> tuple[int, int]:
    """Return zone-1/zone-2 cafe queue values from compatible payload keys.

    Supports boundary compatibility:
    - legacy: `zone_a`, `zone_b`
    - canonical: `zone_1`, `zone_2`
    """

    if "zone_a" in queues and "zone_b" in queues:
        zone_1 = queues["zone_a"]
        zone_2 = queues["zone_b"]
    elif "zone_1" in queues and "zone_2" in queues:
        zone_1 = queues["zone_1"]
        zone_2 = queues["zone_2"]
    else:
        raise ValueError("queues must contain either zone_a/zone_b or zone_1/zone_2")

    if not isinstance(zone_1, dict) or not isinstance(zone_2, dict):
        raise ValueError("zone queue entries must be dicts")

    zone_1_cafe = int(zone_1.get("cafe", 0))
    zone_2_cafe = int(zone_2.get("cafe", 0))
    if zone_1_cafe < 0 or zone_2_cafe < 0:
        raise ValueError("zone cafe queues must be >= 0")
    return zone_1_cafe, zone_2_cafe


def build_congestion_from_queue_state(
    *,
    queue_state_payload: dict,
    policy: CongestionPolicy,
    schema_version: str = "1.0",
    state: CongestionAgentState | None = None,
) -> dict | None:
    """Convert queue-state payload into congestion-state payload."""

    validate_queue_state_payload(queue_state_payload)

    run_id = str(queue_state_payload["run_id"])
    timestamp_s = int(queue_state_payload["timestamp_s"])

    if state is not None and not _accept_run_id_and_timestamp(state, run_id=run_id, timestamp_s=timestamp_s):
        return None

    queues = queue_state_payload["queues"]
    zone_1_cafe, zone_2_cafe = _extract_zone_cafe_queues(queues)

    zone_a_blocked = evaluate_zone_cafe_blocked(zone_1_cafe, policy)
    zone_b_blocked = evaluate_zone_cafe_blocked(zone_2_cafe, policy)

    return build_congestion_state_payload(
        schema_version=schema_version,
        run_id=run_id,
        timestamp_s=timestamp_s,
        zone_a_blocked=zone_a_blocked,
        zone_b_blocked=zone_b_blocked,
    )
