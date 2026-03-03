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


def _zone_block_limit(policy: CongestionPolicy) -> int:
    return policy.queue_people_per_line_threshold * policy.lines_considered


def evaluate_zone_cafe_blocked(zone_cafe_queue: int, policy: CongestionPolicy) -> bool:
    """Return True when a zone is considered blocked by cafe queue demand."""

    if zone_cafe_queue < 0:
        raise ValueError("zone_cafe_queue must be >= 0")
    return zone_cafe_queue >= _zone_block_limit(policy)


def build_congestion_from_queue_state(
    *,
    queue_state_payload: dict,
    policy: CongestionPolicy,
    schema_version: str = "1.0",
) -> dict:
    """Convert queue-state payload into congestion-state payload."""

    validate_queue_state_payload(queue_state_payload)

    run_id = str(queue_state_payload["run_id"])
    timestamp_s = int(queue_state_payload["timestamp_s"])

    queues = queue_state_payload["queues"]
    zone_a_cafe = int(queues["zone_a"]["cafe"])
    zone_b_cafe = int(queues["zone_b"]["cafe"])

    zone_a_blocked = evaluate_zone_cafe_blocked(zone_a_cafe, policy)
    zone_b_blocked = evaluate_zone_cafe_blocked(zone_b_cafe, policy)

    return build_congestion_state_payload(
        schema_version=schema_version,
        run_id=run_id,
        timestamp_s=timestamp_s,
        zone_a_blocked=zone_a_blocked,
        zone_b_blocked=zone_b_blocked,
    )
