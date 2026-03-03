from simulated_city.dashboard_views import (
    DashboardState,
    normalize_wait_percentiles,
    parse_congestion_payload,
    parse_kpi_payload,
    parse_queue_state_payload,
    update_dashboard_state_from_topic,
)
from simulated_city.topic_schema import (
    topic_congestion_state,
    topic_kpi_metrics,
    topic_queue_state,
)


def _wait_percentiles() -> dict[str, float]:
    return {f"P{index:02d}": float(index) for index in range(1, 101)}


def test_phase5_parse_queue_state_payload_shape() -> None:
    payload = {
        "timestamp_s": 42,
        "queues": {
            "zone_a": {"toilet": 10, "cafe": 6},
            "zone_b": {"toilet": 12, "cafe": 4},
            "shared_mens_urinal": 5,
        },
    }

    parsed = parse_queue_state_payload(payload)

    assert parsed.timestamp_s == 42
    assert parsed.zone_a_toilet == 10
    assert parsed.zone_b_cafe == 4
    assert parsed.shared_mens_urinal == 5


def test_phase5_normalize_wait_percentiles_requires_p01_to_p100() -> None:
    values = _wait_percentiles()
    normalized = normalize_wait_percentiles(values)

    assert normalized["P01"] == 1.0
    assert normalized["P100"] == 100.0


def test_phase5_parse_kpi_payload_shape() -> None:
    payload = {
        "timestamp_s": 90,
        "average_wait_s": 123.5,
        "wait_percentiles_s": _wait_percentiles(),
        "missed_kickoff_count": 77,
        "made_kickoff_count": 923,
        "stayed_seated_count": 300,
        "went_down_count": 700,
        "went_down_made_back_count": 623,
    }

    parsed = parse_kpi_payload(payload)

    assert parsed.timestamp_s == 90
    assert parsed.average_wait_s == 123.5
    assert parsed.missed_kickoff_count == 77
    assert parsed.made_kickoff_count == 923
    assert parsed.stayed_seated_count == 300
    assert parsed.went_down_count == 700
    assert parsed.went_down_made_back_count == 623
    assert len(parsed.wait_percentiles_s) == 100


def test_phase5_parse_congestion_payload_shape() -> None:
    payload = {
        "timestamp_s": 120,
        "zone_a_blocked": True,
        "zone_b_blocked": False,
    }

    parsed = parse_congestion_payload(payload)

    assert parsed.timestamp_s == 120
    assert parsed.zone_a_blocked is True
    assert parsed.zone_b_blocked is False


def test_phase5_state_update_by_topic() -> None:
    state = DashboardState()

    update_dashboard_state_from_topic(
        state,
        topic_queue_state(),
        {
            "run_id": "run-a",
            "timestamp_s": 10,
            "queues": {
                "zone_a": {"toilet": 1, "cafe": 2},
                "zone_b": {"toilet": 3, "cafe": 4},
                "shared_mens_urinal": 5,
            },
        },
        topic_queue_state=topic_queue_state(),
        topic_kpi_metrics=topic_kpi_metrics(),
        topic_congestion_state=topic_congestion_state(),
    )
    update_dashboard_state_from_topic(
        state,
        topic_kpi_metrics(),
        {
            "run_id": "run-a",
            "timestamp_s": 20,
            "average_wait_s": 90,
            "wait_percentiles_s": _wait_percentiles(),
            "missed_kickoff_count": 15,
            "made_kickoff_count": 85,
            "stayed_seated_count": 20,
            "went_down_count": 80,
            "went_down_made_back_count": 65,
        },
        topic_queue_state=topic_queue_state(),
        topic_kpi_metrics=topic_kpi_metrics(),
        topic_congestion_state=topic_congestion_state(),
    )

    assert len(state.queue_trends) == 1
    assert state.latest_kpi is not None
    assert state.latest_kpi.missed_kickoff_count == 15
    assert state.latest_kpi.went_down_made_back_count == 65


def test_phase5_state_update_ignores_other_run_ids() -> None:
    state = DashboardState()

    update_dashboard_state_from_topic(
        state,
        topic_queue_state(),
        {
            "run_id": "run-a",
            "timestamp_s": 10,
            "queues": {
                "zone_a": {"toilet": 1, "cafe": 2},
                "zone_b": {"toilet": 3, "cafe": 4},
                "shared_mens_urinal": 5,
            },
        },
        topic_queue_state=topic_queue_state(),
        topic_kpi_metrics=topic_kpi_metrics(),
        topic_congestion_state=topic_congestion_state(),
    )

    update_dashboard_state_from_topic(
        state,
        topic_queue_state(),
        {
            "run_id": "run-b",
            "timestamp_s": 11,
            "queues": {
                "zone_a": {"toilet": 9, "cafe": 9},
                "zone_b": {"toilet": 9, "cafe": 9},
                "shared_mens_urinal": 9,
            },
        },
        topic_queue_state=topic_queue_state(),
        topic_kpi_metrics=topic_kpi_metrics(),
        topic_congestion_state=topic_congestion_state(),
    )

    assert len(state.queue_trends) == 1
