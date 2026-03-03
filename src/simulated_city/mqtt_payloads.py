from __future__ import annotations

"""Payload builders and validation for Phase 3 MQTT publishing."""

from typing import Any


def build_spectator_event_payload(
    *,
    schema_version: str,
    run_id: str,
    timestamp_s: int,
    spectators_out_of_seat: int,
    queue_toilet: int,
    queue_cafe: int,
    stayed_seated_count: int | None = None,
    went_down_count: int | None = None,
    went_down_made_back_count: int | None = None,
) -> dict[str, Any]:
    """Build a spectator event payload with required envelope fields."""

    payload: dict[str, Any] = {
        "schema_version": schema_version,
        "run_id": run_id,
        "timestamp_s": timestamp_s,
        "spectators_out_of_seat": spectators_out_of_seat,
        "queue_lengths": {
            "toilet": queue_toilet,
            "cafe": queue_cafe,
        },
    }
    if stayed_seated_count is not None:
        payload["stayed_seated_count"] = stayed_seated_count
    if went_down_count is not None:
        payload["went_down_count"] = went_down_count
    if went_down_made_back_count is not None:
        payload["went_down_made_back_count"] = went_down_made_back_count
    validate_spectator_event_payload(payload)
    return payload


def validate_spectator_event_payload(payload: dict[str, Any]) -> None:
    """Validate required Phase 3 spectator event payload shape and value types."""

    if not isinstance(payload, dict):
        raise ValueError("Spectator payload must be a dict")

    required = ("schema_version", "run_id", "timestamp_s", "spectators_out_of_seat", "queue_lengths")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"Spectator payload missing required keys: {missing}")

    if not isinstance(payload["schema_version"], str) or not payload["schema_version"].strip():
        raise ValueError("schema_version must be a non-empty string")

    if not isinstance(payload["run_id"], str) or not payload["run_id"].strip():
        raise ValueError("run_id must be a non-empty string")

    timestamp_s = payload["timestamp_s"]
    if not isinstance(timestamp_s, int) or timestamp_s < 0:
        raise ValueError("timestamp_s must be a non-negative integer")

    spectators_out = payload["spectators_out_of_seat"]
    if not isinstance(spectators_out, int) or spectators_out < 0:
        raise ValueError("spectators_out_of_seat must be a non-negative integer")

    queue_lengths = payload["queue_lengths"]
    if not isinstance(queue_lengths, dict):
        raise ValueError("queue_lengths must be a dict")

    for key in ("toilet", "cafe"):
        if key not in queue_lengths:
            raise ValueError(f"queue_lengths must include '{key}'")
        value = queue_lengths[key]
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"queue_lengths.{key} must be a non-negative integer")

    for optional_field in ("stayed_seated_count", "went_down_count", "went_down_made_back_count"):
        if optional_field in payload:
            optional_value = payload[optional_field]
            if not isinstance(optional_value, int) or optional_value < 0:
                raise ValueError(f"{optional_field} must be a non-negative integer")


def build_queue_state_payload(
    *,
    schema_version: str,
    run_id: str,
    timestamp_s: int,
    source_event_timestamp_s: int,
    zone_a_toilet: int,
    zone_a_cafe: int,
    zone_b_toilet: int,
    zone_b_cafe: int,
    shared_urinal: int,
) -> dict[str, Any]:
    """Build facility-manager queue state payload for Phase 4."""

    payload: dict[str, Any] = {
        "schema_version": schema_version,
        "run_id": run_id,
        "timestamp_s": timestamp_s,
        "source_event_timestamp_s": source_event_timestamp_s,
        "queues": {
            "zone_a": {
                "toilet": zone_a_toilet,
                "cafe": zone_a_cafe,
            },
            "zone_b": {
                "toilet": zone_b_toilet,
                "cafe": zone_b_cafe,
            },
            "shared_mens_urinal": shared_urinal,
        },
    }
    validate_queue_state_payload(payload)
    return payload


def validate_queue_state_payload(payload: dict[str, Any]) -> None:
    """Validate required queue-state payload fields and value ranges."""

    if not isinstance(payload, dict):
        raise ValueError("Queue state payload must be a dict")

    required = ("schema_version", "run_id", "timestamp_s", "source_event_timestamp_s", "queues")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"Queue state payload missing required keys: {missing}")

    if not isinstance(payload["schema_version"], str) or not payload["schema_version"].strip():
        raise ValueError("schema_version must be a non-empty string")
    if not isinstance(payload["run_id"], str) or not payload["run_id"].strip():
        raise ValueError("run_id must be a non-empty string")

    for field in ("timestamp_s", "source_event_timestamp_s"):
        value = payload[field]
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"{field} must be a non-negative integer")

    queues = payload["queues"]
    if not isinstance(queues, dict):
        raise ValueError("queues must be a dict")

    for zone in ("zone_a", "zone_b"):
        if zone not in queues or not isinstance(queues[zone], dict):
            raise ValueError(f"queues.{zone} must be a dict")
        for key in ("toilet", "cafe"):
            if key not in queues[zone]:
                raise ValueError(f"queues.{zone}.{key} is required")
            zone_value = queues[zone][key]
            if not isinstance(zone_value, int) or zone_value < 0:
                raise ValueError(f"queues.{zone}.{key} must be a non-negative integer")

    if "shared_mens_urinal" not in queues:
        raise ValueError("queues.shared_mens_urinal is required")
    urinal_value = queues["shared_mens_urinal"]
    if not isinstance(urinal_value, int) or urinal_value < 0:
        raise ValueError("queues.shared_mens_urinal must be a non-negative integer")


def build_congestion_state_payload(
    *,
    schema_version: str,
    run_id: str,
    timestamp_s: int,
    zone_a_blocked: bool,
    zone_b_blocked: bool,
) -> dict[str, Any]:
    """Build congestion-state payload published by Phase 6 congestion agent."""

    payload: dict[str, Any] = {
        "schema_version": schema_version,
        "run_id": run_id,
        "timestamp_s": timestamp_s,
        "zone_a_blocked": zone_a_blocked,
        "zone_b_blocked": zone_b_blocked,
    }
    validate_congestion_state_payload(payload)
    return payload


def validate_congestion_state_payload(payload: dict[str, Any]) -> None:
    """Validate congestion-state payload shape and types."""

    if not isinstance(payload, dict):
        raise ValueError("Congestion payload must be a dict")

    required = ("schema_version", "run_id", "timestamp_s", "zone_a_blocked", "zone_b_blocked")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"Congestion payload missing required keys: {missing}")

    if not isinstance(payload["schema_version"], str) or not payload["schema_version"].strip():
        raise ValueError("schema_version must be a non-empty string")
    if not isinstance(payload["run_id"], str) or not payload["run_id"].strip():
        raise ValueError("run_id must be a non-empty string")

    timestamp_s = payload["timestamp_s"]
    if not isinstance(timestamp_s, int) or timestamp_s < 0:
        raise ValueError("timestamp_s must be a non-negative integer")

    for field in ("zone_a_blocked", "zone_b_blocked"):
        if not isinstance(payload[field], bool):
            raise ValueError(f"{field} must be a boolean")


def build_kpi_metrics_payload(
    *,
    schema_version: str,
    run_id: str,
    timestamp_s: int,
    average_wait_s: float,
    wait_percentiles_s: dict[str, float],
    missed_kickoff_count: int,
    made_kickoff_count: int,
    stayed_seated_count: int,
    went_down_count: int,
    went_down_made_back_count: int,
) -> dict[str, Any]:
    """Build KPI metrics payload for Phase 6 metrics agent."""

    payload: dict[str, Any] = {
        "schema_version": schema_version,
        "run_id": run_id,
        "timestamp_s": timestamp_s,
        "average_wait_s": average_wait_s,
        "wait_percentiles_s": wait_percentiles_s,
        "missed_kickoff_count": missed_kickoff_count,
        "made_kickoff_count": made_kickoff_count,
        "stayed_seated_count": stayed_seated_count,
        "went_down_count": went_down_count,
        "went_down_made_back_count": went_down_made_back_count,
    }
    validate_kpi_metrics_payload(payload)
    return payload


def validate_kpi_metrics_payload(payload: dict[str, Any]) -> None:
    """Validate KPI payload including complete percentile profile P01..P100."""

    if not isinstance(payload, dict):
        raise ValueError("KPI payload must be a dict")

    required = (
        "schema_version",
        "run_id",
        "timestamp_s",
        "average_wait_s",
        "wait_percentiles_s",
        "missed_kickoff_count",
        "made_kickoff_count",
        "stayed_seated_count",
        "went_down_count",
        "went_down_made_back_count",
    )
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"KPI payload missing required keys: {missing}")

    if not isinstance(payload["schema_version"], str) or not payload["schema_version"].strip():
        raise ValueError("schema_version must be a non-empty string")
    if not isinstance(payload["run_id"], str) or not payload["run_id"].strip():
        raise ValueError("run_id must be a non-empty string")

    timestamp_s = payload["timestamp_s"]
    if not isinstance(timestamp_s, int) or timestamp_s < 0:
        raise ValueError("timestamp_s must be a non-negative integer")

    average_wait_s = payload["average_wait_s"]
    if not isinstance(average_wait_s, (int, float)) or float(average_wait_s) < 0:
        raise ValueError("average_wait_s must be a non-negative number")

    for int_field in (
        "missed_kickoff_count",
        "made_kickoff_count",
        "stayed_seated_count",
        "went_down_count",
        "went_down_made_back_count",
    ):
        int_value = payload[int_field]
        if not isinstance(int_value, int) or int_value < 0:
            raise ValueError(f"{int_field} must be a non-negative integer")

    wait_percentiles_s = payload["wait_percentiles_s"]
    if not isinstance(wait_percentiles_s, dict):
        raise ValueError("wait_percentiles_s must be a dict")

    for percentile in range(1, 101):
        key = f"P{percentile:02d}"
        if key not in wait_percentiles_s:
            raise ValueError(f"wait_percentiles_s missing key {key}")
        value = wait_percentiles_s[key]
        if not isinstance(value, (int, float)) or float(value) < 0:
            raise ValueError(f"wait_percentiles_s.{key} must be a non-negative number")
