from textwrap import dedent

from simulated_city.config import load_config
from simulated_city.simulation_core import (
    simulate_halftime,
    simulate_halftime_from_app_config,
)


def test_phase2_load_config_parses_halftime_section(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        dedent(
            """
        mqtt:
          active_profiles: [local]
          profiles:
            local:
              host: localhost
              port: 1883
              tls: false

        halftime:
          seed: 7
          capacity:
            spectator_count: 1000
            toilet_servers: 12
            cafe_servers: 8
            shared_urinal_total: 10
          timing:
            halftime_duration_s: 900
            inter_facility_walk_s: 25
            walking_time_min_s: 30
            walking_time_mode_s: 90
            walking_time_max_s: 300
            toilet_service_s: {min: 60, max: 180}
            cafe_service_s: {min: 30, max: 60}
            urinal_service_s: {min: 20, max: 45}
          behavior:
            seat_leave_rate: 0.7
            women_ratio: 0.3
            queue_abandon_threshold_s: 180
            queue_switch_threshold_people: 12
            missed_kickoff_risk_window_s: 90
          blocking:
            queue_people_per_line_threshold: 15
            lines_considered: 8
            walking_speed_factor_when_blocked: 0.7
          kpi:
            percentiles: [1, 50, 95, 100]

        halftime_map:
          center_lng: 12.5683
          center_lat: 55.6761
          zoom: 17
          seat_area_bbox: [12.5679, 55.6759, 12.5687, 55.6766]
          zone_1_toilet_w: [12.5678, 55.6762]
          zone_1_toilet_m: [12.5679, 55.67622]
          zone_1_cafe: [12.5680, 55.67618]
          zone_2_toilet_w: [12.5689, 55.6760]
          zone_2_toilet_m: [12.5690, 55.67602]
          zone_2_cafe: [12.5691, 55.67598]
          shared_urinal: [12.5685, 55.6756]
          publish_interval_s: 1
          max_points_per_message: 1000
          zone_naming:
            canonical_service_zones: [zone_1, zone_2]
            legacy_zone_aliases:
              zone_a: zone_1
              zone_b: zone_2
        """
        ).strip(),
        encoding="utf-8",
    )

    cfg = load_config(path)

    assert cfg.halftime is not None
    assert cfg.halftime.seed == 7
    assert cfg.halftime.capacity.spectator_count == 1000
    assert cfg.halftime.capacity.shared_urinal_total == 10
    assert cfg.halftime.timing.cafe_service_s.min_s == 30
    assert cfg.halftime.timing.toilet_service_s.max_s == 180
    assert cfg.halftime.behavior.seat_leave_rate == 0.7
    assert cfg.halftime.behavior.women_ratio == 0.3
    assert cfg.halftime.blocking.queue_people_per_line_threshold == 15
    assert cfg.halftime.kpi.percentiles == (1, 50, 95, 100)
    assert cfg.halftime_map is not None
    assert cfg.halftime_map.center.lng == 12.5683
    assert cfg.halftime_map.zone_1_toilet_w.lat == 55.6762
    assert cfg.halftime_map.publish_interval_s == 1
    assert cfg.halftime_map.zone_naming.canonical_service_zones == ("zone_1", "zone_2")
    assert cfg.halftime_map.zone_naming.legacy_zone_aliases["zone_a"] == "zone_1"


def test_phase2_validates_kpi_percentiles_range(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        dedent(
            """
        mqtt:
          active_profiles: [local]
          profiles:
            local:
              host: localhost
              port: 1883
              tls: false

        halftime:
          behavior:
            seat_leave_rate: 1.5
            women_ratio: 1.2
          kpi:
            percentiles: [0, 50, 101]
        """
        ).strip(),
        encoding="utf-8",
    )

    try:
        load_config(path)
        assert False, "Expected ValueError for out-of-range KPI percentiles"
    except ValueError as error:
      message = str(error)
      assert "1..100" in message or "seat_leave_rate" in message or "women_ratio" in message


def test_phase2_simulation_core_uses_loaded_config(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        dedent(
            """
        mqtt:
          active_profiles: [local]
          profiles:
            local:
              host: localhost
              port: 1883
              tls: false

        halftime:
          seed: 13
          capacity:
            spectator_count: 120
            toilet_servers: 4
            cafe_servers: 3
            shared_urinal_total: 2
          timing:
            halftime_duration_s: 120
            inter_facility_walk_s: 20
            walking_time_min_s: 30
            walking_time_mode_s: 60
            walking_time_max_s: 180
            toilet_service_s: {min: 40, max: 70}
            cafe_service_s: {min: 20, max: 40}
            urinal_service_s: {min: 15, max: 30}
          behavior:
            seat_leave_rate: 0.75
            queue_abandon_threshold_s: 120
            queue_switch_threshold_people: 8
            missed_kickoff_risk_window_s: 60
          blocking:
            queue_people_per_line_threshold: 10
            lines_considered: 6
            walking_speed_factor_when_blocked: 0.8
          kpi:
            percentiles: [1, 25, 50, 75, 100]
        """
        ).strip(),
        encoding="utf-8",
    )

    cfg = load_config(path)
    assert cfg.halftime is not None

    from_app_cfg = simulate_halftime_from_app_config(cfg)
    from_kwargs = simulate_halftime(**cfg.halftime.to_simulation_core_kwargs())

    assert len(from_app_cfg.ticks) == 121
    assert from_app_cfg.max_queue_length == from_kwargs.max_queue_length
    assert from_app_cfg.average_wait_s == from_kwargs.average_wait_s
    assert from_app_cfg.missed_kickoff_count == from_kwargs.missed_kickoff_count
    assert from_app_cfg.total_served_tasks == from_kwargs.total_served_tasks


def test_phase2_validates_seat_leave_rate_range(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        dedent(
            """
        mqtt:
          active_profiles: [local]
          profiles:
            local:
              host: localhost
              port: 1883
              tls: false

        halftime:
          behavior:
            seat_leave_rate: -0.1
        """
        ).strip(),
        encoding="utf-8",
    )

    try:
        load_config(path)
        assert False, "Expected ValueError for out-of-range seat_leave_rate"
    except ValueError as error:
        assert "seat_leave_rate" in str(error)


def test_phase2_validates_halftime_map_publish_interval(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        dedent(
            """
        mqtt:
          active_profiles: [local]
          profiles:
            local:
              host: localhost
              port: 1883
              tls: false

        halftime_map:
          publish_interval_s: 0
        """
        ).strip(),
        encoding="utf-8",
    )

    try:
        load_config(path)
        assert False, "Expected ValueError for invalid halftime_map.publish_interval_s"
    except ValueError as error:
        assert "publish_interval_s" in str(error)


def test_phase2_validates_zone_naming_canonical_values(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        dedent(
            """
        mqtt:
          active_profiles: [local]
          profiles:
            local:
              host: localhost
              port: 1883
              tls: false

        halftime_map:
          zone_naming:
            canonical_service_zones: [zone_a, zone_b]
            legacy_zone_aliases:
              zone_a: zone_1
              zone_b: zone_2
        """
        ).strip(),
        encoding="utf-8",
    )

    try:
        load_config(path)
        assert False, "Expected ValueError for invalid canonical zone naming"
    except ValueError as error:
        assert "canonical_service_zones" in str(error)
