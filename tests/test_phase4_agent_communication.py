from simulated_city.facility_manager import (
    FacilityManagerState,
    process_movement_snapshot,
    process_spectator_event,
)
from simulated_city.mqtt_payloads import validate_queue_state_payload, validate_task_state_payload
from simulated_city.topic_schema import (
    topic_movement_state,
    topic_queue_state,
    topic_spectator_events,
    topic_task_state,
)


def _spectator_event(*, ts: int, toilet: int, cafe: int, run_id: str = "run-1") -> dict:
    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "timestamp_s": ts,
        "spectators_out_of_seat": toilet + cafe,
        "queue_lengths": {
            "toilet": toilet,
            "cafe": cafe,
        },
    }


def test_phase4_topics_are_defined() -> None:
    assert topic_spectator_events() == "stadium/a4/halftime/events/spectator"
    assert topic_movement_state() == "stadium/a4/halftime/state/movement"
    assert topic_queue_state() == "stadium/a4/halftime/state/queues"
    assert topic_task_state() == "stadium/a4/halftime/state/tasks"


def test_phase4_facility_manager_transforms_event_to_queue_state() -> None:
    state = FacilityManagerState(shared_urinal_total=16)
    event = _spectator_event(ts=10, toilet=120, cafe=40, run_id="run-a")

    queue_state = process_spectator_event(state, event)

    assert queue_state is not None
    validate_queue_state_payload(queue_state)
    assert queue_state["run_id"] == "run-a"
    assert queue_state["timestamp_s"] == 10
    assert queue_state["source_event_timestamp_s"] == 10

    zone_a = queue_state["queues"]["zone_a"]
    zone_b = queue_state["queues"]["zone_b"]
    shared_urinal = queue_state["queues"]["shared_mens_urinal"]

    assert zone_a["toilet"] >= 0
    assert zone_b["toilet"] >= 0
    assert zone_a["cafe"] >= 0
    assert zone_b["cafe"] >= 0
    assert shared_urinal >= 0

    # Totals remain consistent after splitting and urinal extraction.
    assert zone_a["toilet"] + zone_b["toilet"] + shared_urinal == 120
    assert zone_a["cafe"] + zone_b["cafe"] == 40


def test_phase4_restart_safe_ignores_stale_event() -> None:
    state = FacilityManagerState(shared_urinal_total=16)

    first = process_spectator_event(state, _spectator_event(ts=20, toilet=50, cafe=10))
    stale = process_spectator_event(state, _spectator_event(ts=20, toilet=60, cafe=20))
    older = process_spectator_event(state, _spectator_event(ts=19, toilet=60, cafe=20))

    assert first is not None
    assert stale is None
    assert older is None


def test_phase4_shared_urinal_is_capped_by_capacity_model() -> None:
    state = FacilityManagerState(shared_urinal_total=4)
    queue_state = process_spectator_event(state, _spectator_event(ts=1, toilet=500, cafe=0))

    assert queue_state is not None
    # shared_urinal_total * 3 upper cap from facility manager model
    assert queue_state["queues"]["shared_mens_urinal"] == 12


def test_phase4_two_zones_are_used_simultaneously() -> None:
    state = FacilityManagerState(shared_urinal_total=16)
    queue_state = process_spectator_event(
        state,
        _spectator_event(ts=55, toilet=120, cafe=80, run_id="run-two-zones"),
    )

    assert queue_state is not None
    zone_a = queue_state["queues"]["zone_a"]
    zone_b = queue_state["queues"]["zone_b"]

    # Both zones should receive active demand in the same timestamp.
    assert zone_a["toilet"] > 0
    assert zone_b["toilet"] > 0
    assert zone_a["cafe"] > 0
    assert zone_b["cafe"] > 0

    # Zone queues are not forced to be mirrored copies.
    assert (zone_a["toilet"], zone_a["cafe"]) != (zone_b["toilet"], zone_b["cafe"])


def test_phase4_movement_snapshot_generates_task_events_with_same_run_id() -> None:
    state = FacilityManagerState(shared_urinal_total=16)
    movement_payload = {
        "schema_version": "1.0",
        "run_id": "run-movement-1",
        "timestamp_s": 25,
        "spectators": [
            {
                "spectator_id": 1,
                "state": "WALKING_TO_ZONE",
                "target": "zone_1_toilet_w",
                "lng": 12.5684,
                "lat": 55.6761,
            },
            {
                "spectator_id": 2,
                "state": "IN_SERVICE",
                "target": "zone_2_cafe",
                "lng": 12.5691,
                "lat": 55.67598,
            },
        ],
    }

    task_events = process_movement_snapshot(state, movement_payload)

    assert len(task_events) == 2
    for event in task_events:
        validate_task_state_payload(event)
        assert event["run_id"] == "run-movement-1"
        assert event["timestamp_s"] == 25


def test_phase4_movement_snapshot_deduplicates_same_task_state() -> None:
    state = FacilityManagerState(shared_urinal_total=16)
    movement_payload = {
        "schema_version": "1.0",
        "run_id": "run-movement-2",
        "timestamp_s": 30,
        "spectators": [
            {
                "spectator_id": 7,
                "state": "WAITING",
                "target": "zone_1_toilet_m",
                "lng": 12.5679,
                "lat": 55.67622,
            }
        ],
    }

    first = process_movement_snapshot(state, movement_payload)
    second = process_movement_snapshot(state, movement_payload)

    assert len(first) == 1
    assert second == []


def test_phase4_movement_snapshot_ignores_older_timestamp() -> None:
    state = FacilityManagerState(shared_urinal_total=16)
    newer_payload = {
        "schema_version": "1.0",
        "run_id": "run-movement-3",
        "timestamp_s": 40,
        "spectators": [
            {
                "spectator_id": 8,
                "state": "WAITING",
                "target": "zone_2_toilet_m",
                "lng": 12.5689,
                "lat": 55.6760,
            }
        ],
    }
    older_payload = {
        "schema_version": "1.0",
        "run_id": "run-movement-3",
        "timestamp_s": 39,
        "spectators": [
            {
                "spectator_id": 8,
                "state": "IN_SERVICE",
                "target": "zone_2_toilet_m",
                "lng": 12.5689,
                "lat": 55.6760,
            }
        ],
    }

    first = process_movement_snapshot(state, newer_payload)
    older = process_movement_snapshot(state, older_payload)

    assert len(first) == 1
    assert older == []
