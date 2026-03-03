from __future__ import annotations

"""MQTT topic schema constants for Section A4 halftime simulation."""

STADIUM_A4_HALFTIME_SPECTATOR_EVENTS = "stadium/a4/halftime/events/spectator"
STADIUM_A4_HALFTIME_QUEUE_STATE = "stadium/a4/halftime/state/queues"
STADIUM_A4_HALFTIME_KPI_METRICS = "stadium/a4/halftime/metrics/kpi"
STADIUM_A4_HALFTIME_CONGESTION_STATE = "stadium/a4/halftime/state/congestion"


def topic_spectator_events() -> str:
    """Return the topic for spectator events published in Phase 3."""

    return STADIUM_A4_HALFTIME_SPECTATOR_EVENTS


def topic_queue_state() -> str:
    """Return the topic for facility-manager queue state in Phase 4."""

    return STADIUM_A4_HALFTIME_QUEUE_STATE


def topic_kpi_metrics() -> str:
    """Return the topic for metrics-agent KPI output in Phase 5."""

    return STADIUM_A4_HALFTIME_KPI_METRICS


def topic_congestion_state() -> str:
    """Return the optional congestion-state topic used by dashboard."""

    return STADIUM_A4_HALFTIME_CONGESTION_STATE
