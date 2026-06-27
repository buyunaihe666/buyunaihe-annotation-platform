import json
import logging
import time
import traceback
from typing import Any, Dict

import pika

from .config import config
from .database import SessionLocal
from .models import AIAuditReport
from .audit import run_audit
from datetime import datetime

logger = logging.getLogger("agent-worker")
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)


def _process_message(ch, method, properties, body: bytes) -> None:
    try:
        message: Dict[str, Any] = json.loads(body.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse message body: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    audit_id = message.get("audit_id")
    if not audit_id:
        logger.error("Message missing audit_id, acking to drop")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    task_id = message.get("task_id") or 0
    task_item_id = message.get("task_item_id") or 0
    template_schema = message.get("template_schema")
    annotation_result = message.get("annotation_result")
    raw_data = message.get("raw_data")

    logger.info(f"Received audit {audit_id} item={task_item_id}")

    session = SessionLocal()
    try:
        report = session.get(AIAuditReport, audit_id)
        if report is None:
            report = AIAuditReport(
                id=audit_id, task_id=int(task_id), task_item_id=int(task_item_id),
                status="processing",
            )
            session.add(report)
            session.commit()
        else:
            report.status = "processing"
            session.commit()

        try:
            result = run_audit(template_schema, annotation_result, raw_data)
            report.score = result.get("score")
            report.issues = result.get("issues")
            report.reasoning = result.get("reasoning")
            report.suggestion = result.get("suggestion")
            report.evidence = result.get("evidence")
            report.model = result.get("model")
            report.error = result.get("error")
            report.status = "done"
            report.completed_at = datetime.utcnow()
            session.commit()
            logger.info(f"Audit {audit_id} done score={report.score}")
        except Exception as inner:
            session.rollback()
            report = session.get(AIAuditReport, audit_id) or report
            report.status = "failed"
            report.error = f"{type(inner).__name__}: {str(inner)[:480]}"
            report.completed_at = datetime.utcnow()
            report.model = report.model or "rule-based"
            session.commit()
            logger.error(f"Audit {audit_id} processing failed: {inner}")
    except Exception as e:
        session.rollback()
        logger.error(f"DB error during audit {audit_id}: {e}\n{traceback.format_exc()}")
    finally:
        session.close()

    ch.basic_ack(delivery_tag=method.delivery_tag)


def consume() -> None:
    backoff = 1
    max_backoff = 30
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(config.rabbitmq_url))
            channel = connection.channel()
            channel.exchange_declare(exchange="labelhub", exchange_type="direct", durable=True)
            channel.queue_declare(queue="ai_audit", durable=True)
            try:
                channel.queue_bind(queue="ai_audit", exchange="labelhub", routing_key="ai_audit")
            except Exception:
                pass
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue="ai_audit", on_message_callback=_process_message, auto_ack=False)
            logger.info("Agent worker consuming queue=ai_audit exchange=labelhub")
            backoff = 1
            channel.start_consuming()
        except Exception as e:
            logger.error(f"Connection error: {e}; retrying in {backoff}s")
            time.sleep(backoff)
            backoff = min(max_backoff, backoff * 2)
        try:
            if 'connection' in locals() and connection is not None and not connection.is_closed:
                connection.close()
        except Exception:
            pass