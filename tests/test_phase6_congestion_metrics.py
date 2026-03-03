from simulated_city.congestion import (
    CongestionPolicy,
    build_congestion_from_queue_state,
    evaluate_zone_cafe_blocked,
)
from simulated_city.metrics import (
    MetricsAggregatorState,
    enforce_final_scenario_policies,
    finalize_kpi_payload,
    record_queue_state,
    record_spectator_event,
)


def _queue_state_payload(cafe_a: int, cafe_b: int) -> dict:
    return {
        "schema_version": "1.0",
        "run_id": "run-1",
        "timestamp_s": 100,
        "source_event_timestamp_s": 100,
        "queues": {
            "zone_a": {"toilet": 10, "cafe": cafe_a},
            "zone_b": {"toilet": 10, "cafe": cafe_b},
            "shared_mens_urinal": 4,
        },
    }


def _spectator_event(ts: int, out_of_seat: int, toilet: int, cafe: int) -> dict:
    return {
        "schema_version": "1.0",
        "run_id": "run-1",
        "timestamp_s": ts,
        "spectators_out_of_seat": out_of_seat,
        "stayed_seated_count": 300,
        "went_down_count": 700,
        "went_down_made_back_count": 612,
        "made_kickoff_count": 912,
        "queue_lengths": {
            "toilet": toilet,
            "cafe": cafe,
        },
    }


def test_phase6_congestion_policy_blocks_by_zone_cafe_total() -> None:
    policy = CongestionPolicy(queue_people_per_line_threshold=15, lines_considered=2)

    assert evaluate_zone_cafe_blocked(30, policy) is True
    assert evaluate_zone_cafe_blocked(29, policy) is False


def test_phase6_build_congestion_payload_from_queue_state() -> None:
    policy = CongestionPolicy(queue_people_per_line_threshold=10, lines_considered=2)
    payload = _queue_state_payload(cafe_a=25, cafe_b=15)

    congestion = build_congestion_from_queue_state(queue_state_payload=payload, policy=policy)

    assert congestion["timestamp_s"] == 100
    assert congestion["zone_a_blocked"] is True
    assert congestion["zone_b_blocked"] is False


def test_phase6_metrics_kpi_payload_contains_full_percentile_profile() -> None:
    state = MetricsAggregatorState(halftime_duration_s=900)
    record_queue_state(state, _queue_state_payload(cafe_a=10, cafe_b=12))
    record_queue_state(state, _queue_state_payload(cafe_a=20, cafe_b=22))
    record_spectator_event(state, _spectator_event(900, out_of_seat=88, toilet=20, cafe=10))

    kpi = finalize_kpi_payload(state=state, run_id="run-1", timestamp_s=900)

    assert "average_wait_s" in kpi
    assert "wait_percentiles_s" in kpi
    assert "missed_kickoff_count" in kpi
    assert "made_kickoff_count" in kpi
    assert "stayed_seated_count" in kpi
    assert "went_down_count" in kpi
    assert "went_down_made_back_count" in kpi
    assert len(kpi["wait_percentiles_s"]) == 100
    assert "P01" in kpi["wait_percentiles_s"]
    assert "P100" in kpi["wait_percentiles_s"]
    assert kpi["missed_kickoff_count"] == 88


def test_phase6_missed_kickoff_uses_exact_900_seconds() -> None:
    state = MetricsAggregatorState(halftime_duration_s=900)

    record_spectator_event(state, _spectator_event(899, out_of_seat=20, toilet=10, cafe=5))
    record_spectator_event(state, _spectator_event(900, out_of_seat=42, toilet=12, cafe=6))
    record_spectator_event(state, _spectator_event(901, out_of_seat=99, toilet=15, cafe=7))

    assert state.missed_kickoff_count == 42


def test_phase6_final_policy_enforcement() -> None:
    enforce_final_scenario_policies(
        missed_kickoff_timestamp_s=900,
        external_disruptions_enabled=False,
        group_coordination_share=0.2,
    )

    try:
        enforce_final_scenario_policies(
            missed_kickoff_timestamp_s=901,
            external_disruptions_enabled=False,
            group_coordination_share=0.2,
        )
        assert False, "Expected ValueError for wrong missed kickoff timestamp"
    except ValueError as error:
        assert "900" in str(error)


def test_phase6_metrics_ignores_other_run_ids() -> None:
    state = MetricsAggregatorState(halftime_duration_s=900)

    record_spectator_event(state, _spectator_event(100, out_of_seat=10, toilet=5, cafe=5))
    first_count = len(state.wait_samples_s)

    other_run_event = _spectator_event(110, out_of_seat=30, toilet=20, cafe=10)
    other_run_event["run_id"] = "run-2"
    record_spectator_event(state, other_run_event)

    assert len(state.wait_samples_s) == first_count
