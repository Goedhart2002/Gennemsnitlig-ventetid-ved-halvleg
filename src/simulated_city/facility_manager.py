from __future__ import annotations

"""Facility manager logic for Phase 4 MQTT agent communication."""

from dataclasses import dataclass
import hashlib

from simulated_city.mqtt_payloads import (
    build_queue_state_payload,
    validate_spectator_event_payload,
)


@dataclass(slots=True)
class FacilityManagerState:
    """Mutable state for restart-safe spectator-event processing."""

    shared_urinal_total: int
    schema_version: str = "1.0"
    last_event_timestamp_s: int = -1


def _stable_zone_ratio(*, run_id: str, timestamp_s: int, channel: str) -> float:
    """Return deterministic per-event zone A ratio in [0.35, 0.65]."""

    key = f"{run_id}:{timestamp_s}:{channel}".encode("utf-8")
    digest = hashlib.sha256(key).digest()
    raw = int.from_bytes(digest[:8], byteorder="big", signed=False)
    normalized = raw / float((1 << 64) - 1)
    return 0.35 + (0.30 * normalized)


def _split_by_ratio(total: int, zone_a_ratio: float) -> tuple[int, int]:
    if total <= 0:
        return 0, 0

    zone_a = int(round(total * zone_a_ratio))
    zone_a = max(0, min(total, zone_a))
    zone_b = total - zone_a

    # Keep both zones active whenever total demand has at least two people.
    if total >= 2:
        if zone_a == 0:
            zone_a, zone_b = 1, total - 1
        elif zone_b == 0:
            zone_a, zone_b = total - 1, 1

    return zone_a, zone_b


def process_spectator_event(
    state: FacilityManagerState,
    event_payload: dict,
) -> dict | None:
    """Convert spectator event payload to queue-state payload.

    Returns None for stale events to keep processing restart-safe and monotonic.
    """

    validate_spectator_event_payload(event_payload)

    timestamp_s = int(event_payload["timestamp_s"])
    if timestamp_s <= state.last_event_timestamp_s:
        return None

    run_id = str(event_payload["run_id"])
    spectator_queues = event_payload["queue_lengths"]

    total_toilet = int(spectator_queues["toilet"])
    total_cafe = int(spectator_queues["cafe"])

    estimated_urinal_demand = int(round(total_toilet * 0.35))
    shared_urinal_queue = min(max(0, state.shared_urinal_total * 3), max(0, estimated_urinal_demand))

    remaining_toilet = max(0, total_toilet - shared_urinal_queue)
    toilet_ratio = _stable_zone_ratio(run_id=run_id, timestamp_s=timestamp_s, channel="toilet")
    cafe_ratio = _stable_zone_ratio(run_id=run_id, timestamp_s=timestamp_s, channel="cafe")

    zone_a_toilet, zone_b_toilet = _split_by_ratio(remaining_toilet, toilet_ratio)
    zone_a_cafe, zone_b_cafe = _split_by_ratio(total_cafe, cafe_ratio)

    state.last_event_timestamp_s = timestamp_s

    return build_queue_state_payload(
        schema_version=state.schema_version,
        run_id=run_id,
        timestamp_s=timestamp_s,
        source_event_timestamp_s=timestamp_s,
        zone_a_toilet=zone_a_toilet,
        zone_a_cafe=zone_a_cafe,
        zone_b_toilet=zone_b_toilet,
        zone_b_cafe=zone_b_cafe,
        shared_urinal=shared_urinal_queue,
    )
