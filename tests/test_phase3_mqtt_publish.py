from simulated_city.mqtt import publish_json_checked
from simulated_city.mqtt_payloads import (
    build_spectator_event_payload,
    validate_spectator_event_payload,
)
from simulated_city.topic_schema import topic_spectator_events


class _FakePublishResult:
    def __init__(self, rc: int = 0, published: bool = True):
        self.rc = rc
        self._published = published

    def wait_for_publish(self, timeout=None):
        return None

    def is_published(self):
        return self._published


class _FakeClient:
    def __init__(self, rc: int = 0, published: bool = True):
        self._rc = rc
        self._published = published
        self.calls = []

    def publish(self, topic, payload, qos, retain):
        self.calls.append(
            {
                "topic": topic,
                "payload": payload,
                "qos": qos,
                "retain": retain,
            }
        )
        return _FakePublishResult(rc=self._rc, published=self._published)


def test_phase3_topic_matches_plan() -> None:
    assert topic_spectator_events() == "stadium/a4/halftime/events/spectator"


def test_phase3_payload_builder_includes_required_envelope() -> None:
    payload = build_spectator_event_payload(
        schema_version="1.0",
        run_id="a4-run-test",
        timestamp_s=10,
        spectators_out_of_seat=123,
        queue_toilet=12,
        queue_cafe=4,
    )

    assert payload["schema_version"] == "1.0"
    assert payload["run_id"] == "a4-run-test"
    assert payload["timestamp_s"] == 10
    assert payload["queue_lengths"]["toilet"] == 12
    assert payload["queue_lengths"]["cafe"] == 4


def test_phase3_payload_validator_rejects_missing_envelope_field() -> None:
    invalid_payload = {
        "schema_version": "1.0",
        "timestamp_s": 10,
        "spectators_out_of_seat": 1,
        "queue_lengths": {"toilet": 1, "cafe": 1},
    }

    try:
        validate_spectator_event_payload(invalid_payload)
        assert False, "Expected ValueError for missing run_id"
    except ValueError as error:
        assert "run_id" in str(error)


def test_phase3_publish_json_checked_sends_payload() -> None:
    fake_client = _FakeClient(rc=0, published=True)
    payload = build_spectator_event_payload(
        schema_version="1.0",
        run_id="a4-run-test",
        timestamp_s=5,
        spectators_out_of_seat=42,
        queue_toilet=9,
        queue_cafe=3,
    )

    ok = publish_json_checked(fake_client, topic_spectator_events(), payload, qos=1)

    assert ok is True
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0]["topic"] == "stadium/a4/halftime/events/spectator"
    assert '"schema_version":"1.0"' in fake_client.calls[0]["payload"]


def test_phase3_publish_json_checked_fails_on_bad_rc() -> None:
    fake_client = _FakeClient(rc=1, published=False)
    payload = build_spectator_event_payload(
        schema_version="1.0",
        run_id="a4-run-test",
        timestamp_s=5,
        spectators_out_of_seat=42,
        queue_toilet=9,
        queue_cafe=3,
    )

    ok = publish_json_checked(fake_client, topic_spectator_events(), payload, qos=1)

    assert ok is False
