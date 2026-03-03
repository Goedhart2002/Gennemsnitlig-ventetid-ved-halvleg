from __future__ import annotations

import json
import logging
import socket
import ssl
import time
from typing import TYPE_CHECKING
import threading

from .config import MqttConfig

if TYPE_CHECKING:
    import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MqttConnector:
    """MQTT client with automatic reconnection."""

    def __init__(self, cfg: MqttConfig, *, client_id_suffix: str | None = None):
        try:
            import paho.mqtt.client as mqtt
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                "paho-mqtt is required to use simulated_city.mqtt. "
                "Install dependencies (e.g. `pip install -e .`) and try again."
            ) from e

        self.cfg = cfg
        self._client_id = _make_client_id(cfg.client_id_prefix, client_id_suffix)
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self._client_id)
        self.connected = threading.Event()

        if cfg.username is not None:
            self.client.username_pw_set(cfg.username, password=cfg.password)

        if cfg.tls:
            context = ssl.create_default_context()
            self.client.tls_set_context(context)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc, properties):
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {self.cfg.host}:{self.cfg.port}")
            self.connected.set()
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")

    def _on_disconnect(self, client, userdata, flags, reason, properties):
        logger.warning(f"Disconnected from MQTT broker (reason={reason}). Reconnecting...")
        self.connected.clear()

    def connect(self):
        """Connect the client and start the network loop."""
        try:
            self.client.connect(self.cfg.host, self.cfg.port, keepalive=self.cfg.keepalive_s)
            self.client.loop_start()
        except (OSError, socket.gaierror, ssl.SSLError) as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
            raise

    def disconnect(self):
        """Disconnect the client and stop the network loop."""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected from MQTT broker.")

    def wait_for_connection(self, timeout: float = 10.0) -> bool:
        """Wait for the client to connect."""
        return self.connected.wait(timeout)


class MqttPublisher:
    """A simple MQTT publisher."""

    def __init__(self, connector: MqttConnector):
        self.client = connector.client

    def publish_json(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        """Publish a JSON string to a topic."""
        if not self.client.is_connected():
             logger.warning("MQTT client not connected. Message may not be published.")
        result = self.client.publish(topic, payload=payload, qos=qos, retain=retain)
        # For QoS > 0, this will block until the message is sent.
        # For QoS = 0, it returns immediately.
        if qos > 0:
            result.wait_for_publish()
        return result


def _make_client_id(prefix: str, suffix: str | None) -> str:
    """Create a client ID from a prefix and an optional suffix."""
    safe_prefix = prefix.strip() or "simcity"
    if suffix:
        return f"{safe_prefix}-{suffix}"
    return safe_prefix


def connect_mqtt(cfg: MqttConfig, *, client_id_suffix: str | None = None):
    """Connect to MQTT and return a ready-to-use paho client.

    This helper is intentionally simple for notebooks:
    - creates connector
    - starts connection loop
    - waits for connected state
    """

    connector = MqttConnector(cfg, client_id_suffix=client_id_suffix)
    connector.connect()
    if not connector.wait_for_connection(timeout=10.0):
        connector.disconnect()
        raise TimeoutError(f"Could not connect to MQTT broker at {cfg.host}:{cfg.port}")

    # Keep connector alive by attaching it to the client object.
    connector.client._simcity_connector = connector  # type: ignore[attr-defined]
    return connector.client


def publish_json_checked(
    client,
    topic: str,
    data: dict,
    *,
    qos: int = 1,
    retain: bool = False,
    timeout_s: float = 2.0,
) -> bool:
    """Publish JSON and verify publish call completed successfully.

    Returns True when publish is confirmed by the MQTT client token.
    For QoS>0 this waits for broker acknowledgement.
    """

    if not isinstance(data, dict):
        raise TypeError("publish_json_checked expects `data` to be a dict")

    payload = json.dumps(data, separators=(",", ":"))
    result = client.publish(topic, payload=payload, qos=qos, retain=retain)

    if qos > 0:
        in_mqtt_loop_thread = False
        client_thread = getattr(client, "_thread", None)
        if client_thread is not None:
            in_mqtt_loop_thread = threading.current_thread() is client_thread

        if in_mqtt_loop_thread:
            # When called from on_message callback, blocking for publish completion
            # can deadlock the network loop thread and produce false failures.
            ok = result.rc == 0
        else:
            result.wait_for_publish(timeout=timeout_s)
            # paho sets rc=0 for successful enqueue/ack path
            ok = result.rc == 0 and getattr(result, "is_published", lambda: True)()
    else:
        ok = result.rc == 0

    if not ok:
        logger.warning("MQTT publish check failed for topic %s (rc=%s)", topic, result.rc)
        return False

    # Optional tiny delay so notebook subscribers can observe messages in sequence.
    time.sleep(0.01)
    return True
