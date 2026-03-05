from textwrap import dedent

from simulated_city.config import load_config


def test_load_config_defaults_when_missing(tmp_path) -> None:
    """Test that default config loads when file is missing."""
    cfg = load_config(tmp_path / "missing.yaml")
    assert cfg.mqtt.host
    assert cfg.mqtt.port
    # Should have at least the default 'local' profile
    assert "local" in cfg.mqtt_configs or len(cfg.mqtt_configs) > 0


def test_load_config_reads_yaml(tmp_path) -> None:
    """Test reading YAML config with multi-broker structure."""
    p = tmp_path / "config.yaml"
    p.write_text(
        """
        mqtt:
          active_profiles: [default]
          profiles:
            default:
              host: example.com
              port: 1883
              tls: false
          client_id_prefix: demo
          keepalive_s: 30
        """.strip(),
        encoding="utf-8",
    )

    cfg = load_config(p)
    assert cfg.mqtt.host == "example.com"
    assert cfg.mqtt.port == 1883
    assert cfg.mqtt.tls is False
    assert cfg.mqtt.client_id_prefix == "demo"
    assert cfg.mqtt.keepalive_s == 30


def test_load_config_finds_parent_config_yaml(tmp_path, monkeypatch) -> None:
    """Test that config is found in parent directories."""
    # Simulate running from a subdirectory (like notebooks/)
    root = tmp_path
    (root / "config.yaml").write_text(
        """
        mqtt:
          active_profiles: [parent]
          profiles:
            parent:
              host: parent.example.com
              port: 1883
              tls: false
          client_id_prefix: demo
          keepalive_s: 30
        """.strip(),
        encoding="utf-8",
    )

    subdir = root / "notebooks"
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    cfg = load_config("config.yaml")
    assert cfg.mqtt.host == "parent.example.com"

def test_load_config_multi_broker_with_active_profiles(tmp_path) -> None:
    """Test multi-broker configuration with active_profiles list."""
    p = tmp_path / "config.yaml"
    p.write_text(
        """
        mqtt:
          active_profiles: [local, public]
          profiles:
            local:
              host: localhost
              port: 1883
              tls: false
            public:
              host: broker.example.com
              port: 1883
              tls: false
          client_id_prefix: multi-test
          keepalive_s: 60
          base_topic: test-city
        """.strip(),
        encoding="utf-8",
    )

    cfg = load_config(p)
    
    # Primary broker (first in list)
    assert cfg.mqtt.host == "localhost"
    assert cfg.mqtt.port == 1883
    
    # All brokers available by name
    assert "local" in cfg.mqtt_configs
    assert "public" in cfg.mqtt_configs
    assert cfg.mqtt_configs["local"].host == "localhost"
    assert cfg.mqtt_configs["public"].host == "broker.example.com"


def test_load_config_single_broker_with_active_profiles(tmp_path) -> None:
    """Test single-broker configuration using active_profiles."""
    p = tmp_path / "config.yaml"
    p.write_text(
        dedent(
            """
        mqtt:
          active_profiles: [local]
          profiles:
            local:
              host: localhost
              port: 1883
              tls: false
          client_id_prefix: single-test
          keepalive_s: 60
          base_topic: test-city
        """
        ).strip(),
        encoding="utf-8",
    )

    cfg = load_config(p)
    
    # Primary broker
    assert cfg.mqtt.host == "localhost"
    
    # Only local broker in configs
    assert "local" in cfg.mqtt_configs
    assert len(cfg.mqtt_configs) == 1


def test_load_config_parses_halftime_map_section(tmp_path) -> None:
    """Test typed halftime_map parsing and zone naming compatibility config."""
    p = tmp_path / "config.yaml"
    p.write_text(
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

    cfg = load_config(p)

    assert cfg.halftime_map is not None
    assert cfg.halftime_map.zoom == 17
    assert cfg.halftime_map.max_points_per_message == 1000
    assert cfg.halftime_map.zone_naming.canonical_service_zones == ("zone_1", "zone_2")
    assert cfg.halftime_map.zone_naming.legacy_zone_aliases == {
        "zone_a": "zone_1",
        "zone_b": "zone_2",
    }


def test_load_config_defaults_halftime_map_to_none_when_missing(tmp_path) -> None:
    """Test that halftime_map remains optional when omitted."""
    p = tmp_path / "config.yaml"
    p.write_text(
        dedent(
            """
        mqtt:
          active_profiles: [local]
          profiles:
            local:
              host: localhost
              port: 1883
              tls: false
        """
        ).strip(),
        encoding="utf-8",
    )

    cfg = load_config(p)
    assert cfg.halftime_map is None