from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Literal

from simulated_city.config import AppConfig
from simulated_city.config_models import HalftimeSimulationConfig


TaskType = Literal["toilet_w", "toilet_m", "urinal", "cafe"]
SpectatorStatus = Literal[
    "seated",
    "walking_to_facility",
    "waiting",
    "in_service",
    "walking_between",
    "walking_return",
    "done",
]


@dataclass(slots=True)
class SpectatorState:
    spectator_id: int
    is_male: bool
    departure_time_s: int
    walking_time_one_way_s: int
    planned_tasks: list[TaskType]
    status: SpectatorStatus = "seated"
    task_index: int = 0
    remaining_walk_s: int = 0
    return_time_s: int | None = None


@dataclass(slots=True)
class QueueState:
    name: TaskType
    servers_total: int
    service_min_s: int
    service_max_s: int
    waiting: list[int] = field(default_factory=list)
    joined_at_s: dict[int, int] = field(default_factory=dict)
    in_service_remaining_s: dict[int, int] = field(default_factory=dict)
    max_length: int = 0


@dataclass(frozen=True, slots=True)
class SimulationTickState:
    timestamp_s: int
    spectators_out_of_seat: int
    queue_lengths: dict[str, int]


@dataclass(frozen=True, slots=True)
class SimulationResult:
    max_queue_length: int
    average_wait_s: float
    average_wait_toilet_s: float
    average_wait_cafe_s: float
    average_wait_urinal_s: float
    missed_kickoff_count: int
    made_kickoff_count: int
    stayed_seated_count: int
    went_down_count: int
    went_down_made_back_count: int
    total_served_tasks: int
    women_toilet_served_count: int
    men_toilet_served_count: int
    men_urinal_served_count: int
    ticks: list[SimulationTickState]


def _sample_departure_time_s(rng: random.Random, halftime_duration_s: int) -> int:
    sample = rng.triangular(0, halftime_duration_s, halftime_duration_s * 0.2)
    return max(0, min(halftime_duration_s - 1, int(sample)))


def _sample_walking_time_s(rng: random.Random) -> int:
    sample = rng.triangular(30, 300, 120)
    return max(30, min(300, int(sample)))


def _sample_toilet_task(rng: random.Random, is_male: bool) -> TaskType:
    if not is_male:
        return "toilet_w"
    return "urinal" if rng.random() < 0.5 else "toilet_m"


def _sample_planned_tasks(rng: random.Random, is_male: bool) -> list[TaskType]:
    value = rng.random()
    toilet_task = _sample_toilet_task(rng, is_male)
    if value < 0.28:
        return [toilet_task]
    if value < 0.56:
        return ["cafe"]
    if value < 0.78:
        return [toilet_task, "cafe"]
    if value < 0.96:
        return ["cafe", toilet_task]
    return []


def _enqueue_spectator(
    queue: QueueState,
    spectator_id: int,
    now_s: int,
) -> None:
    queue.waiting.append(spectator_id)
    queue.joined_at_s[spectator_id] = now_s
    if len(queue.waiting) > queue.max_length:
        queue.max_length = len(queue.waiting)


def _start_service_for_waiting(
    queue: QueueState,
    rng: random.Random,
    now_s: int,
    wait_times_s: list[int],
) -> None:
    free_slots = queue.servers_total - len(queue.in_service_remaining_s)
    for _ in range(max(0, free_slots)):
        if not queue.waiting:
            break
        spectator_id = queue.waiting.pop(0)
        joined_at_s = queue.joined_at_s.pop(spectator_id, now_s)
        wait_times_s.append(max(0, now_s - joined_at_s))
        service_time_s = rng.randint(queue.service_min_s, queue.service_max_s)
        queue.in_service_remaining_s[spectator_id] = service_time_s


def _step_service(queue: QueueState) -> list[int]:
    finished_ids: list[int] = []
    remaining_items = list(queue.in_service_remaining_s.items())
    for spectator_id, remaining_s in remaining_items:
        next_remaining = remaining_s - 1
        if next_remaining <= 0:
            finished_ids.append(spectator_id)
            del queue.in_service_remaining_s[spectator_id]
        else:
            queue.in_service_remaining_s[spectator_id] = next_remaining
    return finished_ids


def _active_queue_length(queue: QueueState) -> int:
    return len(queue.waiting) + len(queue.in_service_remaining_s)


def simulate_halftime(
    seed: int,
    spectator_count: int,
    halftime_duration_s: int,
    toilet_servers: int,
    cafe_servers: int,
    toilet_service_min_s: int,
    toilet_service_max_s: int,
    cafe_service_min_s: int,
    cafe_service_max_s: int,
    urinal_service_min_s: int = 20,
    urinal_service_max_s: int = 45,
    inter_facility_walk_s: int = 30,
    seat_leave_rate: float = 0.70,
    shared_urinal_total: int = 0,
) -> SimulationResult:
    rng = random.Random(seed)

    if not (0.0 <= seat_leave_rate <= 1.0):
        raise ValueError("seat_leave_rate must be within 0..1")

    spectators: dict[int, SpectatorState] = {}
    for spectator_id in range(spectator_count):
        participates = rng.random() < seat_leave_rate
        is_male = rng.random() < 0.5
        spectators[spectator_id] = SpectatorState(
            spectator_id=spectator_id,
            is_male=is_male,
            departure_time_s=_sample_departure_time_s(rng, halftime_duration_s),
            walking_time_one_way_s=_sample_walking_time_s(rng),
            planned_tasks=_sample_planned_tasks(rng, is_male) if participates else [],
        )

    women_toilet_servers = max(0, toilet_servers // 2)
    men_toilet_servers = max(0, toilet_servers - women_toilet_servers)

    women_toilet_queue = QueueState(
        name="toilet_w",
        servers_total=women_toilet_servers,
        service_min_s=toilet_service_min_s,
        service_max_s=toilet_service_max_s,
    )
    men_toilet_queue = QueueState(
        name="toilet_m",
        servers_total=men_toilet_servers,
        service_min_s=toilet_service_min_s,
        service_max_s=toilet_service_max_s,
    )
    urinal_queue = QueueState(
        name="urinal",
        servers_total=max(0, shared_urinal_total),
        service_min_s=urinal_service_min_s,
        service_max_s=urinal_service_max_s,
    )
    cafe_queue = QueueState(
        name="cafe",
        servers_total=cafe_servers,
        service_min_s=cafe_service_min_s,
        service_max_s=cafe_service_max_s,
    )

    queue_by_task: dict[TaskType, QueueState] = {
        "toilet_w": women_toilet_queue,
        "toilet_m": men_toilet_queue,
        "urinal": urinal_queue,
        "cafe": cafe_queue,
    }

    wait_times_toilet_s: list[int] = []
    wait_times_cafe_s: list[int] = []
    wait_times_urinal_s: list[int] = []
    ticks: list[SimulationTickState] = []

    women_toilet_served_count = 0
    men_toilet_served_count = 0
    men_urinal_served_count = 0

    for now_s in range(halftime_duration_s + 1):
        for spectator in spectators.values():
            if spectator.status == "seated" and spectator.planned_tasks and spectator.departure_time_s <= now_s:
                spectator.status = "walking_to_facility"
                spectator.remaining_walk_s = spectator.walking_time_one_way_s

        for spectator in spectators.values():
            if spectator.status not in {"walking_to_facility", "walking_between", "walking_return"}:
                continue
            spectator.remaining_walk_s -= 1
            if spectator.remaining_walk_s > 0:
                continue

            if spectator.status in {"walking_to_facility", "walking_between"}:
                next_task = spectator.planned_tasks[spectator.task_index]
                target_queue = queue_by_task[next_task]
                _enqueue_spectator(target_queue, spectator.spectator_id, now_s)
                spectator.status = "waiting"
            elif spectator.status == "walking_return":
                spectator.status = "done"
                spectator.return_time_s = now_s

        _start_service_for_waiting(women_toilet_queue, rng, now_s, wait_times_toilet_s)
        _start_service_for_waiting(men_toilet_queue, rng, now_s, wait_times_toilet_s)
        _start_service_for_waiting(urinal_queue, rng, now_s, wait_times_urinal_s)
        _start_service_for_waiting(cafe_queue, rng, now_s, wait_times_cafe_s)

        finished_women_toilet = _step_service(women_toilet_queue)
        finished_men_toilet = _step_service(men_toilet_queue)
        finished_urinal = _step_service(urinal_queue)
        finished_cafe = _step_service(cafe_queue)

        women_toilet_served_count += len(finished_women_toilet)
        men_toilet_served_count += len(finished_men_toilet)
        men_urinal_served_count += len(finished_urinal)

        for spectator_id in finished_women_toilet + finished_men_toilet + finished_urinal + finished_cafe:
            spectator = spectators[spectator_id]
            spectator.task_index += 1
            if spectator.task_index >= len(spectator.planned_tasks):
                spectator.status = "walking_return"
                spectator.remaining_walk_s = spectator.walking_time_one_way_s
            else:
                spectator.status = "walking_between"
                spectator.remaining_walk_s = inter_facility_walk_s

        current_queue_lengths = {
            "toilet": _active_queue_length(women_toilet_queue)
            + _active_queue_length(men_toilet_queue)
            + _active_queue_length(urinal_queue),
            "toilet_w": _active_queue_length(women_toilet_queue),
            "toilet_m": _active_queue_length(men_toilet_queue),
            "urinal": _active_queue_length(urinal_queue),
            "cafe": _active_queue_length(cafe_queue),
        }
        out_of_seat = sum(
            1
            for spectator in spectators.values()
            if spectator.status not in {"seated", "done"}
        )
        ticks.append(
            SimulationTickState(
                timestamp_s=now_s,
                spectators_out_of_seat=out_of_seat,
                queue_lengths=current_queue_lengths,
            )
        )

    for spectator in spectators.values():
        if spectator.return_time_s is None:
            if spectator.status == "seated":
                spectator.return_time_s = spectator.departure_time_s
            else:
                spectator.return_time_s = halftime_duration_s + 1

    total_queue_lengths = [tick.queue_lengths["toilet"] for tick in ticks]
    max_queue_length = max(total_queue_lengths) if total_queue_lengths else 0
    all_wait_times_s = wait_times_toilet_s + wait_times_urinal_s + wait_times_cafe_s
    average_wait_s = sum(all_wait_times_s) / len(all_wait_times_s) if all_wait_times_s else 0.0
    average_wait_toilet_s = sum(wait_times_toilet_s) / len(wait_times_toilet_s) if wait_times_toilet_s else 0.0
    average_wait_cafe_s = sum(wait_times_cafe_s) / len(wait_times_cafe_s) if wait_times_cafe_s else 0.0
    average_wait_urinal_s = sum(wait_times_urinal_s) / len(wait_times_urinal_s) if wait_times_urinal_s else 0.0
    missed_kickoff_count = sum(
        1 for spectator in spectators.values() if (spectator.return_time_s or 0) > halftime_duration_s
    )
    made_kickoff_count = spectator_count - missed_kickoff_count
    went_down_count = sum(1 for spectator in spectators.values() if spectator.planned_tasks)
    stayed_seated_count = spectator_count - went_down_count
    went_down_made_back_count = sum(
        1
        for spectator in spectators.values()
        if spectator.planned_tasks and (spectator.return_time_s or 0) <= halftime_duration_s
    )

    return SimulationResult(
        max_queue_length=max_queue_length,
        average_wait_s=average_wait_s,
        average_wait_toilet_s=average_wait_toilet_s,
        average_wait_cafe_s=average_wait_cafe_s,
        average_wait_urinal_s=average_wait_urinal_s,
        missed_kickoff_count=missed_kickoff_count,
        made_kickoff_count=made_kickoff_count,
        stayed_seated_count=stayed_seated_count,
        went_down_count=went_down_count,
        went_down_made_back_count=went_down_made_back_count,
        total_served_tasks=len(all_wait_times_s),
        women_toilet_served_count=women_toilet_served_count,
        men_toilet_served_count=men_toilet_served_count,
        men_urinal_served_count=men_urinal_served_count,
        ticks=ticks,
    )


def simulate_halftime_with_config(config: HalftimeSimulationConfig) -> SimulationResult:
    """Run halftime simulation using typed config values from `config.yaml`."""

    return simulate_halftime(**config.to_simulation_core_kwargs())


def simulate_halftime_from_app_config(app_config: AppConfig) -> SimulationResult:
    """Run halftime simulation from `load_config()` output.

    Phase 2 requires configuration-driven behavior. This helper keeps notebook
    usage simple for beginners: load config once, then call this function.
    """

    if app_config.halftime is None:
        raise ValueError("App config has no 'halftime' section. Add halftime settings to config.yaml.")
    return simulate_halftime_with_config(app_config.halftime)
