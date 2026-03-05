from __future__ import annotations

"""Metrics aggregation logic for Phase 6 metrics agent."""

from dataclasses import dataclass, field
from math import floor
from typing import Any

from simulated_city.mqtt_payloads import (
    build_kpi_metrics_payload,
    validate_queue_state_payload,
    validate_spectator_event_payload,
)


def enforce_final_scenario_policies(
    *,
    missed_kickoff_timestamp_s: int,
    external_disruptions_enabled: bool,
    group_coordination_share: float,
) -> None:
    """Enforce final Phase 6 scenario decisions.

    Decisions:
    - missed kickoff is evaluated exactly at 900 seconds
    - external disruptions are disabled
    - group coordination share is controlled in [0.0, 0.5]
    """

    if missed_kickoff_timestamp_s != 900:
        raise ValueError("Final scenario requires missed kickoff evaluation exactly at 900 seconds")
    if external_disruptions_enabled:
        raise ValueError("Final scenario disallows external disruption events")
    if not (0.0 <= group_coordination_share <= 0.5):
        raise ValueError("group_coordination_share must be in range [0.0, 0.5]")


@dataclass(slots=True)
class MetricsAggregatorState:
    """Mutable KPI aggregation state for a single simulation run."""

    halftime_duration_s: int = 900
    wait_samples_s: list[float] = field(default_factory=list)
    missed_kickoff_count: int = 0
    made_kickoff_count: int = 0
    stayed_seated_count: int = 0
    went_down_count: int = 0
    went_down_made_back_count: int = 0
    active_run_id: str | None = None
    last_spectator_timestamp_s: int = -1
    last_queue_timestamp_s: int = -1


def _percentile(sorted_values: list[float], percentile: int) -> float:
    if not sorted_values:
        return 0.0
    if percentile <= 1:
        return float(sorted_values[0])
    if percentile >= 100:
        return float(sorted_values[-1])

    n = len(sorted_values)
    rank = (percentile - 1) * (n - 1) / 99.0
    lower_index = floor(rank)
    upper_index = min(lower_index + 1, n - 1)
    fraction = rank - lower_index
    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    return float(lower_value + (upper_value - lower_value) * fraction)


def _proxy_wait_from_queue_total(total_queue_people: int) -> float:
    """Convert queue demand to a stable wait-time proxy in seconds."""

    # Calibrated to stay on the same magnitude as simulation_core average_wait_s.
    return float(total_queue_people * 0.6)


def _accept_run_id(state: MetricsAggregatorState, payload: dict[str, Any]) -> bool:
    run_id_raw = payload.get("run_id")
    if not isinstance(run_id_raw, str) or not run_id_raw.strip():
        return False

    run_id = run_id_raw.strip()
    if state.active_run_id is None:
        state.active_run_id = run_id
        return True
    return run_id == state.active_run_id


def record_spectator_event(state: MetricsAggregatorState, payload: dict) -> None:
    """Ingest spectator-event payload into KPI aggregation state."""

    validate_spectator_event_payload(payload)
    if not _accept_run_id(state, payload):
        return

    timestamp_s = int(payload["timestamp_s"])
    if timestamp_s <= state.last_spectator_timestamp_s:
        return
    state.last_spectator_timestamp_s = timestamp_s

    queue_lengths = payload["queue_lengths"]
    queue_total = int(queue_lengths["toilet"]) + int(queue_lengths["cafe"])

    state.wait_samples_s.append(_proxy_wait_from_queue_total(queue_total))

    if timestamp_s == state.halftime_duration_s:
        state.missed_kickoff_count = int(payload["spectators_out_of_seat"])
        state.made_kickoff_count = int(payload.get("made_kickoff_count", state.made_kickoff_count))
        state.stayed_seated_count = int(payload.get("stayed_seated_count", state.stayed_seated_count))
        state.went_down_count = int(payload.get("went_down_count", state.went_down_count))
        state.went_down_made_back_count = int(
            payload.get("went_down_made_back_count", state.went_down_made_back_count)
        )


def record_queue_state(state: MetricsAggregatorState, payload: dict) -> None:
    """Ingest queue-state payload into KPI aggregation state."""

    validate_queue_state_payload(payload)
    if not _accept_run_id(state, payload):
        return

    timestamp_s = int(payload["timestamp_s"])
    if timestamp_s <= state.last_queue_timestamp_s:
        return
    state.last_queue_timestamp_s = timestamp_s

    queues = payload["queues"]
    queue_total = (
        int(queues["zone_a"]["toilet"])
        + int(queues["zone_a"]["cafe"])
        + int(queues["zone_b"]["toilet"])
        + int(queues["zone_b"]["cafe"])
        + int(queues["shared_mens_urinal"])
    )
    state.wait_samples_s.append(_proxy_wait_from_queue_total(queue_total))


def finalize_kpi_payload(
    *,
    state: MetricsAggregatorState,
    run_id: str,
    timestamp_s: int,
    schema_version: str = "1.0",
) -> dict:
    """Produce final KPI payload including P01..P100 percentiles."""

    if state.active_run_id is not None and run_id != state.active_run_id:
        raise ValueError("run_id must match MetricsAggregatorState.active_run_id")
    if state.active_run_id is None:
        state.active_run_id = run_id

    if timestamp_s < state.halftime_duration_s:
        raise ValueError("timestamp_s must be >= halftime_duration_s when finalizing KPI payload")

    sorted_samples = sorted(state.wait_samples_s)
    average_wait_s = sum(sorted_samples) / len(sorted_samples) if sorted_samples else 0.0

    wait_percentiles_s = {
        f"P{percentile:02d}": _percentile(sorted_samples, percentile)
        for percentile in range(1, 101)
    }

    return build_kpi_metrics_payload(
        schema_version=schema_version,
        run_id=run_id,
        timestamp_s=timestamp_s,
        average_wait_s=average_wait_s,
        wait_percentiles_s=wait_percentiles_s,
        missed_kickoff_count=state.missed_kickoff_count,
        made_kickoff_count=state.made_kickoff_count,
        stayed_seated_count=state.stayed_seated_count,
        went_down_count=state.went_down_count,
        went_down_made_back_count=state.went_down_made_back_count,
    )
