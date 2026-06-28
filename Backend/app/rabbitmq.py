from __future__ import annotations

import json
import logging

import pika
import pika.exceptions

from . import config

logger = logging.getLogger("buyunaihe.rabbitmq")

_channel = None
_connection = None


def _connect():
    global _connection, _channel
    credentials = pika.PlainCredentials(config.RABBITMQ_USER, config.RABBITMQ_PASSWORD)
    params = pika.ConnectionParameters(
        host=config.RABBITMQ_HOST,
        port=config.RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=30,
        blocked_connection_timeout=10,
    )
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.exchange_declare(exchange=config.RABBITMQ_EXCHANGE, exchange_type="direct", durable=True)
    ch.queue_declare(queue=config.RABBITMQ_QUEUE, durable=True)
    ch.queue_bind(
        exchange=config.RABBITMQ_EXCHANGE,
        queue=config.RABBITMQ_QUEUE,
        routing_key=config.RABBITMQ_ROUTING_KEY,
    )
    _connection = conn
    _channel = ch
    return ch


def verify_connection() -> bool:
    # Quick socket check first to avoid slow pika retries
    try:
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        if s.connect_ex((config.RABBITMQ_HOST, config.RABBITMQ_PORT)) != 0:
            s.close()
            logger.warning(f"[rabbitmq] not reachable at {config.RABBITMQ_HOST}:{config.RABBITMQ_PORT}")
            return False
        s.close()
    except Exception as e:
        logger.warning(f"[rabbitmq] socket probe failed: {e}")
        return False
    try:
        _connect()
        return True
    except Exception as e:
        logger.warning(f"[rabbitmq] connection failed: {e}")
        return False


def publish_audit(message: dict) -> bool:
    global _connection, _channel
    try:
        ch = _channel
        if ch is None or _connection is None or _connection.is_closed:
            _connect()
        assert _channel is not None
        _channel.basic_publish(
            exchange=config.RABBITMQ_EXCHANGE,
            routing_key=config.RABBITMQ_ROUTING_KEY,
            body=json.dumps(message, ensure_ascii=False).encode("utf-8"),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )
        return True
    except Exception as e:
        logger.warning(f"[rabbitmq] publish failed: {e}")
        try:
            _connection = None
            _channel = None
        except Exception:
            pass
        return False