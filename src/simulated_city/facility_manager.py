from __future__ import annotations

"""Facility manager logic for Phase 4 MQTT agent communication."""

from dataclasses import dataclass
import hashlib

from simulated_city.mqtt_payloads import (
    build_queue_state_payload,
    build_task_state_payload,
    validate_movement_state_payload,
    validate_spectator_event_payload,
)


@dataclass(slots=True)
class FacilityManagerState:
    """Mutable state for restart-safe spectator-event processing."""

    shared_urinal_total: int
    schema_version: str = "1.0"
    last_event_timestamp_s: int = -1
    last_movement_timestamp_s: int = -1
    last_task_state_by_spectator: dict[int, str] | None = None

    def __post_init__(self) -> None:
        if self.last_task_state_by_spectator is None:
            self.last_task_state_by_spectator = {}


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

    zone_1_toilet, zone_2_toilet = _split_by_ratio(remaining_toilet, toilet_ratio)
    zone_1_cafe, zone_2_cafe = _split_by_ratio(total_cafe, cafe_ratio)

    state.last_event_timestamp_s = timestamp_s

    return build_queue_state_payload(
        schema_version=state.schema_version,
        run_id=run_id,
        timestamp_s=timestamp_s,
        source_event_timestamp_s=timestamp_s,
        zone_a_toilet=zone_1_toilet,
        zone_a_cafe=zone_1_cafe,
        zone_b_toilet=zone_2_toilet,
        zone_b_cafe=zone_2_cafe,
        shared_urinal=shared_urinal_queue,
    )


def process_movement_snapshot(
    state: FacilityManagerState,
    movement_payload: dict,
) -> list[dict]:
    """Convert movement snapshot entries to task-state events.

    Internal route naming is canonical (`zone_1`, `zone_2`). Task-state events are
    emitted only when a spectator state transition changes the derived task state.
    """

    validate_movement_state_payload(movement_payload)

    timestamp_s = int(movement_payload["timestamp_s"])
    if timestamp_s <= state.last_movement_timestamp_s:
        return []

    run_id = str(movement_payload["run_id"])
    task_events: list[dict] = []

    for spectator in movement_payload["spectators"]:
        spectator_id = int(spectator["spectator_id"])
        movement_state = str(spectator["state"])
        target = str(spectator["target"])
        task_name = target.split("_", 2)[-1] if "_" in target else target

        if movement_state in {"WALKING_TO_ZONE", "WAITING"}:
            task_state = "queue_entered"
        elif movement_state == "IN_SERVICE":
            task_state = "service_started"
        elif movement_state in {"WALKING_TO_SEAT", "SEATED_DONE", "done"}:
            task_state = "service_completed"
        else:
            continue

        previous = state.last_task_state_by_spectator.get(spectator_id)
        if previous == task_state:
            continue

        payload = build_task_state_payload(
            schema_version=state.schema_version,
            run_id=run_id,
            timestamp_s=timestamp_s,
            spectator_id=spectator_id,
            task=task_name,
            task_state=task_state,
        )
        task_events.append(payload)
        state.last_task_state_by_spectator[spectator_id] = task_state

    state.last_movement_timestamp_s = timestamp_s
    return task_events
