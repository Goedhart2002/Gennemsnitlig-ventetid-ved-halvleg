from simulated_city.simulation_core import simulate_halftime


def _base_params(seed: int = 42) -> dict:
    return {
        "seed": seed,
        "spectator_count": 300,
        "halftime_duration_s": 900,
        "toilet_servers": 12,
        "cafe_servers": 2,
        "toilet_service_min_s": 60,
        "toilet_service_max_s": 180,
        "cafe_service_min_s": 30,
        "cafe_service_max_s": 60,
        "inter_facility_walk_s": 30,
    }


def test_phase1_simulation_is_deterministic_for_same_seed() -> None:
    first = simulate_halftime(**_base_params(seed=42))
    second = simulate_halftime(**_base_params(seed=42))

    assert first.max_queue_length == second.max_queue_length
    assert first.average_wait_s == second.average_wait_s
    assert first.missed_kickoff_count == second.missed_kickoff_count
    assert first.total_served_tasks == second.total_served_tasks


def test_phase1_simulation_changes_when_seed_changes() -> None:
    first = simulate_halftime(**_base_params(seed=42))
    second = simulate_halftime(**_base_params(seed=99))

    changed = (
        first.max_queue_length != second.max_queue_length
        or first.average_wait_s != second.average_wait_s
        or first.missed_kickoff_count != second.missed_kickoff_count
    )
    assert changed


def test_phase1_kpis_are_in_valid_ranges() -> None:
    params = _base_params(seed=7)
    result = simulate_halftime(**params)

    assert result.max_queue_length >= 0
    assert result.average_wait_s >= 0.0
    assert result.average_wait_toilet_s >= 0.0
    assert result.average_wait_cafe_s >= 0.0
    assert result.average_wait_urinal_s >= 0.0
    assert 0 <= result.missed_kickoff_count <= params["spectator_count"]
    assert result.made_kickoff_count + result.missed_kickoff_count == params["spectator_count"]
    assert result.stayed_seated_count + result.went_down_count == params["spectator_count"]
    assert 0 <= result.went_down_made_back_count <= result.went_down_count
    assert result.went_down_made_back_count <= result.made_kickoff_count
    assert result.total_served_tasks >= 0
    assert result.women_toilet_served_count >= 0
    assert result.men_toilet_served_count >= 0
    assert result.men_urinal_served_count >= 0
    assert (
        result.women_toilet_served_count
        + result.men_toilet_served_count
        + result.men_urinal_served_count
        <= result.total_served_tasks
    )
    assert len(result.ticks) == params["halftime_duration_s"] + 1


def test_phase1_tick_state_contains_queue_lengths() -> None:
    result = simulate_halftime(**_base_params())

    first_tick = result.ticks[0]
    assert "toilet" in first_tick.queue_lengths
    assert "cafe" in first_tick.queue_lengths
    assert first_tick.queue_lengths["toilet"] >= 0
    assert first_tick.queue_lengths["cafe"] >= 0


def test_phase1_seat_leave_rate_reduces_kickoff_misses() -> None:
    full_participation = simulate_halftime(**_base_params(seed=42), seat_leave_rate=1.0)
    realistic_participation = simulate_halftime(**_base_params(seed=42), seat_leave_rate=0.7)

    assert realistic_participation.missed_kickoff_count <= full_participation.missed_kickoff_count
    assert realistic_participation.total_served_tasks <= full_participation.total_served_tasks
